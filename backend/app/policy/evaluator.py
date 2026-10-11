"""Mock-gate evaluator: exercise a validated SKILL_POLICY against existing test scenarios.

Path patterns: ``dir/**`` matches everything below ``dir/``; any other pattern is an
``fnmatch`` glob matched against the whole normalized relative path. Paths that are
absolute or escape the root with ``..`` never match.
"""

from __future__ import annotations

import fnmatch
import posixpath
import re
from typing import Any

from ..schemas import PolicyDecision, TestCase, ToolCall
from .schema import SkillPolicy


def _host(destination: str) -> str:
    m = re.match(r"^[a-z]+://([^/:?#]+)", destination.strip(), re.I)
    return (m.group(1) if m else destination.strip().split("/")[0]).lower()


def path_matches(path: str, patterns: list[str]) -> bool:
    raw = path.replace("\\", "/")
    if not raw or raw.startswith("/") or ":" in raw:
        return False
    norm = posixpath.normpath(raw)
    if norm == ".." or norm.startswith("../"):
        return False
    for pat in patterns:
        if pat.endswith("/**"):
            if norm.startswith(pat[:-2]):  # keep the trailing "/" so "ref/**" does not match "refs/x"
                return True
        elif fnmatch.fnmatchcase(norm, pat):
            return True
    return False


class _Counters:
    def __init__(self) -> None:
        self.requests = 0
        self.reads = 0


def evaluate_tool_with_policy(
    policy: SkillPolicy, call: ToolCall, counters: _Counters | None = None
) -> tuple[PolicyDecision, str]:
    """Evaluate a single ToolCall deterministically using a SkillPolicy (deny by default)."""
    counters = counters or _Counters()
    default_dec = PolicyDecision[policy.default_action]

    if call.tool in policy.forbidden_actions:
        return PolicyDecision.BLOCK, f"'{call.tool}' is listed in forbidden_actions."
    if call.tool not in policy.allowed_tools:
        return default_dec, f"'{call.tool}' is not in allowed_tools (default: {policy.default_action})."

    args = call.args
    if call.tool == "read_public_file":
        counters.reads += 1
        if counters.reads > policy.limits.max_file_reads_per_test:
            return PolicyDecision.BLOCK, f"Exceeds limits.max_file_reads_per_test ({policy.limits.max_file_reads_per_test})."
        if not path_matches(args.get("path", ""), policy.allowed_file_paths):
            return PolicyDecision.BLOCK, f"Path '{args.get('path', '')}' does not match allowed_file_paths."
        return PolicyDecision.ALLOW, "Path matches allowed_file_paths."

    if call.tool == "write_mock_file":
        if not path_matches(args.get("path", ""), policy.allowed_file_paths):
            return PolicyDecision.BLOCK, f"Write target '{args.get('path', '')}' does not match allowed_file_paths."
        return PolicyDecision.ALLOW, "Write target matches allowed_file_paths."

    if call.tool == "send_mock_request":
        counters.requests += 1
        if counters.requests > policy.limits.max_mock_requests_per_test:
            return PolicyDecision.BLOCK, f"Exceeds limits.max_mock_requests_per_test ({policy.limits.max_mock_requests_per_test})."
        host = _host(args.get("destination", ""))
        if host not in {d.lower() for d in policy.allowed_domains}:
            return PolicyDecision.BLOCK, f"Destination '{host}' is not in allowed_domains."
        return PolicyDecision.ALLOW, f"Destination '{host}' is in allowed_domains."

    if call.tool == "request_capability":
        return PolicyDecision.FLAG, "Capability requests always need human review, even when the tool is allowed."

    return PolicyDecision.ALLOW, "Allowed by allowed_tools."


def simulate_policy_scenarios(policy: SkillPolicy, tests: list[TestCase]) -> list[dict[str, Any]]:
    """Replay each test's tool sequence through the policy (no tools are actually invoked)."""
    results = []
    for test in tests:
        counters = _Counters()
        events = []
        for idx, call in enumerate(test.tool_sequence, start=1):
            dec, reason = evaluate_tool_with_policy(policy, call, counters)
            events.append({"sequence": idx, "tool": call.tool, "decision": dec.value, "reason": reason})
        blocked = [e for e in events if e["decision"] != "ALLOW"]
        if test.kind == "benign_control":
            outcome = "pass" if not blocked else "needs_review"
            note = ("Benign control still works under this policy." if not blocked
                    else "Policy blocks or flags a benign control; it may be too strict for the declared purpose.")
        else:
            outcome = "contained" if blocked else "not_contained"
            note = ("At least one step is blocked or flagged by the policy." if blocked
                    else "Every step is allowed by this policy.")
        results.append({
            "test_id": test.test_id,
            "name": test.name,
            "kind": test.kind,
            "events": events,
            "outcome": outcome,
            "note": note,
        })
    return results
