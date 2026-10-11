"""Optional mock gate evaluator for validating and testing SKILL_POLICY against scenarios."""

from __future__ import annotations

import fnmatch
import posixpath
import re

from ..harness.mock_tools import MockWorld
from ..schemas import PolicyDecision, TestCase, ToolCall, TraceEvent
from .schema import SkillPolicy


def _host(destination: str) -> str:
    m = re.match(r"^[a-z]+://([^/:?#]+)", destination.strip(), re.I)
    return (m.group(1) if m else destination.strip().split("/")[0]).lower()


def evaluate_tool_with_policy(policy: SkillPolicy, call: ToolCall) -> tuple[PolicyDecision, str]:
    """Evaluate a single ToolCall deterministically using a SkillPolicy."""
    default_dec = PolicyDecision[policy.default_action]

    # Explicitly forbidden actions
    if call.tool in policy.forbidden_actions:
        return PolicyDecision.BLOCK, f"Tool '{call.tool}' is explicitly listed in forbidden_actions."

    # Check allowed_tools list
    if call.tool not in policy.allowed_tools:
        return default_dec, f"Tool '{call.tool}' is not in allowed_tools (default: {policy.default_action})."

    args = call.args

    if call.tool == "read_public_file":
        path = args.get("path", "")
        norm = posixpath.normpath(path.replace("\\", "/"))
        # Check against allowed_file_paths
        matched = False
        for pat in policy.allowed_file_paths:
            if pat.endswith("/**"):
                base = pat[:-3]
                if norm.startswith(base):
                    matched = True
                    break
            elif fnmatch.fnmatch(norm, pat) or norm == pat:
                matched = True
                break
        if not matched:
            return PolicyDecision.BLOCK, f"Path '{path}' does not match any allowed_file_paths in policy."
        return PolicyDecision.ALLOW, "Read operation matches allowed_file_paths."

    if call.tool == "send_mock_request":
        dest = args.get("destination", "")
        host = _host(dest)
        if not policy.allowed_domains:
            return PolicyDecision.BLOCK, "allowed_domains is empty; all outbound mock requests blocked."
        if host not in [d.lower() for d in policy.allowed_domains]:
            return PolicyDecision.BLOCK, f"Destination host '{host}' not in allowed_domains."
        return PolicyDecision.ALLOW, f"Destination '{host}' permitted by allowed_domains."

    if call.tool == "write_mock_file":
        path = args.get("path", "")
        norm = posixpath.normpath(path.replace("\\", "/"))
        matched = False
        for pat in policy.allowed_file_paths:
            if pat.endswith("/**") and norm.startswith(pat[:-3]):
                matched = True
                break
            elif fnmatch.fnmatch(norm, pat) or norm == pat or norm.startswith("workspace/"):
                matched = True
                break
        if not matched:
            return PolicyDecision.BLOCK, f"Write target '{path}' outside allowed paths."
        return PolicyDecision.ALLOW, "Write target allowed by policy."

    return PolicyDecision.ALLOW, "Action allowed by policy."


def simulate_policy_scenarios(
    policy: SkillPolicy,
    tests: list[TestCase],
    files: dict[str, str],
) -> list[dict[str, Any]]:
    """Simulate a set of tests against the proposed policy."""
    results = []
    for test in tests:
        events = []
        for idx, call in enumerate(test.tool_sequence, start=1):
            dec, reason = evaluate_tool_with_policy(policy, call)
            events.append({
                "sequence": idx,
                "tool": call.tool,
                "decision": dec.value,
                "reason": reason,
            })
        results.append({
            "test_id": test.test_id,
            "name": test.name,
            "events": events,
            "all_allowed": all(e["decision"] == "ALLOW" for e in events),
        })
    return results
