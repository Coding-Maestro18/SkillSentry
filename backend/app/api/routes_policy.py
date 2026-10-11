"""API endpoints for SKILL_POLICY.yaml generation, validation, testing, and export."""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from ..policy.evaluator import simulate_policy_scenarios
from ..policy.generator import generate_least_privilege_policy
from ..policy.schema import PolicyValidationResult, SkillPolicy
from ..policy.validator import validate_policy
from ..policy.yaml_export import from_yaml, to_yaml
from ..schemas import ScanState
from .deps import ApiError, get_report_or_404, store

router = APIRouter()


class PolicyResponse(BaseModel):
    policy: SkillPolicy
    yaml: str
    validation: PolicyValidationResult


class PolicyValidateRequest(BaseModel):
    policy: Optional[dict[str, Any]] = None
    yaml: Optional[str] = None


class PolicyTestRequest(BaseModel):
    policy: Optional[dict[str, Any]] = None
    yaml: Optional[str] = None
    test_ids: Optional[list[str]] = None


@router.post("/api/scans/{scan_id}/policy/generate", response_model=PolicyResponse)
def generate_policy(scan_id: str) -> PolicyResponse:
    report = get_report_or_404(scan_id)
    if report.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Scan has not completed yet.")

    policy = generate_least_privilege_policy(report)
    val = validate_policy(policy)
    yaml_text = to_yaml(policy)
    store().save_policy(scan_id, yaml_text)

    return PolicyResponse(policy=policy, yaml=yaml_text, validation=val)


@router.get("/api/scans/{scan_id}/policy", response_model=PolicyResponse)
def get_policy(scan_id: str) -> PolicyResponse:
    report = get_report_or_404(scan_id)
    yaml_text = store().get_policy(scan_id)

    if not yaml_text:
        policy = generate_least_privilege_policy(report)
        yaml_text = to_yaml(policy)
        store().save_policy(scan_id, yaml_text)
        val = validate_policy(policy)
        return PolicyResponse(policy=policy, yaml=yaml_text, validation=val)

    policy, val = from_yaml(yaml_text)
    if not policy:
        # Fallback to fresh generation if saved YAML was invalid
        policy = generate_least_privilege_policy(report)
        yaml_text = to_yaml(policy)
        val = validate_policy(policy)

    return PolicyResponse(policy=policy, yaml=yaml_text, validation=val)


@router.post("/api/scans/{scan_id}/policy/validate", response_model=PolicyValidationResult)
def validate_policy_endpoint(scan_id: str, req: PolicyValidateRequest) -> PolicyValidationResult:
    get_report_or_404(scan_id)

    if req.yaml:
        _, val = from_yaml(req.yaml)
        return val
    elif req.policy:
        return validate_policy(req.policy)
    else:
        raise ApiError(400, "MISSING_POLICY_PAYLOAD", "Either 'yaml' or 'policy' must be provided.")


@router.post("/api/scans/{scan_id}/policy/test")
def test_policy_endpoint(scan_id: str, req: PolicyTestRequest) -> dict[str, Any]:
    report = get_report_or_404(scan_id)
    files = store().get_files(scan_id)

    policy: Optional[SkillPolicy] = None
    if req.yaml:
        policy, val = from_yaml(req.yaml)
        if not val.valid or not policy:
            raise ApiError(422, "POLICY_SCHEMA_INVALID", "Cannot simulate test with an invalid policy.")
    elif req.policy:
        val = validate_policy(req.policy)
        if not val.valid:
            raise ApiError(422, "POLICY_SCHEMA_INVALID", "Cannot simulate test with an invalid policy.")
        policy = SkillPolicy.model_validate(req.policy)
    else:
        yaml_text = store().get_policy(scan_id)
        if yaml_text:
            policy, _ = from_yaml(yaml_text)
        if not policy:
            policy = generate_least_privilege_policy(report)

    # Filter tests
    tests_to_run = report.tests
    if req.test_ids:
        tests_to_run = [t for t in report.tests if t.test_id in req.test_ids]

    results = simulate_policy_scenarios(policy, tests_to_run, files)
    return {
        "scan_id": scan_id,
        "policy_id": policy.policy_id,
        "results": results,
    }


@router.get("/api/scans/{scan_id}/policy/export")
def export_policy(scan_id: str):
    get_report_or_404(scan_id)
    yaml_text = store().get_policy(scan_id)
    if not yaml_text:
        report = get_report_or_404(scan_id)
        policy = generate_least_privilege_policy(report)
        yaml_text = to_yaml(policy)
        store().save_policy(scan_id, yaml_text)

    # Ensure it's valid before export
    _, val = from_yaml(yaml_text)
    if not val.valid:
        raise ApiError(422, "POLICY_SCHEMA_INVALID", "Policy failed validation and cannot be exported.")

    filename = f"SKILL_POLICY-{scan_id}.yaml"
    return PlainTextResponse(
        yaml_text,
        media_type="text/yaml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
