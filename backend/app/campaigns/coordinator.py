"""Campaign coordinator for multi-skill attack chains.

A campaign links two completed scans through an explicit, inert handoff fixture.
Simulation never executes either skill: each skill's half of the fixed chain
scenario is performed by the mock harness only when that skill's own scan has a
medium-or-higher finding that motivates it, so two benign skills do not produce
a "reproduced" chain.
"""

from __future__ import annotations

import secrets
from typing import Optional

from ..harness.runner import CANARY_PLACEHOLDER, run_test
from ..persistence.store import ScanStore
from ..schemas import SEVERITY_ORDER, Finding, PolicyDecision, ScanReport, ScanState, Severity, TestCase, TestTrigger, ToolCall
from .graph import build_campaign_graph
from .schemas import Campaign

_CAMPAIGNS: dict[str, Campaign] = {}
HANDOFF_PATH = "workspace/handoff.txt"
MAX_HANDOFF_CHARS = 2000


def _save(store: ScanStore, camp: Campaign) -> None:
    _CAMPAIGNS[camp.campaign_id] = camp
    store.save_artifact("campaigns", camp.campaign_id, camp.model_dump_json())


def get_campaign(campaign_id: str, store: Optional[ScanStore] = None) -> Optional[Campaign]:
    if campaign_id in _CAMPAIGNS:
        return _CAMPAIGNS[campaign_id]
    if store is not None:
        raw = store.get_artifact("campaigns", campaign_id)
        if raw:
            camp = Campaign.model_validate_json(raw)
            _CAMPAIGNS[campaign_id] = camp
            return camp
    return None


def list_campaigns(store: Optional[ScanStore] = None) -> list[Campaign]:
    if store is not None:
        for raw in store.list_artifacts("campaigns"):
            camp = Campaign.model_validate_json(raw)
            _CAMPAIGNS.setdefault(camp.campaign_id, camp)
    return sorted(_CAMPAIGNS.values(), key=lambda c: c.created_at, reverse=True)


def motivating_findings(report: ScanReport) -> list[Finding]:
    """Findings that justify simulating this skill's half of the chain (medium or higher)."""
    floor = SEVERITY_ORDER[Severity.medium]
    return [f for f in report.findings if SEVERITY_ORDER[f.severity] >= floor]


def create_campaign(
    store: ScanStore,
    scan_ids: list[str],
    handoff_fixture_id: str = "handoff_fixture_001",
    handoff_content: Optional[str] = None,
    campaign_name: Optional[str] = None,
) -> Campaign:
    """Create a campaign from two completed scans without rescanning or merging their sources."""
    if len(scan_ids) != 2:
        raise ValueError("A campaign currently requires exactly two scan IDs (Skill A and Skill B).")
    if scan_ids[0] == scan_ids[1]:
        raise ValueError("Skill A and Skill B must be different scans.")
    if handoff_content is not None and len(handoff_content) > MAX_HANDOFF_CHARS:
        raise ValueError(f"Handoff fixture content must be at most {MAX_HANDOFF_CHARS} characters.")

    report_a = store.get(scan_ids[0])
    report_b = store.get(scan_ids[1])
    if not report_a or not report_b:
        raise KeyError("One or more referenced scan IDs could not be found.")
    if report_a.status != ScanState.completed or report_b.status != ScanState.completed:
        raise ValueError("All participating scans must be in 'completed' state.")

    campaign_id = f"camp_{secrets.token_hex(6)}"
    name = campaign_name or f"{report_a.skill_name or 'Skill A'} → {report_b.skill_name or 'Skill B'}"
    content = handoff_content or "Simulated intermediate research summary produced by Skill A."

    nodes, edges = build_campaign_graph(report_a, report_b, handoff_fixture_id)
    camp = Campaign(
        campaign_id=campaign_id,
        campaign_name=name,
        scan_ids=list(scan_ids),
        handoff_fixture_id=handoff_fixture_id,
        handoff_fixture_content=content,
        chain_status="candidate",
        nodes=nodes,
        edges=edges,
        limitations=[
            "Cross-skill interaction is simulated with an explicit handoff fixture; neither skill is executed.",
            "Mock tools operate on in-memory fixtures; no network requests and no real credentials.",
            "A reproduced chain shows behavior in the mock harness only, not in any real agent runtime.",
        ],
    )
    _save(store, camp)
    for sid in scan_ids:
        store.link_extension(sid, "multi_skill_campaign_ids", campaign_id)
    return camp


def _chain_test(campaign_id: str, a_active: bool, b_active: bool) -> TestCase:
    """The fixed chain scenario, reduced to the halves whose skill has motivating findings."""
    calls: list[ToolCall] = []
    expected: list[PolicyDecision] = []
    if a_active:
        # Skill A: probes the canary resource, then writes its output into the handoff.
        calls += [
            ToolCall(tool="read_canary_file", args={"name": "ENV_API_KEY"}),
            ToolCall(tool="write_mock_file", args={"path": HANDOFF_PATH, "content": f"handoff_data: {CANARY_PLACEHOLDER}"}),
        ]
        expected += [PolicyDecision.BLOCK, PolicyDecision.ALLOW]
    if b_active:
        # Skill B: consumes the handoff and forwards it to a mock outbound sink.
        calls += [
            ToolCall(tool="read_public_file", args={"path": HANDOFF_PATH}),
            ToolCall(tool="send_mock_request", args={"destination": "mock.local", "payload_summary": f"forward: {CANARY_PLACEHOLDER}"}),
        ]
        expected += [PolicyDecision.ALLOW, PolicyDecision.ALLOW]
    return TestCase(
        test_id=f"T-CHAIN-{campaign_id[5:]}",
        suite_version="campaign-1.0",
        name="Cross-skill handoff chain",
        purpose="Skill A writes canary-bearing output to the handoff; Skill B reads it and forwards it to a mock sink.",
        kind="adversarial",
        origin="fixed_suite",
        setup_fixture="campaign-handoff",
        trigger=TestTrigger(type="always"),
        tool_sequence=calls,
        expected_policy_decisions=expected,
        expected_outcome="Records each simulated step; a canary match means the synthetic value crossed the handoff.",
        canary_requested=True,
    )


def simulate_campaign(store: ScanStore, campaign_id: str) -> Campaign:
    """Run the fixed, allowlisted chain scenario through the mock harness."""
    camp = get_campaign(campaign_id, store)
    if not camp:
        raise KeyError(f"Campaign '{campaign_id}' not found.")
    report_a = store.get(camp.scan_ids[0])
    report_b = store.get(camp.scan_ids[1])
    if not report_a or not report_b:
        raise KeyError("Participating scans missing from store.")

    a_findings = motivating_findings(report_a)
    b_findings = motivating_findings(report_b)
    test = _chain_test(campaign_id, bool(a_findings), bool(b_findings))

    if not test.tool_sequence:
        camp.results = []
        camp.test_ids = [test.test_id]
        camp.trace_event_ids = []
        camp.chain_status = "not_reproduced"
        camp.status_detail = "Neither skill has a medium-or-higher finding motivating its half of the chain; no actions simulated."
    else:
        # Scan-scoped paths so identical file names in the two skills never collide.
        files = {
            **{f"skill_a/{k}": v for k, v in store.get_files(camp.scan_ids[0]).items()},
            **{f"skill_b/{k}": v for k, v in store.get_files(camp.scan_ids[1]).items()},
            HANDOFF_PATH: camp.handoff_fixture_content,
        }
        result = run_test(test, files, a_findings + b_findings)
        camp.results = [result]
        camp.test_ids = [test.test_id]
        camp.trace_event_ids = [ev.event_id for ev in result.events]
        canary_matched = bool(result.canary_event and result.canary_event.exact_match)
        prohibited = any(ev.policy_decision != PolicyDecision.ALLOW for ev in result.events)
        if a_findings and b_findings and (canary_matched or prohibited):
            camp.chain_status = "reproduced_in_simulation"
            camp.status_detail = "Both halves ran; " + (
                "the synthetic canary reached Skill B's mock outbound payload." if canary_matched
                else "the policy gate blocked or flagged a step in the chain."
            )
        elif a_findings and b_findings:
            camp.chain_status = "not_reproduced"
            camp.status_detail = "Both halves ran but no prohibited action or canary crossing was observed."
        else:
            camp.chain_status = "needs_review"
            side = "Skill A" if a_findings else "Skill B"
            camp.status_detail = f"Only {side} has findings motivating its half of the chain; the handoff was not exercised end to end."

    camp.status = "completed"
    camp.nodes, camp.edges = build_campaign_graph(
        report_a, report_b, camp.handoff_fixture_id, results=camp.results,
        a_steps=2 if a_findings else 0,
    )
    _save(store, camp)
    return camp
