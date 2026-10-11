"""Run validated test cases against a skill version using only mock tools.

The "simulated agent" is deterministic: a test's tool sequence is performed
only when its trigger is still present in the skill version under test (a
matching rule finding or a quoted excerpt). This makes reruns against a revised
copy directly comparable. It is a simulation, not evidence of how a real agent
runtime would behave.
"""

from __future__ import annotations

from ..schemas import SEVERITY_ORDER, Finding, PolicyDecision, TestCase, TestResult, TraceEvent
from . import policy
from .canary import CanaryObserver
from .mock_tools import MockWorld

SIMULATION_NOTE = "Simulated behavior via mock tools; not evidence of what a real agent runtime would do."


def _sanitize(args: dict[str, str], observer: Optional[CanaryObserver] = None) -> dict[str, str]:
    res = {}
    for k, v in args.items():
        val = observer.redact_string(v) if observer else v
        res[k] = val[:120] + "…" if len(val) > 120 else val
    return res


def is_triggered(test: TestCase, files: dict[str, str], findings: list[Finding]) -> bool:
    t = test.trigger
    if t.type == "always":
        return True
    if t.type == "rule":
        floor = SEVERITY_ORDER[t.min_severity]
        return any(f.rule_id in t.rule_ids and SEVERITY_ORDER[f.severity] >= floor for f in findings)
    if t.type == "excerpt" and t.excerpt:
        needle = t.excerpt.strip()
        return any(needle in text for text in files.values())
    return False


def run_test(
    test: TestCase,
    files: dict[str, str],
    findings: list[Finding],
    canary_token: Optional[str] = None,
) -> TestResult:
    if test.validation_status != "valid":
        return TestResult(test_id=test.test_id, status="skipped", triggered=False,
                          summary="Test failed validation and was not run.")
    triggered = is_triggered(test, files, findings)
    if not triggered:
        return TestResult(
            test_id=test.test_id, status="pass", triggered=False,
            summary="The simulated agent found no instruction in this skill version that triggers the scenario; "
                    "no tool calls were made.",
        )
    observer = CanaryObserver(token=canary_token)
    world = MockWorld(skill_files=files, canary_token=observer.token)
    skill_paths = set(files)
    events: list[TraceEvent] = []
    for idx, call in enumerate(test.tool_sequence, start=1):
        decision, reason = policy.evaluate(call, skill_paths)
        event_id = f"{test.test_id}-E{idx:02d}"
        observer.on_tool_call(event_id, call.tool, call.args, decision)
        allowed = decision == PolicyDecision.ALLOW
        a = call.args
        if call.tool == "read_public_file":
            result = world.read_public_file(a.get("path", "")) if allowed else "Not read (policy)."
        elif call.tool == "read_canary_file":
            result = world.read_canary_file(a.get("name", ""), allowed)
        elif call.tool == "write_mock_file":
            result = world.write_mock_file(a.get("path", ""), a.get("content", ""), allowed)
        elif call.tool == "send_mock_request":
            result = world.send_mock_request(a.get("destination", ""), a.get("payload_summary", ""))
        elif call.tool == "list_mock_resources":
            result = world.list_mock_resources()
        else:
            result = world.request_capability(a.get("capability", ""))
        events.append(TraceEvent(
            event_id=event_id, test_id=test.test_id, sequence_number=idx, tool_name=call.tool,
            sanitized_arguments=_sanitize(a, observer), policy_decision=decision, decision_reason=reason,
            mock_result_summary=result,
        ))

    decisions = [e.policy_decision for e in events]
    matches_expected = decisions == list(test.expected_policy_decisions)
    if test.kind == "benign_control":
        if all(d == PolicyDecision.ALLOW for d in decisions):
            status, summary = "pass", "Benign control: all simulated actions were allowed, as expected."
        else:
            status, summary = "needs_review", "Benign control produced a BLOCK/FLAG; check policy or fixtures."
    else:
        unsafe = [d for d in decisions if d != PolicyDecision.ALLOW]
        if not unsafe:
            status, summary = "pass", "Triggered, but every simulated action was within policy."
        elif any(d == PolicyDecision.BLOCK for d in unsafe):
            status = "fail"
            summary = ("The skill induces actions the policy gate blocked: "
                       + "; ".join(f"{e.tool_name} → {e.policy_decision.value}" for e in events if e.policy_decision != PolicyDecision.ALLOW)
                       + ".")
        else:
            status, summary = "needs_review", "The skill induces actions the policy gate flagged for review."
        if not matches_expected:
            summary += f" Observed decisions {[d.value for d in decisions]} differ from expected {[d.value for d in test.expected_policy_decisions]}."

    canary_evt = observer.build_event(test.test_id, force=test.canary_requested)
    return TestResult(
        test_id=test.test_id,
        status=status,
        triggered=True,
        summary=summary,
        events=events,
        canary_event=canary_evt,
    )


def run_suite(tests: list[TestCase], files: dict[str, str], findings: list[Finding]) -> list[TestResult]:
    return [run_test(t, files, findings) for t in tests]

