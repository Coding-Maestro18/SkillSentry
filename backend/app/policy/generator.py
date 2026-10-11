"""Least-privilege policy generator from scan findings and capability passport."""

from __future__ import annotations

import secrets
from typing import Optional

from ..schemas import ScanReport, Severity, utcnow
from .schema import PolicyLimits, PolicyMetadata, SkillPolicy


def generate_least_privilege_policy(report: ScanReport) -> SkillPolicy:
    """Derive a conservative, least-privilege policy proposal from scan results."""
    scan_id = report.scan_id
    policy_id = f"policy_{secrets.token_hex(6)}"
    name = f"{report.skill_name or 'Skill'} Least-Privilege Policy"

    allowed_tools = ["read_public_file", "list_mock_resources"]
    forbidden_actions = ["read_canary_file", "send_sensitive_payload"]
    allowed_domains: list[str] = []
    allowed_file_paths: list[str] = []

    # Check for file paths in scanned files
    safe_rel_paths: list[str] = []
    for f in report.files:
        if f.scanned and not f.relative_path.startswith("."):
            safe_rel_paths.append(f.relative_path)

    if safe_rel_paths:
        allowed_file_paths = sorted(set(safe_rel_paths))
    else:
        allowed_file_paths = ["references/**", "assets/**"]

    # Check findings for exfiltration or network activity
    has_exfil = any(
        "exfiltration" in f.category.lower()
        or "network" in f.category.lower()
        or "canary" in f.category.lower()
        or "secret" in f.category.lower()
        for f in report.findings
    )

    if has_exfil:
        forbidden_actions.append("send_mock_request")
        max_requests = 0
    else:
        # If passport has safe declared destinations
        if report.passport and report.passport.destinations_mentioned:
            for dest in report.passport.destinations_mentioned:
                dest_clean = dest.strip().lower()
                if "://" not in dest_clean and "/" not in dest_clean and dest_clean:
                    allowed_domains.append(dest_clean)
        max_requests = len(allowed_domains)

    # Capability writes
    has_unsafe_write = any(
        "write" in f.category.lower() and f.severity in (Severity.high, Severity.medium)
        for f in report.findings
    )
    if not has_unsafe_write:
        allowed_tools.append("write_mock_file")

    policy = SkillPolicy(
        schema_version="1.0",
        policy_id=policy_id,
        name=name,
        source_scan_ids=[scan_id],
        default_action="BLOCK",
        allowed_tools=sorted(set(allowed_tools)),
        allowed_domains=sorted(set(allowed_domains)),
        allowed_file_paths=allowed_file_paths,
        forbidden_actions=sorted(set(forbidden_actions)),
        limits={
            "max_mock_requests_per_test": max_requests,
            "max_file_reads_per_test": 20,
        },
        metadata={
            "generated_by": "SkillSentry",
            "generator_mode": "deterministic_fallback",
            "policy_schema_version": "1.0",
            "created_at": utcnow(),
            "source_finding_count": len(report.findings),
            "notes": "Generated least-privilege boundary proposal based on static findings and inventory.",
        },
    )

    return policy
