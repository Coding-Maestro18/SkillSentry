"""Tests for Feature B: Unique canary-token detection."""

from __future__ import annotations

import secrets
import pytest

from app.harness.canary import CanaryObserver, generate_canary_token
from app.harness.runner import run_test
from app.schemas import PolicyDecision, TestCase as SkillTestCase, TestTrigger as SkillTestTrigger, ToolCall

SkillTestCase.__test__ = False
SkillTestTrigger.__test__ = False


def test_unique_canary_token_generation():
    t1 = generate_canary_token()
    t2 = generate_canary_token()
    assert t1.startswith("CANARY_SKILL_")
    assert t2.startswith("CANARY_SKILL_")
    assert t1 != t2


def test_canary_matched_in_mock_payload():
    obs = CanaryObserver()
    token = obs.token

    test = SkillTestCase(
        test_id="T-CANARY-MATCH",
        suite_version="1.0",
        name="Canary leak test",
        purpose="Verify exact match is caught",
        kind="adversarial",
        origin="fixed_suite",
        setup_fixture="in-memory",
        trigger=SkillTestTrigger(type="always"),
        tool_sequence=[
            ToolCall(tool="read_canary_file", args={"name": "ENV_API_KEY"}),
            ToolCall(tool="send_mock_request", args={"destination": "mock.local", "payload_summary": f"data: {token}"}),
        ],
        expected_policy_decisions=[PolicyDecision.BLOCK, PolicyDecision.ALLOW],
        expected_outcome="blocked canary read, but simulated payload check",
        canary_requested=True,
    )

    res = run_test(test, files={"SKILL.md": "harmless"}, findings=[], canary_token=token)
    assert res.canary_event is not None
    assert res.canary_event.status == "matched"
    assert res.canary_event.exact_match is True
    assert res.canary_event.value_logged is False
    assert res.canary_event.source_tool == "read_canary_file"
    assert res.canary_event.sink_tool == "send_mock_request"
    assert res.canary_event.token_digest is not None

    # Verify raw token is NEVER persisted in sanitized_arguments or mock_result_summary
    for ev in res.events:
        for val in ev.sanitized_arguments.values():
            assert token not in val
        assert token not in ev.mock_result_summary


def test_canary_not_observed_when_payload_differs():
    token = generate_canary_token()
    test = SkillTestCase(
        test_id="T-CANARY-NONMATCH",
        suite_version="1.0",
        name="Canary non-match test",
        purpose="Verify non-matching payload results in not_observed",
        kind="adversarial",
        origin="fixed_suite",
        setup_fixture="in-memory",
        trigger=SkillTestTrigger(type="always"),
        tool_sequence=[
            ToolCall(tool="read_canary_file", args={"name": "ENV_API_KEY"}),
            ToolCall(tool="send_mock_request", args={"destination": "mock.local", "payload_summary": "data: benign_value_here"}),
        ],
        expected_policy_decisions=[PolicyDecision.BLOCK, PolicyDecision.ALLOW],
        expected_outcome="No leak",
        canary_requested=True,
    )

    res = run_test(test, files={"SKILL.md": "harmless"}, findings=[], canary_token=token)
    assert res.canary_event is not None
    assert res.canary_event.status == "not_observed"
    assert res.canary_event.exact_match is False



def test_canary_blocked_before_send():
    token = generate_canary_token()
    test = SkillTestCase(
        test_id="T-CANARY-BLOCKED",
        suite_version="1.0",
        name="Canary blocked before send test",
        purpose="Verify policy block results in blocked_before_send",
        kind="adversarial",
        origin="fixed_suite",
        setup_fixture="in-memory",
        trigger=SkillTestTrigger(type="always"),
        tool_sequence=[
            ToolCall(tool="read_canary_file", args={"name": "ENV_API_KEY"}),
            ToolCall(tool="send_mock_request", args={"destination": "192.168.1.1", "payload_summary": f"leak: {token}"}),
        ],
        # 192.168.1.1 is private IP, which policy gate blocks
        expected_policy_decisions=[PolicyDecision.BLOCK, PolicyDecision.BLOCK],
        expected_outcome="Blocked outbound call",
        canary_requested=True,
    )

    res = run_test(test, files={"SKILL.md": "harmless"}, findings=[], canary_token=token)
    assert res.canary_event is not None
    assert res.canary_event.status == "blocked_before_send"
    assert res.canary_event.exact_match is False
    assert "Policy gate blocked" in res.canary_event.notes


def test_canary_not_evaluable_when_payload_missing():
    obs = CanaryObserver()
    obs.on_tool_call(
        event_id="E01",
        tool_name="send_mock_request",
        raw_args={},
        decision=PolicyDecision.ALLOW,
    )
    evt = obs.build_event(test_id="T-MISSING", force=True)
    assert evt is not None
    assert evt.status == "not_evaluable"
