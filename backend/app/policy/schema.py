"""SKILL_POLICY.yaml schema definitions."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from ..schemas import ToolName


PolicyAction = Literal["ALLOW", "BLOCK", "FLAG"]


class PolicyLimits(BaseModel):
    max_mock_requests_per_test: int = 0
    max_file_reads_per_test: int = 50


class PolicyMetadata(BaseModel):
    generated_by: str = "SkillSentry"
    generator_mode: Literal["model_proposal", "deterministic_fallback"] = "deterministic_fallback"
    policy_schema_version: str = "1.0"
    created_at: Optional[str] = None
    notes: Optional[str] = None


class SkillPolicy(BaseModel):
    schema_version: str = "1.0"
    policy_id: str
    name: str
    source_scan_ids: list[str] = Field(default_factory=list)
    source_campaign_id: Optional[str] = None
    default_action: PolicyAction = "BLOCK"
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_domains: list[str] = Field(default_factory=list)
    allowed_file_paths: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    limits: dict[str, int] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    generator_mode: Literal["model_proposal", "deterministic_fallback"] = "deterministic_fallback"
    enforcement_status: Literal["not_tested", "mock_tested", "not_applicable"] = "not_tested"
