"""API endpoints for SKILL_POLICY.yaml generation, validation, revisions, mock testing and export.

Every generated or edited policy is stored as a new immutable revision; nothing
is overwritten. Only validated revisions can be saved, tested or exported.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..policy.evaluator import simulate_policy_scenarios
from ..policy.generator import generate_least_privilege_policy, policy_rationale
from ..policy.schema import PolicyRationale, PolicyValidationResult, SkillPolicy
from ..policy.validator import validate_policy
from ..policy.yaml_export import from_yaml, to_yaml
from ..schemas import ScanReport, ScanState
from .deps import ApiError, get_report_or_404, store

router = APIRouter()


class PolicyResponse(BaseModel):
    revision: int
    revisions: list[int]
    policy: SkillPolicy
    yaml: str
    validation: PolicyValidationResult
    rationale: list[PolicyRationale]


class PolicyPayload(BaseModel):
    policy: Optional[dict[str, Any]] = None
    yaml: Optional[str] = None


class PolicyTestRequest(PolicyPayload):
    revision: Optional[int] = None
    test_ids: Optional[list[str]] = None


def _completed(scan_id: str) -> ScanReport:
    report = get_report_or_404(scan_id)
    if report.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Scan has not completed yet.")
    return report


def _store_revision(scan_id: str, policy: SkillPolicy) -> int:
    rev = store().save_policy(scan_id, to_yaml(policy))
    store().link_extension(scan_id, "policy_revisions", f"r{rev:03d}")
    return rev


def _response(report: ScanReport, rev: int, yaml_text: str) -> PolicyResponse:
    policy, val = from_yaml(yaml_text)
    if policy is None:  # stored revisions are validated before saving; this is defensive
        raise ApiError(500, "POLICY_SCHEMA_INVALID", f"Stored policy revision r{rev:03d} failed validation.")
    rationale, warnings = policy_rationale(report, policy)
    if policy.metadata.get("generator_mode") == "user_edited":
        rationale = [PolicyRationale(field="*", value=f"r{rev:03d}", reason="Edited by a reviewer; generated rationale may no longer apply.")]
        warnings = []
    val.warnings = val.warnings + warnings
    val.source_finding_ids = sorted({fid for r in rationale for fid in r.finding_ids})
    return PolicyResponse(
        revision=rev, revisions=store().policy_revisions(report.scan_id), policy=policy,
        yaml=yaml_text, validation=val, rationale=rationale,
    )


def _parse_payload(body: PolicyPayload) -> tuple[Optional[SkillPolicy], PolicyValidationResult]:
    if body.yaml is not None:
        return from_yaml(body.yaml)
    if body.policy is not None:
        val = validate_policy(body.policy)
        return (SkillPolicy.model_validate(body.policy) if val.valid else None), val
    raise ApiError(400, "MISSING_POLICY_PAYLOAD", "Provide either 'yaml' or 'policy'.")


@router.post("/api/scans/{scan_id}/policy/generate", response_model=PolicyResponse)
def generate_policy(scan_id: str) -> PolicyResponse:
    report = _completed(scan_id)
    policy = generate_least_privilege_policy(report)
    if not validate_policy(policy).valid:
        raise ApiError(500, "POLICY_SEMANTICS_INVALID", "Generated policy failed validation.")
    rev = _store_revision(scan_id, policy)
    return _response(report, rev, store().get_policy(scan_id, rev)[1])


@router.get("/api/scans/{scan_id}/policy", response_model=PolicyResponse)
def get_policy(scan_id: str, revision: Optional[int] = Query(None, ge=1)) -> PolicyResponse:
    report = _completed(scan_id)
    found = store().get_policy(scan_id, revision)
    if found is None:
        if revision is not None:
            raise ApiError(404, "POLICY_REVISION_NOT_FOUND", f"Policy revision {revision} not found.")
        return generate_policy(scan_id)
    return _response(report, *found)


@router.post("/api/scans/{scan_id}/policy/validate", response_model=PolicyValidationResult)
def validate_policy_endpoint(scan_id: str, body: PolicyPayload) -> PolicyValidationResult:
    get_report_or_404(scan_id)
    return _parse_payload(body)[1]


@router.post("/api/scans/{scan_id}/policy/revisions", response_model=PolicyResponse)
def save_policy_revision(scan_id: str, body: PolicyPayload) -> PolicyResponse:
    """Validate an edited copy and store it as a new revision; earlier revisions stay unchanged."""
    report = _completed(scan_id)
    policy, val = _parse_payload(body)
    if policy is None:
        raise ApiError(422, "POLICY_SCHEMA_INVALID", "Policy failed validation and was not saved.",
                       {"errors": [e.model_dump() for e in val.errors][:20]})
    policy.metadata = {**policy.metadata, "generator_mode": "user_edited"}
    rev = _store_revision(scan_id, policy)
    return _response(report, rev, store().get_policy(scan_id, rev)[1])


@router.post("/api/scans/{scan_id}/policy/test")
def test_policy_endpoint(scan_id: str, body: PolicyTestRequest) -> dict[str, Any]:
    """Replay existing test scenarios through a validated policy in the mock gate."""
    report = _completed(scan_id)
    rev: Optional[int] = None
    if body.yaml is not None or body.policy is not None:
        policy, val = _parse_payload(body)
        if policy is None:
            raise ApiError(422, "POLICY_SCHEMA_INVALID", "Cannot test an invalid policy.",
                           {"errors": [e.model_dump() for e in val.errors][:20]})
    else:
        found = store().get_policy(scan_id, body.revision)
        if found is None:
            raise ApiError(404, "POLICY_REVISION_NOT_FOUND", "No saved policy revision to test.")
        rev = found[0]
        policy, _ = from_yaml(found[1])

    tests = report.tests
    if body.test_ids:
        unknown = set(body.test_ids) - {t.test_id for t in tests}
        if unknown:
            raise ApiError(404, "TEST_NOT_FOUND", "Unknown test IDs.", {"test_ids": sorted(unknown)})
        tests = [t for t in tests if t.test_id in body.test_ids]

    return {
        "scan_id": scan_id,
        "policy_id": policy.policy_id,
        "revision": rev,
        "enforcement_status": "mock_tested",
        "results": simulate_policy_scenarios(policy, tests),
    }


@router.get("/api/scans/{scan_id}/policy/export")
def export_policy(scan_id: str, revision: Optional[int] = Query(None, ge=1)):
    get_report_or_404(scan_id)
    found = store().get_policy(scan_id, revision)
    if found is None:
        raise ApiError(404, "POLICY_REVISION_NOT_FOUND", "No saved policy revision to export. Generate one first.")
    rev, yaml_text = found
    if not from_yaml(yaml_text)[1].valid:
        raise ApiError(422, "POLICY_SCHEMA_INVALID", "Policy failed validation and cannot be exported.")
    return PlainTextResponse(
        yaml_text,
        media_type="text/yaml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="SKILL_POLICY-{scan_id}-r{rev:03d}.yaml"'},
    )
