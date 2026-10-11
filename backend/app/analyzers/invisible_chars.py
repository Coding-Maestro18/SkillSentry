"""Zero-width / default-ignorable characters, bidi controls and Unicode tag characters.

Uses Unicode general categories from Python's ``unicodedata`` (version recorded in
reports) rather than only a hard-coded list. Context rules keep legitimate uses
(emoji ZWJ sequences, ZWNJ in Persian/Indic text, a leading BOM, flag tag
sequences) at informational level.
"""

from __future__ import annotations

import re
import unicodedata

from ..schemas import Severity
from .common import AnnotationSink, cp, cp_label, hidden_match
from .patterns import SENSITIVE_WORDS
from .static_rules import RuleMatch, instruction_signals

DETECTOR = "unicode.invisible_chars.v1"

BIDI_CONTROLS = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E, 0x2066, 0x2067, 0x2068, 0x2069, 0x200E, 0x200F, 0x061C}
ZERO_WIDTH_BITS = {"\u200b": "0", "\u200c": "1"}
EXTRA_IGNORABLE = {0x034F, 0x115F, 0x1160, 0x3164, 0xFFA0, 0x180E}
JOINING_SCRIPTS = ("ARABIC", "PERSIAN", "DEVANAGARI", "BENGALI", "GURMUKHI", "GUJARATI", "ORIYA", "TAMIL",
                   "TELUGU", "KANNADA", "MALAYALAM", "SINHALA", "SYRIAC", "MONGOLIAN", "HEBREW", "THAI", "KHMER",
                   "MYANMAR", "TIBETAN")
RTL_SCRIPTS = ("ARABIC", "HEBREW", "SYRIAC", "THAANA", "NKO")


def is_tag(ch: str) -> bool:
    return 0xE0000 <= ord(ch) <= 0xE007F


def is_variation_selector(ch: str) -> bool:
    o = ord(ch)
    return 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF


def is_target(ch: str) -> bool:
    o = ord(ch)
    if ch == "\ufeff" or o in EXTRA_IGNORABLE or o in BIDI_CONTROLS or is_tag(ch):
        return True
    return unicodedata.category(ch) == "Cf"


def _is_emoji(ch: str) -> bool:
    o = ord(ch)
    return (0x1F000 <= o <= 0x1FAFF) or (0x2600 <= o <= 0x27BF) or o in (0x2640, 0x2642, 0x2695, 0x2708, 0x2764)


def _script(ch: str) -> str:
    return unicodedata.name(ch, "").split(" ", 1)[0]


def _legit_reason(text: str, i: int, j: int) -> str | None:
    run = text[i:j]
    prev = text[i - 1] if i > 0 else ""
    nxt = text[j] if j < len(text) else ""
    if run == "\ufeff" and i == 0:
        return "Byte-order mark at file start (encoding signature)."
    if set(run) <= {"\u200d", "\ufe0f"} and prev and nxt and (_is_emoji(prev) or prev == "\ufe0f") and _is_emoji(nxt):
        return "ZWJ inside an emoji sequence."
    if set(run) <= {"\u200c", "\u200d"} and (
        _script(prev).startswith(JOINING_SCRIPTS) or _script(nxt).startswith(JOINING_SCRIPTS)
    ):
        return "Joiner/non-joiner adjacent to a script that uses it orthographically."
    if all(is_tag(c) for c in run) and prev == "\U0001F3F4" and run.endswith("\U000E007F"):
        return "Tag sequence forming an emoji subdivision flag."
    if set(run) <= {"\u200e", "\u200f", "\u061c"} and (
        _script(prev).startswith(RTL_SCRIPTS) or _script(nxt).startswith(RTL_SCRIPTS)
    ):
        return "Directional mark adjacent to right-to-left text."
    if all(is_variation_selector(c) for c in run) and len(run) == 1:
        return "Single variation selector (normal emoji/glyph presentation)."
    return None


def _decode_tags(run: str) -> str:
    return "".join(chr(ord(c) - 0xE0000) for c in run if 0xE0020 <= ord(c) <= 0xE007E)


def _decode_zero_width_bits(run: str) -> str | None:
    bits = "".join(ZERO_WIDTH_BITS.get(c, "") for c in run)
    if len(bits) != len(run) or len(bits) < 16:
        return None
    data = [int(bits[k:k + 8], 2) for k in range(0, len(bits) - len(bits) % 8, 8)]
    if not data or not all(32 <= b < 127 for b in data):
        return None
    return "".join(map(chr, data))


_WORD_CHAR = re.compile(r"[^\W_]", re.UNICODE)


def scan(text: str, sink: AnnotationSink) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    i = 0
    n = len(text)
    zw_suspicious: list[tuple[int, int, str, list[str], str | None]] = []
    while i < n:
        ch = text[i]
        if not (is_target(ch) or is_variation_selector(ch)):
            i += 1
            continue
        j = i + 1
        while j < n and (is_target(text[j]) or is_variation_selector(text[j])):
            j += 1
        run = text[i:j]
        distinct = sorted(set(run), key=ord)
        cps = ", ".join(cp(c) for c in distinct[:4]) + ("…" if len(distinct) > 4 else "")
        names = "; ".join(cp_label(c) for c in distinct[:4])
        legit = _legit_reason(text, i, j)
        if legit:
            sink.add("invisible_char", i, j, DETECTOR, Severity.informational, f"Likely legitimate: {legit}", cps, names)
            i = j
            continue

        if any(is_tag(c) for c in run):
            decoded = _decode_tags(run)
            signals = instruction_signals(decoded) if decoded else []
            sev = Severity.high if signals else Severity.medium
            aid = sink.add("tag_char", i, j, DETECTOR, sev,
                           f"{len(run)} Unicode tag characters; decoded ASCII: {decoded[:120]!r}", cps, names)
            matches.append(hidden_match(
                "SS-UNI-003", "invisible_unicode", "Invisible Unicode tag characters (ASCII smuggling)", sev, i, j,
                "Tag characters (U+E0000–E007F) are invisible in most renderers but map 1:1 to ASCII, so they can "
                "carry hidden text that a model may still read." + (f" Decoded text matches rules: {', '.join(signals)}." if signals else ""),
                "Remove all tag characters outside of emoji flag sequences.",
                f"{len(run)} tag characters ({cps}) occur at this location.", [aid],
                decoded_payload=decoded, decoder="Unicode tag → ASCII (code point − 0xE0000)", inner_rule_ids=signals,
            ))
            i = j
            continue

        if any(ord(c) in BIDI_CONTROLS for c in run):
            line_start = text.rfind("\n", 0, i) + 1
            line_end = text.find("\n", j)
            line = text[line_start: line_end if line_end >= 0 else n]
            clean = "".join(c for c in line if not is_target(c))
            words = {w.lower() for w in re.findall(r"[A-Za-z_]+", clean)}
            sensitive = bool(words & SENSITIVE_WORDS) or bool(instruction_signals(clean))
            override = any(ord(c) in (0x202D, 0x202E) for c in run)
            sev = Severity.high if (sensitive and override) else Severity.medium
            aid = sink.add("bidi_control", i, j, DETECTOR, sev,
                           "Bidirectional control can make displayed order differ from logical order.", cps, names)
            matches.append(hidden_match(
                "SS-UNI-002", "bidi_control", "Bidirectional control character", sev, i, j,
                "Bidi overrides/isolates can reorder how text is displayed versus how it is processed "
                "(“Trojan Source”)." + (" The line contains security-sensitive terms." if sensitive else ""),
                "Remove bidi controls unless the file intentionally contains right-to-left text.",
                f"{names} occurs here (logical line: {clean.strip()[:80]!r}).", [aid],
            ))
            i = j
            continue

        decoded = _decode_zero_width_bits(run)
        prev_word = bool(i > 0 and _WORD_CHAR.match(text[i - 1]))
        next_word = bool(j < n and _WORD_CHAR.match(text[j]))
        joined = None
        if prev_word and next_word:
            ws = i
            while ws > 0 and (_WORD_CHAR.match(text[ws - 1]) or is_target(text[ws - 1])):
                ws -= 1
            we = j
            while we < n and (_WORD_CHAR.match(text[we]) or is_target(text[we])):
                we += 1
            joined = "".join(c for c in text[ws:we] if not is_target(c))
        aid = sink.add("invisible_char", i, j, DETECTOR, Severity.low,
                       f"{len(run)} invisible character(s)" + (f" splitting the word {joined!r}" if joined else ""),
                       cps, names)
        zw_suspicious.append((i, j, cps, [aid], joined if joined else None))
        if decoded:
            signals = instruction_signals(decoded)
            sev = Severity.high if signals else Severity.medium
            matches.append(hidden_match(
                "SS-UNI-004", "invisible_unicode", "Zero-width binary encoded text", sev, i, j,
                "A run of ZWSP/ZWNJ characters decodes to printable ASCII under a documented bit scheme.",
                "Remove the zero-width run.", f"Run of {len(run)} zero-width characters ({cps}).", [aid],
                decoded_payload=decoded, decoder="zero-width bits: U+200B=0, U+200C=1, 8-bit MSB-first ASCII",
                inner_rule_ids=signals,
            ))
        elif len(run) >= 16:
            matches.append(hidden_match(
                "SS-UNI-004", "invisible_unicode", "Long run of zero-width characters", Severity.medium, i, j,
                "A long invisible run may encode data. Suspicious invisible pattern; payload not decoded.",
                "Remove the zero-width run.", f"Run of {len(run)} invisible characters ({cps}).", [aid],
            ))
        i = j

    # Aggregate ordinary zero-width observations into per-occurrence findings with contextual severity.
    count = len(zw_suspicious)
    for (s, e, cps, aids, joined) in zw_suspicious:
        sev = Severity.low
        why = "Isolated invisible character with no risky context."
        if joined and joined.lower() in SENSITIVE_WORDS:
            sev = Severity.medium
            why = f"It splits the security-sensitive word {joined!r}, which can evade keyword filters."
        elif count >= 3:
            sev = Severity.medium
            why = f"{count} unexplained invisible characters occur in this file."
        line_start = text.rfind("\n", 0, s) + 1
        line_end = text.find("\n", e)
        clean_line = "".join(c for c in text[line_start: line_end if line_end >= 0 else n] if not is_target(c))
        signals = instruction_signals(clean_line)
        if signals and (joined or count >= 3):
            sev = Severity.high
            why += f" With invisibles removed, the line matches instruction rules: {', '.join(signals)}."
        matches.append(hidden_match(
            "SS-UNI-001", "invisible_unicode", "Zero-width / default-ignorable character", sev, s, e,
            "Invisible characters are hard to see in editors and rendered views. " + why
            + " They can be legitimate; review in context.",
            "Remove the character unless it is required by the script or emoji sequence.",
            f"{cps} occurs here" + (f", inside {joined!r}" if joined else "") + ".", aids,
            inner_rule_ids=signals,
        ))
    return matches
