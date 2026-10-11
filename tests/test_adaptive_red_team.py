"""Tests for Feature E: Bounded adaptive red-team testing."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ScanReport, ScanState, utcnow
from app.test_generation.adaptive import (
    advance_red_team_run,
    create_red_team_run,
    get_run,
    stop_red_team_run,
)


client = TestClient(app)


def test_adaptive_red_team_lifecycle_and_budget():
    report = ScanReport(
        scan_id="scan_adaptive_01",
        created_at=utcnow(),
        input_kind="text",
        status=ScanState.completed,
        skill_name="Test Adaptive Skill",
        findings=[],
        files=[],
    )

    files = {"SKILL.md": " harmless text "}
    run = create_red_team_run(report)
    assert run.current_round == 0
    assert run.max_rounds == 3
    assert run.max_tests_total == 9
    assert run.status == "ready"

    # Round 1
    run = advance_red_team_run(run, report, files)
    assert run.current_round == 1
    assert len(run.candidates) == 3
    # Check that at least one candidate was accepted and one was rejected (the shell one)
    accepted = [c for c in run.candidates if c.status in ("passed", "failed")]
    rejected = [c for c in run.candidates if c.status == "rejected"]
    assert len(accepted) >= 1
    assert len(rejected) >= 1
    assert any("rejected" in " ".join(c.validation_notes).lower() for c in rejected)

    # Round 2
    run = advance_red_team_run(run, report, files)
    assert run.current_round == 2
    assert len(run.candidates) == 6

    # Round 3
    run = advance_red_team_run(run, report, files)
    assert run.current_round == 3
    assert run.status == "completed"

    # Round 4 attempted: should remain completed and not exceed max_rounds
    run = advance_red_team_run(run, report, files)
    assert run.current_round == 3
    assert run.status == "completed"
    assert run.metrics["rounds_completed"] == 3


def test_stop_red_team_run():
    report = ScanReport(
        scan_id="scan_adaptive_stop",
        created_at=utcnow(),
        input_kind="text",
        status=ScanState.completed,
        findings=[],
        files=[],
    )
    files = {"SKILL.md": " harmless "}
    run = create_red_team_run(report)
    run = advance_red_team_run(run, report, files)
    assert run.status == "running"

    stopped = stop_red_team_run(run.run_id)
    assert stopped is not None
    assert stopped.status == "stopped"
    assert len(stopped.candidates) > 0


def test_api_red_team_endpoints():
    # Setup scan in store
    from app.api.deps import store
    from app.pipeline import new_scan_id
    sid = new_scan_id()
    report = ScanReport(
        scan_id=sid,
        created_at=utcnow(),
        input_kind="text",
        status=ScanState.completed,
        findings=[],
        files=[],
    )
    store().save(report)
    store().save_files(report.scan_id, {"SKILL.md": "hello"})


    # POST start
    res = client.post(f"/api/scans/{report.scan_id}/red-team-runs", json={"advance_first_round": True})
    assert res.status_code == 200
    data = res.json()
    run_id = data["run_id"]
    assert data["current_round"] == 1
    assert len(data["candidates"]) == 3

    # GET run
    get_res = client.get(f"/api/red-team-runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["run_id"] == run_id

    # POST advance
    adv_res = client.post(f"/api/red-team-runs/{run_id}/advance")
    assert adv_res.status_code == 200
    assert adv_res.json()["current_round"] == 2

    # POST stop
    stop_res = client.post(f"/api/red-team-runs/{run_id}/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "stopped"


def test_adaptive_pass_means_expected_decisions_and_rerun():
    report = ScanReport(scan_id="scan_adaptive_eval", created_at=utcnow(), input_kind="text",
                        status=ScanState.completed, findings=[], files=[])
    files = {"SKILL.md": "harmless"}
    run = advance_red_team_run(create_red_team_run(report), report, files)
    assert run.proposal_source == "deterministic_template"
    executed = [c for c in run.candidates if c.result is not None]
    assert executed
    # A correctly blocked attack matches its expected decisions and therefore passes.
    for c in executed:
        observed = [e.policy_decision for e in c.result.events]
        assert (c.status == "passed") == (observed == c.expected_policy_decisions)
    assert all(c.status == "rejected" and not c.tool_sequence for c in run.candidates if c.result is None)

    from app.test_generation.adaptive import rerun_accepted
    before = [(c.candidate_id, c.status) for c in run.candidates]
    run = rerun_accepted(run, report, files)
    assert [(c.candidate_id, c.status) for c in run.candidates] == before
    assert run.metrics["reruns"] == 1
    assert run.metrics["tests_executed"] == len(executed)  # rerun does not consume budget
