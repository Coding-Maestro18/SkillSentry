"""Graph generation for multi-skill attack chains."""

from __future__ import annotations

from typing import Optional

from ..schemas import SEVERITY_ORDER, ScanReport, TestResult
from .schemas import CampaignEdge, CampaignNode

MAX_FINDINGS_PER_SKILL = 3


def _skill_nodes(
    report: ScanReport, role: str, nodes: list[CampaignNode], edges: list[CampaignEdge]
) -> tuple[str, list[str]]:
    """Add the skill node and its most severe findings; return (skill node id, finding node ids)."""
    skill_id = f"skill-{role}"
    nodes.append(CampaignNode(
        node_id=skill_id,
        node_type="skill",
        scan_id=report.scan_id,
        label=report.skill_name or f"Skill {role.upper()}",
        provenance="observed",
        metadata={
            "role": role.upper(),
            "description": report.skill_description or "",
            "file_count": len(report.files),
            "files_scanned": sum(1 for f in report.files if f.scanned),
            "finding_count": len(report.findings),
        },
    ))
    top = sorted(report.findings, key=lambda f: SEVERITY_ORDER[f.severity], reverse=True)[:MAX_FINDINGS_PER_SKILL]
    finding_ids = []
    for f in top:
        # Finding IDs are only unique within a scan, so node IDs are scoped by role.
        f_node = f"finding-{role}-{f.finding_id}"
        finding_ids.append(f_node)
        nodes.append(CampaignNode(
            node_id=f_node,
            node_type="finding",
            scan_id=report.scan_id,
            finding_id=f.finding_id,
            label=f.title,
            provenance="deterministic" if f.evidence_type.value != "model_interpretation" else "model_hypothesis",
            metadata={
                "severity": f.severity.value,
                "category": f.category,
                "location": f"{f.source_file}:{f.line_start}" if f.source_file else "",
            },
        ))
        edges.append(CampaignEdge(
            source_node_id=skill_id, target_node_id=f_node, edge_type="contains_finding",
            label="contains", provenance="deterministic",
        ))
    return skill_id, finding_ids


def build_campaign_graph(
    report_a: ScanReport,
    report_b: ScanReport,
    fixture_id: str,
    results: Optional[list[TestResult]] = None,
    a_steps: int = 0,
) -> tuple[list[CampaignNode], list[CampaignEdge]]:
    """Link two scanned skills via an explicit handoff; add trace nodes once simulated.

    ``a_steps`` is the number of leading trace events performed on behalf of Skill A;
    the remaining events belong to Skill B.
    """
    nodes: list[CampaignNode] = []
    edges: list[CampaignEdge] = []

    skill_a, findings_a = _skill_nodes(report_a, "a", nodes, edges)

    handoff_id = f"handoff-{fixture_id}"
    nodes.append(CampaignNode(
        node_id=handoff_id,
        node_type="handoff",
        fixture_id=fixture_id,
        label=f"Handoff fixture {fixture_id}",
        provenance="user_defined",
        metadata={"description": "Inert content passed from Skill A to Skill B in the simulation"},
    ))
    edges.append(CampaignEdge(
        source_node_id=skill_a, target_node_id=handoff_id, edge_type="produces_handoff",
        label="produces", provenance="user_defined",
    ))

    skill_b, findings_b = _skill_nodes(report_b, "b", nodes, edges)
    edges.append(CampaignEdge(
        source_node_id=handoff_id, target_node_id=skill_b, edge_type="consumes_handoff",
        label="consumes", provenance="user_defined",
    ))

    for r in results or []:
        for idx, ev in enumerate(r.events):
            owner = skill_a if idx < a_steps else skill_b
            action_id = f"action-{ev.event_id}"
            nodes.append(CampaignNode(
                node_id=action_id,
                node_type="mock_action",
                label=f"{ev.tool_name} → {ev.policy_decision.value}",
                action_tool=ev.tool_name,
                provenance="simulated_trace",
                metadata={"decision": ev.policy_decision.value, "reason": ev.decision_reason,
                          "trace_event_id": ev.event_id, "owner": "A" if owner == skill_a else "B"},
            ))
            edges.append(CampaignEdge(
                source_node_id=owner, target_node_id=action_id, edge_type="requests_action",
                label="requests", provenance="simulated_trace",
            ))
        if a_steps and r.events and findings_a:
            # The most severe Skill A finding motivated the simulated handoff write.
            edges.append(CampaignEdge(
                source_node_id=findings_a[0], target_node_id=handoff_id, edge_type="observed_in_trace",
                label="motivates handoff", provenance="simulated_trace",
            ))
        ce = r.canary_event
        if ce and ce.exact_match:
            canary_id = f"canary-{ce.canary_event_id}"
            nodes.append(CampaignNode(
                node_id=canary_id,
                node_type="canary_match",
                label="Synthetic canary matched in mock payload",
                provenance="simulated_trace",
                metadata={"status": ce.status, "digest": ce.token_digest},
            ))
            if ce.sink_trace_event_id:
                edges.append(CampaignEdge(
                    source_node_id=f"action-{ce.sink_trace_event_id}", target_node_id=canary_id,
                    edge_type="observed_in_trace", label="payload contains canary", provenance="simulated_trace",
                ))

    return nodes, edges
