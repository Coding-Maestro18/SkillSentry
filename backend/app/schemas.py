"""Shared data contracts and Pydantic schemas for SkillSentry.
Reflects Section 7 of architecture.md.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# --- Health & Status Schemas ---

class ModelStatus(BaseModel):
    configured: bool = False
    mode: str = "offline"  # "local", "hosted", "offline"
    model_name: Optional[str] = None
    available: bool = False
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    version: str = "0.1.0"
    model_adapter: ModelStatus


# --- Finding Schema (Section 7.1) ---

class Finding(BaseModel):
    finding_id: str
    category: Literal[
        "invisible_unicode",
        "homoglyph_confusable",
        "html_comment",
        "suspicious_whitespace",
        "excessive_capability",
        "instruction_conflict",
        "structural_anomaly",
        "model_flagged"
    ]
    severity: Literal["low", "medium", "high", "critical", "info"]
    title: str
    source_file: str
    line_start: Optional[int] = None
    column_start: Optional[int] = None
    line_end: Optional[int] = None
    column_end: Optional[int] = None
    evidence: str
    observed_fact: str
    interpretation: Optional[str] = None
    detector: str  # e.g. "deterministic_unicode_scanner", "static_rules", "open_weight_model"
    model_interpretation: Optional[str] = None
    status: Literal["confirmed", "needs_review", "dismissed", "mitigated"] = "needs_review"
    related_test_ids: List[str] = Field(default_factory=list)


# --- Test Case & Simulation Schemas (Section 7.2, 7.3) ---

class TestCase(BaseModel):
    test_id: str
    suite_version: str = "1.0"
    name: str
    purpose: str
    source_finding_ids: List[str] = Field(default_factory=list)
    setup_fixture: Dict[str, Any] = Field(default_factory=dict)
    tool_sequence: List[Dict[str, Any]] = Field(default_factory=list)
    expected_policy_decisions: List[Literal["ALLOW", "BLOCK", "FLAG"]] = Field(default_factory=list)
    expected_outcome: str
    validation_status: Literal["valid", "invalid", "untested"] = "valid"


class TraceEvent(BaseModel):
    event_id: str
    test_id: str
    sequence_number: int
    tool_name: str
    sanitized_arguments: Dict[str, Any]
    policy_decision: Literal["ALLOW", "BLOCK", "FLAG"]
    decision_reason: str
    mock_result_summary: str
    timestamp: str


# --- Scan & Inventory Schemas ---

class FileInventoryItem(BaseModel):
    file_id: str
    relative_path: str
    size_bytes: int
    scanned: bool = True
    skip_reason: Optional[str] = None


class CapabilityPassport(BaseModel):
    declared_purpose: Optional[str] = None
    declared_tools: List[str] = Field(default_factory=list)
    inferred_capabilities: List[str] = Field(default_factory=list)
    requested_secrets: List[str] = Field(default_factory=list)
    network_targets: List[str] = Field(default_factory=list)
    filesystem_access: List[str] = Field(default_factory=list)


class ScanResponse(BaseModel):
    scan_id: str
    status: Literal["queued", "analyzing", "simulating", "completed", "failed"]
    created_at: str
    findings_count: int = 0
    files_count: int = 0
