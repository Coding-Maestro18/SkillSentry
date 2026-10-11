"""Strict schemas for model output. Anything that fails validation is rejected."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")
    category: Literal[
        "instruction_override", "secret_disclosure", "data_exfiltration", "capability_expansion",
        "concealment", "role_hijack", "purpose_mismatch", "hidden_instruction", "other",
    ]
    title: str = Field(max_length=200)
    rationale: str = Field(max_length=1500)
    evidence_excerpt: str = Field(max_length=500)
    source_file: str = Field(max_length=300)
    severity: Literal["informational", "low", "medium", "high"]
    confidence: Literal["low", "medium", "high"]


class ModelToolCall(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tool: str = Field(max_length=60)
    args: dict[str, str] = Field(default_factory=dict)


class ModelTestHypothesis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(max_length=120)
    purpose: str = Field(max_length=600)
    evidence_excerpt: str = Field(max_length=500)
    tool_sequence: list[ModelToolCall] = Field(max_length=6)
    expected_policy_decisions: list[Literal["ALLOW", "BLOCK", "FLAG"]] = Field(max_length=6)


class ModelAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    summary: str = Field(default="", max_length=2000)
    declared_purpose: str = Field(default="", max_length=500)
    findings: list[ModelFinding] = Field(default_factory=list, max_length=20)
    inferred_capabilities: list[str] = Field(default_factory=list, max_length=20)
    test_hypotheses: list[ModelTestHypothesis] = Field(default_factory=list, max_length=8)


class ModelFixFile(BaseModel):
    model_config = ConfigDict(extra="ignore")
    path: str = Field(max_length=300)
    revised_content: str = Field(max_length=200_000)
    rationale: str = Field(max_length=1500)


class ModelFix(BaseModel):
    model_config = ConfigDict(extra="ignore")
    files: list[ModelFixFile] = Field(max_length=10)


class ModelAdaptiveCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(max_length=120)
    hypothesis: str = Field(max_length=600)
    target_finding_id: str = Field(default="", max_length=60)
    target_category: str = Field(default="general", max_length=60)
    tool_sequence: list[ModelToolCall] = Field(max_length=6)
    expected_policy_decisions: list[Literal["ALLOW", "BLOCK", "FLAG"]] = Field(max_length=6)


class ModelAdaptiveProposals(BaseModel):
    model_config = ConfigDict(extra="ignore")
    candidates: list[ModelAdaptiveCandidate] = Field(default_factory=list, max_length=6)
