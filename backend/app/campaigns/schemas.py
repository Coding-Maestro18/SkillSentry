"""Data contracts for Multi-skill attack chains (Feature A)."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from ..schemas import Finding, TestResult, TraceEvent, utcnow


NodeProvenance = Literal[
    "observed",
    "deterministic",
    "model_hypothesis",
    "user_defined",
    "simulated_trace",
]

EdgeType = Literal[
    "contains_finding",
    "produces_handoff",
    "consumes_handoff",
    "requests_action",
    "observed_in_trace",
    "related_to",
]

ChainStatus = Literal[
    "candidate",
    "reproduced_in_simulation",
    "not_reproduced",
    "needs_review",
]


class CampaignNode(BaseModel):
    node_id: str
    node_type: Literal["skill", "finding", "handoff", "mock_action", "canary_match"]
    label: str
    scan_id: Optional[str] = None
    finding_id: Optional[str] = None
    fixture_id: Optional[str] = None
    action_tool: Optional[str] = None
    provenance: NodeProvenance = "deterministic"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CampaignEdge(BaseModel):
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType
    label: Optional[str] = None
    provenance: NodeProvenance = "deterministic"


class CreateCampaignRequest(BaseModel):
    scan_ids: list[str]
    handoff_fixture_id: Optional[str] = "handoff_fixture_001"
    handoff_content: Optional[str] = None
    campaign_name: Optional[str] = None


class Campaign(BaseModel):
    campaign_id: str
    campaign_name: str
    created_at: str = Field(default_factory=utcnow)
    status: Literal["ready", "simulating", "completed", "failed"] = "ready"
    scan_ids: list[str]
    campaign_version: str = "1.0"
    handoff_fixture_id: str
    handoff_fixture_content: str = ""
    chain_status: ChainStatus = "candidate"
    status_detail: str = "Not simulated yet; graph shows declared relationships only."
    nodes: list[CampaignNode] = Field(default_factory=list)
    edges: list[CampaignEdge] = Field(default_factory=list)
    test_ids: list[str] = Field(default_factory=list)
    trace_event_ids: list[str] = Field(default_factory=list)
    results: list[TestResult] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CampaignReport(BaseModel):
    campaign: Campaign
    participating_scans: list[dict[str, Any]]
    findings_by_scan: dict[str, list[Finding]]
    traces: list[TraceEvent]
