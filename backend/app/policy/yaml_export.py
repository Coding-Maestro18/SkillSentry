"""YAML serialization and deserialization for SKILL_POLICY."""

from __future__ import annotations

import yaml
from typing import Any

from .schema import PolicyValidationError, PolicyValidationResult, SkillPolicy
from .validator import validate_policy


def to_yaml(policy: SkillPolicy) -> str:
    """Serialize a SkillPolicy object to valid YAML format."""
    data = policy.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=False, default_flow_style=False)


def from_yaml(yaml_str: str) -> tuple[SkillPolicy | None, PolicyValidationResult]:
    """Parse YAML text and deterministically validate the resulting policy."""
    try:
        raw_data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        err = PolicyValidationError(
            code="YAML_PARSE_ERROR",
            field="syntax",
            message=f"YAML parsing error: {exc}",
        )
        return None, PolicyValidationResult(
            valid=False,
            schema_version="1.0",
            errors=[err],
            warnings=[],
            enforcement_status="not_applicable",
        )

    if not isinstance(raw_data, dict):
        err = PolicyValidationError(
            code="INVALID_YAML_ROOT",
            field="root",
            message="Policy YAML root must be a mapping/dictionary.",
        )
        return None, PolicyValidationResult(
            valid=False,
            schema_version="1.0",
            errors=[err],
            warnings=[],
            enforcement_status="not_applicable",
        )

    validation = validate_policy(raw_data)
    if not validation.valid:
        return None, validation

    policy = SkillPolicy.model_validate(raw_data)
    return policy, validation
