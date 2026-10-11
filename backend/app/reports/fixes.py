"""Fix suggestions. The original upload is never modified: suggestions produce a
revised *copy* plus a diff for human review."""

from __future__ import annotations

import difflib
import re

from ..analyzers.common import escape_invisibles
from ..schemas import FileAnnotation, Finding, FixSuggestion, Severity

STATIC_LINE_RULES = {"SS-OVR-001", "SS-SEC-001", "SS-EXF-001", "SS-CAP-001", "SS-CNC-001", "SS-ROLE-001",
                     "SS-ENC-001", "SS-ENC-002"}
_LABEL = re.compile(r"\[U\+[0-9A-F]{4,6} [A-Z0-9 \-]+\]")


def unified_diff(path: str, before: str, after: str) -> str:
    a = [escape_invisibles(l) for l in before.splitlines()]
    b = [escape_invisibles(l) for l in after.splitlines()]
    return "\n".join(difflib.unified_diff(a, b, f"original/{path}", f"revised/{path}", lineterm=""))


def _line_span(text: str, start: int, end: int) -> tuple[int, int]:
    s = text.rfind("\n", 0, start) + 1
    e = text.find("\n", end)
    return s, (len(text) if e < 0 else e + 1)


def deterministic_fix(files: dict[str, str], findings: list[Finding], annotations: list[FileAnnotation]) -> FixSuggestion:
    # Medium/high findings, plus low-severity invisible/whitespace findings (removing them is always safe).
    targeted = [f for f in findings if f.rule_id != "SS-MODEL" and (
        f.severity in (Severity.medium, Severity.high)
        or (f.severity == Severity.low and f.rule_id.startswith(("SS-UNI", "SS-WS"))))]
    by_ann = {a.annotation_id: a for a in annotations}
    revised: dict[str, str] = {}
    rationale: list[str] = []
    for path, text in files.items():
        edits: list[tuple[int, int, str]] = []
        frontmatter_end = 0
        m = re.match(r"\A\ufeff?---\r?\n.*?\r?\n---[ \t]*\r?\n", text, re.DOTALL)
        if m:
            frontmatter_end = m.end()
        for f in [f for f in targeted if f.source_file == path]:
            anns = [by_ann[a] for a in f.annotation_ids if a in by_ann]
            if f.rule_id in ("SS-HID-001", "SS-HID-002", "SS-HID-003"):
                for a in anns:
                    edits.append((a.start_offset, a.end_offset, ""))
                rationale.append(f"{f.finding_id}: removed concealed block ({path}:{f.line_start}).")
            elif f.rule_id in ("SS-UNI-001", "SS-UNI-002", "SS-UNI-003", "SS-UNI-004"):
                for a in anns:
                    edits.append((a.start_offset, a.end_offset, ""))
                rationale.append(f"{f.finding_id}: removed invisible characters ({path}:{f.line_start}).")
            elif f.rule_id == "SS-UNI-005":
                for a in anns:
                    if a.skeleton:
                        edits.append((a.start_offset, a.end_offset, a.skeleton))
                rationale.append(f"{f.finding_id}: replaced look-alike characters with ASCII ({path}:{f.line_start}).")
            elif f.rule_id in ("SS-WS-001", "SS-WS-003"):
                for a in anns:
                    edits.append((a.start_offset, a.end_offset, ""))
                rationale.append(f"{f.finding_id}: stripped trailing whitespace ({path}:{f.line_start}).")
            elif f.rule_id == "SS-WS-002":
                for a in anns:
                    edits.append((a.start_offset, a.end_offset, " "))
                rationale.append(f"{f.finding_id}: replaced unusual spaces with ASCII spaces.")
        # Static instruction findings: drop the whole line that carries the instruction (outside frontmatter).
        smap_lines = text
        for f in [f for f in targeted if f.source_file == path and f.rule_id in STATIC_LINE_RULES]:
            if f.extra.get("inside_hidden_region"):
                continue  # removed with its hidden block
            line_start = 0
            for _ in range(f.line_start - 1):
                line_start = smap_lines.find("\n", line_start) + 1
            if line_start < frontmatter_end:
                continue
            s, e = _line_span(text, line_start, line_start)
            edits.append((s, e, ""))
            rationale.append(f"{f.finding_id}: removed line {f.line_start} containing '{f.title.lower()}'.")
        if not edits:
            continue
        # Apply non-overlapping edits from the end; for overlaps keep the widest span.
        edits.sort(key=lambda x: (x[0], -(x[1] - x[0])))
        merged: list[tuple[int, int, str]] = []
        for s, e, r in edits:
            if merged and s < merged[-1][1]:
                ps, pe, pr = merged[-1]
                if e > pe:
                    merged[-1] = (ps, e, pr)
                continue
            merged.append((s, e, r))
        out = text
        for s, e, r in reversed(merged):
            out = out[:s] + r + out[e:]
        out = re.sub(r"\n{3,}", "\n\n", out)
        if out != text:
            revised[path] = out
    return FixSuggestion(
        origin="deterministic", model_status="not used", finding_ids=[f.finding_id for f in targeted],
        rationale=list(dict.fromkeys(rationale)) or ["No medium/high findings to fix."],
        revised_files=revised, diffs={p: unified_diff(p, files[p], t) for p, t in revised.items()},
    )


def clean_model_revision(text: str) -> str:
    """Models sometimes echo our escape labels; strip them so the revision contains no fake labels."""
    return _LABEL.sub("", text)
