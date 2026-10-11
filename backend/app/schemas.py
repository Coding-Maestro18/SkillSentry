"""Shared data contracts.

Single source of truth for API responses, analyzer output and stored artifacts.
The frontend mirrors these in ``frontend/src/types/index.ts``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Severity(str, Enum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"


SEVERITY_ORDER = {
    Severity.informational: 0,
    Severity.low: 1,
    Severity.medium: 2,
    Severity.high: 3,
}


class Detector(str, Enum):
    static_rules = "deterministic_static_rules"
    unicode_scanner = "deterministic_unicode_scanner"
    parser = "deterministic_parser"
    model = "open_weight_model"
    harness = "mock_harness"


class EvidenceType(str, Enum):
    observed = "observed"
    rule_based = "rule_based"
    model_interpretation = "model_interpretation"
    simulated = "simulated"
    user_confirmed = "user_confirmed"


class FindingStatus(str, Enum):
    needs_review = "needs_review"
    confirmed = "confirmed"
    dismissed = "dismissed"


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    FLAG = "FLAG"


class ScanState(str, Enum):
    queued = "queued"
    validating = "validating"
    parsing = "parsing"
    analyzing = "analyzing"
    generating_tests = "generating_tests"
    simulating = "simulating"
    reporting = "reporting"
    completed = "completed"
    failed = "failed"


# ---------------------------------------------------------------------------
# Files and annotations
# ---------------------------------------------------------------------------


class FileEntry(BaseModel):
    file_id: str
    relative_path: str
    size_bytes: int
    scanned: bool
    skip_reason: Optional[str] = None
    role: Literal["skill_md", "reference", "script", "asset", "other"] = "other"
    encoding: Optional[str] = None
    line_ending: Optional[str] = None
    sha256: str
    warnings: list[str] = Field(default_factory=list)


class FileAnnotation(BaseModel):
    annotation_id: str
    file_id: str
    relative_path: str
    line: int
    column: int
    end_line: int
    end_column: int
    start_offset: int
    end_offset: int
    annotation_type: Literal[
        "invisible_char",
        "bidi_control",
        "tag_char",
        "confusable",
        "html_comment",
        "hidden_html",
        "whitespace_anomaly",
        "unusual_space",
    ]
    code_point: Optional[str] = None
    unicode_name: Optional[str] = None
    escaped_excerpt: str
    detector_id: str
    severity: Severity
    notes: str = ""
    skeleton: Optional[str] = None  # confusable comparison only; never replaces source


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    finding_id: str
    rule_id: str
    category: str
    severity: Severity
    title: str
    source_file: str
    line_start: int
    column_start: int
    line_end: int
    column_end: int
    evidence: str
    observed_fact: str
    interpretation: str
    remediation: str = ""
    detector: Detector
    evidence_type: EvidenceType
    model_interpretation: Optional[str] = None
    model_confidence: Optional[Literal["low", "medium", "high"]] = None
    status: FindingStatus = FindingStatus.needs_review
    related_test_ids: list[str] = Field(default_factory=list)
    annotation_ids: list[str] = Field(default_factory=list)
    occurrences: int = 1
    decoded_payload: Optional[str] = None
    decoder: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tests and traces
# ---------------------------------------------------------------------------

ToolName = Literal[
    "read_public_file",
    "read_canary_file",
    "write_mock_file",
    "send_mock_request",
    "list_mock_resources",
    "request_capability",
]


class ToolCall(BaseModel):
    tool: ToolName
    args: dict[str, str] = Field(default_factory=dict)


class TestTrigger(BaseModel):
    """What in the skill content makes the simulated agent perform the tool sequence.

    * ``always`` – benign control; the sequence always runs.
    * ``rule`` – runs when the (possibly revised) skill still produces a finding with one of ``rule_ids``.
    * ``excerpt`` – runs when ``excerpt`` still occurs in the skill text (used for model-proposed tests).
    """

    type: Literal["always", "rule", "excerpt"]
    rule_ids: list[str] = Field(default_factory=list)
    min_severity: Severity = Severity.low
    excerpt: Optional[str] = None


class TestCase(BaseModel):
    test_id: str
    suite_version: str
    name: str
    purpose: str
    kind: Literal["benign_control", "adversarial"]
    origin: Literal["fixed_suite", "model_proposed"]
    source_finding_ids: list[str] = Field(default_factory=list)
    setup_fixture: str
    trigger: TestTrigger
    tool_sequence: list[ToolCall]
    expected_policy_decisions: list[PolicyDecision]
    expected_outcome: str
    validation_status: Literal["valid", "rejected"] = "valid"
    validation_notes: list[str] = Field(default_factory=list)


class TraceEvent(BaseModel):
    event_id: str
    test_id: str
    sequence_number: int
    tool_name: str
    sanitized_arguments: dict[str, str]
    policy_decision: PolicyDecision
    decision_reason: str
    mock_result_summary: str
    timestamp: str = Field(default_factory=utcnow)


class TestResult(BaseModel):
    test_id: str
    status: Literal["pass", "fail", "needs_review", "skipped"]
    triggered: bool
    summary: str
    events: list[TraceEvent] = Field(default_factory=list)
    ran_at: str = Field(default_factory=utcnow)


# ---------------------------------------------------------------------------
# Model provenance and output
# ---------------------------------------------------------------------------


class ModelInfo(BaseModel):
    provider: str
    name: str
    revision: str
    license: str
    inference_mode: Literal["local", "remote", "cached-replay", "disabled", "unavailable"]
    adapter_version: str
    status: Literal["ok", "unavailable", "disabled", "invalid_output", "timeout", "error"]
    status_detail: str = ""
    schema_valid_responses: int = 0
    total_responses: int = 0
    latency_ms: Optional[int] = None


class CapabilityPassport(BaseModel):
    skill_name: Optional[str]
    description: Optional[str]
    files_discovered: list[str]
    references: list[str]
    declared_capabilities: list[str]
    inferred_capabilities_model: list[str]
    inferred_capabilities_rules: list[str]
    observed_simulated_actions: list[str]
    sensitive_items_mentioned: list[str]
    destinations_mentioned: list[str]
    unresolved_concerns: list[str]
    unscanned_files: list[str]


class ScanSummary(BaseModel):
    files_scanned: int
    files_skipped: int
    findings_by_severity: dict[str, int]
    findings_by_category: dict[str, int]
    hidden_content_counts: dict[str, int]
    tests_total: int
    tests_by_status: dict[str, int]
    headline: str


class ScanReport(BaseModel):
    scan_id: str
    parent_scan_id: Optional[str] = None
    created_at: str
    input_kind: Literal["zip", "text", "revision"]
    status: ScanState
    stage_detail: str = ""
    error: Optional[dict[str, Any]] = None
    skill_name: Optional[str] = None
    skill_description: Optional[str] = None
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    files: list[FileEntry] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    annotations: list[FileAnnotation] = Field(default_factory=list)
    tests: list[TestCase] = Field(default_factory=list)
    rejected_tests: list[TestCase] = Field(default_factory=list)
    results: list[TestResult] = Field(default_factory=list)
    passport: Optional[CapabilityPassport] = None
    summary: Optional[ScanSummary] = None
    model: Optional[ModelInfo] = None
    analyzer_version: str = ""
    ruleset_version: str = ""
    unicode_version: str = ""
    confusables_version: str = ""
    suite_version: str = ""
    timings_ms: dict[str, int] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class ScanStatus(BaseModel):
    scan_id: str
    status: ScanState
    stage_detail: str
    error: Optional[dict[str, Any]] = None
    parent_scan_id: Optional[str] = None


class FileView(BaseModel):
    file_id: str
    relative_path: str
    raw: str
    reveal: list[list[dict[str, str]]]  # per line: segments {text, kind, label}
    preview: str
    annotations: list[FileAnnotation]
    preview_note: str


class FixSuggestion(BaseModel):
    origin: Literal["model", "deterministic"]
    model_status: str
    finding_ids: list[str]
    rationale: list[str]
    revised_files: dict[str, str]
    diffs: dict[str, str]


class RerunRequest(BaseModel):
    files: dict[str, str]  # relative_path -> revised content (copy; original untouched)


class Comparison(BaseModel):
    original_scan_id: str
    revised_scan_id: str
    suite_version: str
    same_suite: bool
    tests: list[dict[str, Any]]
    findings_before: dict[str, int]
    findings_after: dict[str, int]
    resolved_findings: list[str]
    remaining_findings: list[str]
    new_findings: list[str]
    verdict: str
