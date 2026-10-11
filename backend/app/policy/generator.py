"""Deterministic least-privilege policy proposal from scan findings and the capability passport.

No model is used here; every proposal is labelled ``deterministic_fallback``. Each
granted or denied capability is explained by ``policy_rationale`` and linked to
the finding IDs that motivated it.
"""

from __future__ import annotations

import secrets

from ..schemas import Finding, ScanReport, utcnow
from .schema import PolicyLimits, PolicyRationale, SkillPolicy

WORKSPACE_PATTERN = "workspace/**"
OUTBOUND_CATEGORIES = {"data_exfiltration", "secret_disclosure"}
CAPABILITY_CATEGORIES = {"capability_expansion", "role_hijack", "instruction_override"}


def _ids(findings: list[Finding], categories: set[str]) -> list[str]:
    return [f.finding_id for f in findings if f.category in categories]


def generate_least_privilege_policy(report: ScanReport) -> SkillPolicy:
    """Derive a conservative, deny-by-default policy proposal from scan results."""
    outbound_ids = _ids(report.findings, OUTBOUND_CATEGORIES)
    capability_ids = _ids(report.findings, CAPABILITY_CATEGORIES)

    forbidden = {"read_canary_file", "send_sensitive_payload"}
    if outbound_ids:
        forbidden.add("send_mock_request")
    if capability_ids:
        forbidden.add("request_capability")

    skill_paths = sorted({f.relative_path for f in report.files if f.scanned and not f.relative_path.startswith(".")})
    return SkillPolicy(
        policy_id=f"policy_{secrets.token_hex(6)}",
        name=f"{report.skill_name or 'Skill'} least-privilege policy",
        source_scan_ids=[report.scan_id],
        default_action="BLOCK",
        allowed_tools=["list_mock_resources", "read_public_file", "write_mock_file"],
        allowed_domains=[],
        allowed_file_paths=skill_paths + [WORKSPACE_PATTERN],
        forbidden_actions=sorted(forbidden),
        limits=PolicyLimits(max_mock_requests_per_test=0, max_file_reads_per_test=20),
        metadata={
            "generated_by": "SkillSentry",
            "generator_mode": "deterministic_fallback",
            "policy_schema_version": "1.0",
            "created_at": utcnow(),
        },
    )


def policy_rationale(report: ScanReport, policy: SkillPolicy) -> tuple[list[PolicyRationale], list[str]]:
    """Explain each field of a generated policy; return (rationale, review warnings)."""
    outbound_ids = _ids(report.findings, OUTBOUND_CATEGORIES)
    capability_ids = _ids(report.findings, CAPABILITY_CATEGORIES)
    out: list[PolicyRationale] = [
        PolicyRationale(field="default_action", value="BLOCK",
                        reason="Unknown tools, paths and destinations are denied unless explicitly listed."),
        PolicyRationale(field="allowed_file_paths", value=", ".join(policy.allowed_file_paths),
                        reason="The skill may read its own scanned files and read/write the mock workspace."),
        PolicyRationale(field="forbidden_actions", value="read_canary_file",
                        reason="Secret material is never needed by a skill; canary reads are always denied."),
    ]
    if "send_mock_request" in policy.forbidden_actions:
        out.append(PolicyRationale(
            field="forbidden_actions", value="send_mock_request",
            reason="Findings instruct the agent to disclose secrets or send data externally.",
            finding_ids=outbound_ids,
        ))
    else:
        out.append(PolicyRationale(
            field="allowed_domains", value="[] (none)",
            reason="No outbound destination is required by evidence; outbound mock requests are not granted.",
        ))
    if "request_capability" in policy.forbidden_actions:
        out.append(PolicyRationale(
            field="forbidden_actions", value="request_capability",
            reason="Findings try to expand capabilities or override the agent's rules.",
            finding_ids=capability_ids,
        ))

    warnings: list[str] = []
    dests = (report.passport.destinations_mentioned if report.passport else []) or []
    if dests:
        warnings.append(
            "Destinations mentioned in the skill were not granted: " + ", ".join(dests[:5])
            + ". Add a bare domain to allowed_domains only if the declared purpose genuinely needs it."
        )
    declared = " ".join((report.passport.declared_capabilities if report.passport else []) or []).lower()
    if any(k in declared for k in ("web", "http", "network", "fetch", "api")) and not policy.allowed_domains:
        warnings.append("The skill declares network-related capabilities, but this policy grants no destinations; "
                        "review whether that blocks the declared purpose.")
    return out, warnings
