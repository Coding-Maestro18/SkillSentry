"""Suspicious whitespace and a single documented whitespace decoder.

Decoder (documented, deterministic): over a block of consecutive lines with
trailing whitespace, concatenate each line's trailing characters in order,
map SPACE→0 and TAB→1, and read 8-bit ASCII most-significant-bit first. A
payload is only reported as *decoded* when this yields ≥2 bytes that are all
printable ASCII; otherwise the finding says "payload not decoded".

Thresholds are module-level constants so they can be tuned and are reported in
each finding's rationale.
"""

from __future__ import annotations

import unicodedata

from ..schemas import Severity
from .common import AnnotationSink, cp, cp_label, hidden_match
from .static_rules import RuleMatch, instruction_signals

DETECTOR = "whitespace.anomaly.v1"
DECODER = "trailing whitespace bits: SPACE=0, TAB=1, 8-bit ASCII MSB-first, ≥2 printable bytes"

MIN_BLOCK_LINES = 4  # consecutive lines with mixed trailing space/tab
LONG_TRAILING = 8  # trailing whitespace length considered a long run
MIN_LONG_LINES = 3
UNUSUAL_SPACE_MEDIUM_COUNT = 10

_CJK_PREFIXES = ("CJK", "HIRAGANA", "KATAKANA", "HANGUL", "FULLWIDTH", "IDEOGRAPHIC")


def _unusual_space(ch: str) -> bool:
    return ch != " " and unicodedata.category(ch) == "Zs"


def _space_legit(text: str, i: int) -> str | None:
    ch = text[i]
    prev = text[i - 1] if i > 0 else ""
    nxt = text[i + 1] if i + 1 < len(text) else ""
    if ch == "\u3000" and (unicodedata.name(prev, "").startswith(_CJK_PREFIXES) or unicodedata.name(nxt, "").startswith(_CJK_PREFIXES)):
        return "Ideographic space in CJK text."
    if ch in ("\u00a0", "\u202f") and (nxt in ":;?!»%€" or prev in "«" or (prev.isdigit() and nxt.isalpha())):
        return "Non-breaking space used typographically (punctuation/units)."
    return None


def _decode(bits: str) -> str | None:
    if len(bits) < 16:
        return None
    data = [int(bits[k:k + 8], 2) for k in range(0, len(bits) - len(bits) % 8, 8)]
    if len(data) < 2 or not all(32 <= b < 127 for b in data):
        return None
    return "".join(map(chr, data))


def scan(text: str, sink: AnnotationSink) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    smap = sink.smap

    # --- Unusual Unicode spaces ---------------------------------------------
    unusual = [(i, c) for i, c in enumerate(text) if _unusual_space(c)]
    suspicious_spaces = []
    for i, c in unusual:
        legit = _space_legit(text, i)
        if legit:
            sink.add("unusual_space", i, i + 1, DETECTOR, Severity.informational, f"Likely legitimate: {legit}",
                     cp(c), cp_label(c))
        else:
            suspicious_spaces.append((i, c))
    if suspicious_spaces:
        sev = Severity.medium if len(suspicious_spaces) >= UNUSUAL_SPACE_MEDIUM_COUNT else Severity.low
        by_line: dict[int, list[tuple[int, str]]] = {}
        for i, c in suspicious_spaces:
            by_line.setdefault(smap.position(i)[0], []).append((i, c))
        for line, items in by_line.items():
            aids = [sink.add("unusual_space", i, i + 1, DETECTOR, sev, "Non-ASCII space separator.", cp(c), cp_label(c))
                    for i, c in items]
            kinds = sorted({cp_label(c) for _, c in items})
            matches.append(hidden_match(
                "SS-WS-002", "whitespace_anomaly", "Unusual Unicode space character", sev, items[0][0], items[-1][0] + 1,
                "Non-ASCII spaces look identical to normal spaces but are different code points; they can defeat "
                f"keyword matching. {len(suspicious_spaces)} found in file (medium at ≥{UNUSUAL_SPACE_MEDIUM_COUNT}).",
                "Replace with ordinary spaces unless typographically required.",
                f"{len(items)} occurrence(s) on line {line}: {', '.join(kinds)}.", aids,
            ))

    # --- Trailing whitespace patterns ---------------------------------------
    lines = smap.lines()
    trailing: list[tuple[int, str]] = []  # (line_no, trailing ws)
    for ln, line in enumerate(lines, start=1):
        stripped = line.rstrip(" \t")
        trailing.append((ln, line[len(stripped):]))

    def is_markdown_break(ws: str) -> bool:
        return ws == "  " or ws == " "

    used_lines: set[int] = set()
    block: list[tuple[int, str]] = []

    def flush() -> None:
        if len(block) >= MIN_BLOCK_LINES:
            joined = "".join(ws for _, ws in block)
            if " " in joined and "\t" in joined:
                first, last = block[0][0], block[-1][0]
                start = smap.line_starts[first - 1] + len(lines[first - 1]) - len(block[0][1])
                end = smap.line_starts[last - 1] + len(lines[last - 1])
                bits = "".join("0" if c == " " else "1" for c in joined)
                decoded = _decode(bits)
                signals = instruction_signals(decoded) if decoded else []
                sev = Severity.high if signals else Severity.medium
                aids = []
                for ln, ws in block:
                    s = smap.line_starts[ln - 1] + len(lines[ln - 1]) - len(ws)
                    aids.append(sink.add("whitespace_anomaly", s, s + len(ws), DETECTOR, sev,
                                         f"Trailing whitespace: {ws.replace(' ', '·').replace(chr(9), '⇥')}"))
                    used_lines.add(ln)
                matches.append(hidden_match(
                    "SS-WS-001", "whitespace_anomaly",
                    "Whitespace-encoded payload decoded" if decoded else "Suspicious space/tab trailing pattern",
                    sev, start, end,
                    f"Lines {first}–{last} ({len(block)} ≥ {MIN_BLOCK_LINES} consecutive lines) end in mixed "
                    "spaces and tabs, a pattern used by whitespace steganography. "
                    + (f"The documented decoder produced printable text." if decoded
                       else "Suspicious whitespace pattern; payload not decoded.")
                    + (f" Decoded text matches rules: {', '.join(signals)}." if signals else ""),
                    "Strip trailing whitespace from these lines.",
                    f"{len(joined)} trailing whitespace characters across lines {first}–{last}.", aids,
                    decoded_payload=decoded, decoder=DECODER if decoded else None, inner_rule_ids=signals,
                ))
        block.clear()

    for ln, ws in trailing:
        if ws and not is_markdown_break(ws):
            block.append((ln, ws))
        else:
            flush()
    flush()

    long_runs = [(ln, ws) for ln, ws in trailing if len(ws) >= LONG_TRAILING and ln not in used_lines]
    if len(long_runs) >= MIN_LONG_LINES:
        aids = []
        for ln, ws in long_runs:
            s = smap.line_starts[ln - 1] + len(lines[ln - 1]) - len(ws)
            aids.append(sink.add("whitespace_anomaly", s, s + len(ws), DETECTOR, Severity.low,
                                 f"{len(ws)} trailing whitespace characters"))
        first = long_runs[0][0]
        s0 = smap.line_starts[first - 1]
        matches.append(hidden_match(
            "SS-WS-003", "whitespace_anomaly", "Repeated long trailing whitespace runs", Severity.low,
            s0, s0 + len(lines[first - 1]),
            f"{len(long_runs)} lines (threshold {MIN_LONG_LINES}) end with ≥{LONG_TRAILING} whitespace characters. "
            "Often accidental, but can hide data. Suspicious whitespace pattern; payload not decoded.",
            "Strip trailing whitespace.",
            "Lines: " + ", ".join(str(ln) for ln, _ in long_runs[:20]), aids,
        ))
    return matches
