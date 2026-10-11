"""Graph generation for Multi-skill attack chains."""

from __future__ import annotations

from typing import Optional

from ..schemas import ScanReport, TestResult
from .schemas import CampaignEdge, CampaignNode


def build_campaign_graph(
    report_a: ScanReport,
    report_b: ScanReport,
    fixture_id: str,
    results: Optional[list[TestResult]] = None,
) -> tuple[list[CampaignNode], list[CampaignEdge]]:
    """Build graph nodes and edges linking two scanned skills via a simulated handoff."""
    nodes: list[CampaignNode] = []
    edges: list[CampaignEdge] = []

    # Node: Skill A
    node_a_id = f"skill-{report_a.scan_id[:8]}"
    nodes.append(CampaignNode(
        node_id=node_a_id,
        node_type="skill",
        scan_id=report_a.scan_id,
        label=report_a.skill_name or f"Skill ({report_a.scan_id[:8]})",
        provenance="observed",
        metadata={"file_count": len(report_a.files), "finding_count": len(report_a.findings)},
    ))

    # Findings in Skill A (up to 3 most severe to keep graph readable)
    for f in report_a.findings[:3]:
        f_node_id = f"finding-{f.finding_id}"
        nodes.append(CampaignNode(
            node_id=f_node_id,
            node_type="finding",
            scan_id=report_a.scan_id,
            finding_id=f.finding_id,
            label=f"{f.title[:30]} ({f.severity.value})",
            provenance="deterministic",
            metadata={"severity": f.severity.value, "category": f.category},
        ))
        edges.append(CampaignEdge(
            source_node_id=node_a_id,
            target_node_id=f_node_id,
            edge_type="contains_finding",
            label="contains",
            provenance="deterministic",
        ))

    # Node: Handoff Fixture
    handoff_node_id = f"handoff-{fixture_id}"
    nodes.append(CampaignNode(
        node_id=handoff_node_id,
        node_type="handoff",
        fixture_id=fixture_id,
        label=f"Handoff ({fixture_id})",
        provenance="user_defined",
        metadata={"description": "Simulated intermediate artifact passing from Skill A to Skill B"},
    ))

    # Edge: Skill A produces handoff
    edges.append(CampaignEdge(
        source_node_id=node_a_id,
        target_node_id=handoff_node_id,
        edge_type="produces_handoff",
        label="produces artifact",
        provenance="user_defined",
    ))

    # Node: Skill B
    node_b_id = f"skill-{report_b.scan_id[:8]}"
    nodes.append(CampaignNode(
        node_id=node_b_id,
        node_type="skill",
        scan_id=report_b.scan_id,
        label=report_b.skill_name or f"Skill ({report_b.scan_id[:8]})",
        provenance="observed",
        metadata={"file_count": len(report_b.files), "finding_count": len(report_b.findings)},
    ))

    # Edge: Skill B consumes handoff
    edges.append(CampaignEdge(
        source_node_id=handoff_node_id,
        target_node_id=node_b_id,
        edge_type="consumes_handoff",
        label="consumes artifact",
        provenance="user_defined",
    ))

    # Findings in Skill B (up to 3)
    for f in report_b.findings[:3]:
        f_node_id = f"finding-{f.finding_id}"
        nodes.append(CampaignNode(
            node_id=f_node_id,
            node_type="finding",
            scan_id=report_b.scan_id,
            finding_id=f.finding_id,
            label=f"{f.title[:30]} ({f.severity.value})",
            provenance="deterministic",
            metadata={"severity": f.severity.value, "category": f.category},
        ))
        edges.append(CampaignEdge(
            source_node_id=node_b_id,
            target_node_id=f_node_id,
            edge_type="contains_finding",
            label="contains",
            provenance="deterministic",
        ))

    # If simulation results exist, append mock action and canary match nodes
    if results:
        for r in results:
            for ev in r.events:
                action_node_id = f"action-{ev.event_id}"
                nodes.append(CampaignNode(
                    node_id=action_node_id,
                    node_type="mock_action",
                    label=f"{ev.tool_name} → {ev.policy_decision.value}",
                    action_tool=ev.tool_name,
                    provenance="simulated_trace",
                    metadata={"decision": ev.policy_decision.value, "reason": ev.decision_reason},
                ))
                edges.append(CampaignEdge(
                    source_node_id=node_b_id,
                    target_node_id=action_node_id,
                    edge_type="requests_action",
                    label="simulated action",
                    provenance="simulated_trace",
                ))

            if r.canary_event and r.canary_event.exact_match:
                canary_node_id = f"canary-{r.canary_event.canary_event_id}"
                nodes.append(CampaignNode(
                    node_id=canary_node_id,
                    node_type="canary_match",
                    label="Canary Match Detected",
                    provenance="simulated_trace",
                    metadata={"status": r.canary_event.status, "digest": r.canary_event.token_digest},
                ))
                if r.events:
                    last_action_id = f"action-{r.events[-1].event_id}"
                    edges.append(CampaignEdge(
                        source_node_id=last_action_id,
                        target_node_id=canary_node_id,
                        edge_type="observed_in_trace",
                        label="leaks canary in trace",
                        provenance="simulated_trace",
                    ))

    return nodes, edges
