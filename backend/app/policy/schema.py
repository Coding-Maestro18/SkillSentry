"""SKILL_POLICY.yaml schema definitions.

Enforcement fields are strict: unknown keys are rejected so a model or an editor
cannot smuggle in fields the mock gate would silently ignore. Explanatory
rationale lives outside the policy file (see ``PolicyRationale``).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

PolicyAction = Literal["ALLOW", "BLOCK", "FLAG"]
GeneratorMode = Literal["model_proposal", "deterministic_fallback", "user_edited"]


class PolicyLimits(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_mock_requests_per_test: int = Field(default=0, ge=0, le=100)
    max_file_reads_per_test: int = Field(default=50, ge=0, le=1000)


class SkillPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    policy_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    source_scan_ids: list[str] = Field(default_factory=list)
    source_campaign_id: Optional[str] = None
    default_action: PolicyAction = "BLOCK"
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_file_paths: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    limits: PolicyLimits = Field(default_factory=PolicyLimits)
    # Informational only; never consulted by the gate.
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyRationale(BaseModel):
    """Why a policy field has its value; sidecar data, not part of SKILL_POLICY.yaml."""

    field: str
    value: str
    reason: str
    finding_ids: list[str] = Field(default_factory=list)


class PolicyValidationError(BaseModel):
    code: str
    field: str
    message: str


class PolicyValidationResult(BaseModel):
    valid: bool
    schema_version: str = "1.0"
    errors: list[PolicyValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_finding_ids: list[str] = Field(default_factory=list)
    generator_mode: GeneratorMode = "deterministic_fallback"
    enforcement_status: Literal["not_tested", "mock_tested", "not_applicable"] = "not_tested"
