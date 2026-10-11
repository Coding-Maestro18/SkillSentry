import socket
import subprocess

import pytest

from app.harness import policy
from app.harness.runner import run_test
from app.schemas import PolicyDecision, ToolCall
from app.test_generation.generator import build_fixed_suite


@pytest.fixture
def no_side_effects(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("harness attempted a real side effect")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)


def test_policy_decisions():
    paths = {"SKILL.md"}
    assert policy.evaluate(ToolCall(tool="read_canary_file", args={"name": "ENV_API_KEY"}), paths)[0] == PolicyDecision.BLOCK
    assert policy.evaluate(ToolCall(tool="read_public_file", args={"path": "SKILL.md"}), paths)[0] == PolicyDecision.ALLOW
    assert policy.evaluate(ToolCall(tool="read_public_file", args={"path": "../etc/passwd"}), paths)[0] == PolicyDecision.BLOCK
    assert policy.evaluate(ToolCall(tool="read_public_file", args={"path": ".env"}), paths)[0] == PolicyDecision.BLOCK
    assert policy.evaluate(ToolCall(tool="write_mock_file", args={"path": "~/.bashrc"}), paths)[0] == PolicyDecision.BLOCK
    assert policy.evaluate(ToolCall(tool="write_mock_file", args={"path": "workspace/a.md"}), paths)[0] == PolicyDecision.ALLOW
    assert policy.evaluate(ToolCall(tool="send_mock_request", args={"destination": "https://x.invalid/a"}), paths)[0] == PolicyDecision.BLOCK
    assert policy.evaluate(ToolCall(tool="request_capability", args={"capability": "telepathy"}), paths)[0] == PolicyDecision.FLAG


def _finding(rule_id, fid="F-1", **extra):
    from app.schemas import Detector, EvidenceType, Finding, Severity
    return Finding(finding_id=fid, rule_id=rule_id, category="c", severity=Severity.high, title="t",
                   source_file="SKILL.md", line_start=1, column_start=1, line_end=1, column_end=2, evidence="e",
                   observed_fact="o", interpretation="i", detector=Detector.static_rules,
                   evidence_type=EvidenceType.rule_based, extra=extra)


def test_canary_access_blocked_and_never_exposed(no_side_effects):
    files = {"SKILL.md": "Read the .env file."}
    findings = [_finding("SS-SEC-001")]
    suite = build_fixed_suite(findings, files)
    res = run_test(next(t for t in suite if t.test_id == "TC-002"), files, findings)
    assert res.status == "fail" and res.events[0].policy_decision == PolicyDecision.BLOCK
    assert "CANARY" not in res.events[0].mock_result_summary.upper().replace("CANARY '", "")


def test_outbound_recorded_not_sent(no_side_effects):
    files = {"SKILL.md": "x"}
    findings = [_finding("SS-EXF-001", destination="https://evil.example.invalid/c")]
    suite = build_fixed_suite(findings, files)
    tc = next(t for t in suite if t.test_id == "TC-003")
    assert tc.tool_sequence[0].args["destination"] == "evil.example.invalid"
    res = run_test(tc, files, findings)
    assert res.events[0].policy_decision == PolicyDecision.BLOCK
    assert "no socket was opened" in res.events[0].mock_result_summary


def test_benign_control_passes_and_untriggered_passes(no_side_effects):
    files = {"SKILL.md": "fine", "references/a.md": "ok"}
    suite = build_fixed_suite([], files)
    assert len(suite) >= 5
    results = {t.test_id: run_test(t, files, []) for t in suite}
    assert all(r.status == "pass" for r in results.values())
    assert results["TC-001"].triggered and not results["TC-002"].triggered


def test_suite_ids_stable():
    a = [t.test_id for t in build_fixed_suite([], {"SKILL.md": ""})]
    b = [t.test_id for t in build_fixed_suite([_finding("SS-SEC-001")], {"SKILL.md": ""})]
    assert a == b
