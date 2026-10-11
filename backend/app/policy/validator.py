"""Deterministic semantic and schema validator for SKILL_POLICY.yaml."""

from __future__ import annotations

import posixpath
import re
from typing import Any

from .schema import PolicyValidationError, PolicyValidationResult, SkillPolicy


ALLOWED_TOOL_REGISTRY = {
    "read_public_file",
    "read_canary_file",
    "write_mock_file",
    "send_mock_request",
    "list_mock_resources",
    "request_capability",
}

ALLOWED_FORBIDDEN_ACTIONS = {
    "read_canary_file",
    "send_sensitive_payload",
    "write_mock_file",
    "request_capability",
    "shell_execution",
    "network_exfiltration",
}

DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$|"
    r"^(?:localhost|mock\.local|localhost\.mock)$"
)


def validate_policy(policy_data: dict[str, Any] | SkillPolicy) -> PolicyValidationResult:
    """Validate a policy object or dictionary according to least-privilege rules."""
    errors: list[PolicyValidationError] = []
    warnings: list[str] = []

    if isinstance(policy_data, dict):
        try:
            policy = SkillPolicy.model_validate(policy_data)
        except Exception as exc:
            errors.append(PolicyValidationError(code="POLICY_SCHEMA_INVALID", field="root", message=str(exc)))
            return PolicyValidationResult(
                valid=False,
                errors=errors,
                warnings=warnings,
                enforcement_status="not_applicable",
            )
    else:
        policy = policy_data

    # Default action must be BLOCK (least privilege)
    if policy.default_action not in ("BLOCK", "FLAG"):
        errors.append(PolicyValidationError(
            code="INVALID_DEFAULT_ACTION",
            field="default_action",
            message=f"Default action must be BLOCK or FLAG for least privilege; got '{policy.default_action}'",
        ))

    # Tool checks
    for idx, tool in enumerate(policy.allowed_tools):
        if tool == "*":
            errors.append(PolicyValidationError(
                code="UNRESTRICTED_WILDCARD",
                field=f"allowed_tools[{idx}]",
                message="Unrestricted wildcard '*' is forbidden for allowed_tools.",
            ))
        elif tool not in ALLOWED_TOOL_REGISTRY:
            errors.append(PolicyValidationError(
                code="UNKNOWN_TOOL",
                field=f"allowed_tools[{idx}]",
                message=f"Unknown tool identifier '{tool}'. Must be one of {sorted(ALLOWED_TOOL_REGISTRY)}.",
            ))

    if not policy.allowed_tools:
        warnings.append("Empty allowed_tools: all tool actions will be denied by default.")

    # Domain checks
    for idx, domain in enumerate(policy.allowed_domains):
        clean = domain.strip().lower()
        if clean == "*":
            errors.append(PolicyValidationError(
                code="UNRESTRICTED_WILDCARD",
                field=f"allowed_domains[{idx}]",
                message="Unrestricted wildcard '*' is forbidden for allowed_domains.",
            ))
        elif "://" in clean or "/" in clean or "@" in clean or ":" in clean:
            errors.append(PolicyValidationError(
                code="INVALID_DOMAIN_FORMAT",
                field=f"allowed_domains[{idx}]",
                message=f"Domain must be a bare host/domain name (no scheme, path, port or credentials): '{domain}'",
            ))
        elif not DOMAIN_REGEX.match(clean):
            errors.append(PolicyValidationError(
                code="MALFORMED_DOMAIN",
                field=f"allowed_domains[{idx}]",
                message=f"Invalid domain format: '{domain}'",
            ))

    # File path checks
    for idx, path_pat in enumerate(policy.allowed_file_paths):
        if path_pat == "*" or path_pat == "**":
            errors.append(PolicyValidationError(
                code="UNRESTRICTED_WILDCARD",
                field=f"allowed_file_paths[{idx}]",
                message="Unrestricted wildcard '*' covering entire filesystem is forbidden.",
            ))
        norm = posixpath.normpath(path_pat.replace("\\", "/"))
        if norm.startswith(("/", "\\")) or ":" in norm:
            errors.append(PolicyValidationError(
                code="ABSOLUTE_PATH_FORBIDDEN",
                field=f"allowed_file_paths[{idx}]",
                message=f"Absolute path patterns are forbidden: '{path_pat}'",
            ))
        if norm.startswith("..") or "/../" in norm or norm.endswith("/.."):
            errors.append(PolicyValidationError(
                code="PATH_TRAVERSAL_FORBIDDEN",
                field=f"allowed_file_paths[{idx}]",
                message=f"Path traversal ('..') is forbidden: '{path_pat}'",
            ))

    # Forbidden action checks
    for idx, action in enumerate(policy.forbidden_actions):
        if action not in ALLOWED_FORBIDDEN_ACTIONS and action not in ALLOWED_TOOL_REGISTRY:
            errors.append(PolicyValidationError(
                code="UNKNOWN_FORBIDDEN_ACTION",
                field=f"forbidden_actions[{idx}]",
                message=f"Unrecognized action '{action}'.",
            ))

    generator_mode = policy.metadata.get("generator_mode", "deterministic_fallback")
    is_valid = len(errors) == 0

    return PolicyValidationResult(
        valid=is_valid,
        schema_version=policy.schema_version,
        errors=errors,
        warnings=warnings,
        source_finding_ids=[],
        generator_mode=generator_mode,
        enforcement_status="not_tested",
    )
