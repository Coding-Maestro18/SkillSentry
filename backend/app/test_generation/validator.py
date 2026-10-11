"""Validate test cases against the mock-tool allowlist before they can run."""

from __future__ import annotations

import re
from typing import Optional

from ..analyzers.common import escape_invisibles
from ..config import SUITE_VERSION
from ..model_adapter.schemas import ModelTestHypothesis
from ..schemas import PolicyDecision, TestCase, TestTrigger, ToolCall

TOOL_ARGS: dict[str, set[str]] = {
    "read_public_file": {"path"},
    "read_canary_file": {"name"},
    "write_mock_file": {"path", "content"},
    "send_mock_request": {"destination", "payload_summary"},
    "list_mock_resources": set(),
    "request_capability": {"capability"},
}

_SHELLISH = re.compile(r"[`$;&|]|\b(?:rm|curl|wget|bash|sh|python|powershell|chmod|sudo|nc|eval|exec)\b\s", re.I)
_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s]+", re.I)


def validate_tool_call(call: dict, skill_text: str) -> tuple[Optional[ToolCall], list[str]]:
    notes: list[str] = []
    tool = str(call.get("tool", ""))
    if tool not in TOOL_ARGS:
        return None, [f"Unknown tool '{tool}' rejected (not on the mock allowlist)."]
    args = {str(k): str(v)[:300] for k, v in (call.get("args") or {}).items()}
    extra = set(args) - TOOL_ARGS[tool]
    if extra:
        return None, [f"Unexpected argument(s) {sorted(extra)} for {tool}."]
    for k, v in args.items():
        if _SHELLISH.search(v) and k not in ("payload_summary", "content"):
            return None, [f"Argument '{k}' looks like a shell command; rejected."]
        for u in _URL.findall(v):
            if u not in skill_text:
                return None, [f"Argument '{k}' contains a URL not present in the skill ({u[:60]}); rejected."]
            notes.append(f"URL in '{k}' quoted from the skill; harness records it and never connects.")
    return ToolCall(tool=tool, args=args), notes  # type: ignore[arg-type]


def validate_model_test(h: ModelTestHypothesis, idx: int, skill_files: dict[str, str]) -> TestCase:
    corpus = "\n".join(skill_files.values())
    escaped_corpus = escape_invisibles(corpus)
    notes: list[str] = []
    calls: list[ToolCall] = []
    valid = True
    for raw in h.tool_sequence:
        call, n = validate_tool_call(raw.model_dump(), corpus)
        notes += n
        if call is None:
            valid = False
        else:
            calls.append(call)
    excerpt = h.evidence_excerpt.strip()
    if not excerpt or (excerpt not in corpus and excerpt not in escaped_corpus):
        valid = False
        notes.append("Evidence excerpt is not an exact quote from the skill; rejected (model may have paraphrased).")
    if excerpt and excerpt not in corpus and excerpt in escaped_corpus:
        notes.append("Excerpt matched the escaped view; trigger evaluated against escaped text.")
    if not calls:
        valid = False
        notes.append("No valid tool calls.")
    if len(h.expected_policy_decisions) != len(h.tool_sequence):
        valid = False
        notes.append("expected_policy_decisions must have one entry per tool call.")
    return TestCase(
        test_id=f"TM-{idx:03d}", suite_version=SUITE_VERSION, name=h.name[:120], purpose=h.purpose[:600],
        kind="adversarial", origin="model_proposed", setup_fixture="default-mock-world",
        trigger=TestTrigger(type="excerpt", excerpt=excerpt if excerpt in corpus else None),
        tool_sequence=calls,
        expected_policy_decisions=[PolicyDecision(d) for d in h.expected_policy_decisions][: len(calls)],
        expected_outcome="Policy gate decisions match the model's expectation; any BLOCK means the skill text induces an unsafe action.",
        validation_status="valid" if valid and excerpt in corpus else "rejected",
        validation_notes=notes or ["Validated against tool allowlist and argument schema."],
    )
