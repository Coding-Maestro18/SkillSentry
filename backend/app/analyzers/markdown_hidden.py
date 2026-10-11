"""HTML comments and common hidden-presentation patterns in Markdown/HTML source.

This is conservative pattern matching, NOT a browser rendering or CSS engine.
Content is reported as present in source and potentially hidden in rendered
views; actual exposure to a model depends on the skill loader/runtime.
"""

from __future__ import annotations

import re

from ..schemas import Severity
from .common import AnnotationSink, escape_invisibles, hidden_match
from .patterns import IMPERATIVE_START
from .static_rules import RuleMatch, instruction_signals

DETECTOR_COMMENT = "markdown.html_comment.v1"
DETECTOR_STYLE = "markdown.hidden_style.v1"

LIMITATION = "Regex-based detection; SkillSentry is not a full HTML/CSS rendering engine."

_FENCE = re.compile(r"^(?P<f>```|~~~)[^\n]*\n.*?^(?P=f)[ \t]*$", re.MULTILINE | re.DOTALL)
_OPEN_TAG = re.compile(
    r"<(?P<tag>[a-zA-Z][a-zA-Z0-9]*)\b(?P<attrs>[^>]*)>", re.DOTALL
)
_STYLE_ATTR = re.compile(r"\bstyle\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", re.IGNORECASE)
_HIDDEN_DECLS = [
    (re.compile(r"display\s*:\s*none", re.I), "display:none"),
    (re.compile(r"visibility\s*:\s*hidden", re.I), "visibility:hidden"),
    (re.compile(r"(?<![-\w])opacity\s*:\s*0(?:\.0+)?\s*(?:;|$|!)", re.I), "opacity:0"),
    (re.compile(r"font-size\s*:\s*0(?:\.0+)?(?:px|em|rem|pt|%)?\s*(?:;|$|!)", re.I), "font-size:0"),
    (re.compile(r"(?:max-)?(?:height|width)\s*:\s*0(?:px)?\s*;[^\"']*overflow\s*:\s*hidden", re.I), "zero-size + overflow:hidden"),
    (re.compile(r"(?:left|top|text-indent)\s*:\s*-\d{3,}", re.I), "off-screen positioning"),
    (re.compile(r"(?<![-\w])color\s*:\s*transparent", re.I), "color:transparent"),
]
_COLOR = re.compile(r"(?<![-\w])color\s*:\s*([#\w(),.\s%]+?)\s*(?:;|$|!)", re.I)
_BG = re.compile(r"background(?:-color)?\s*:\s*([#\w(),.\s%]+?)\s*(?:;|$|!)", re.I)
_HIDDEN_ATTR = re.compile(r"(?:^|\s)hidden(?:\s|=|$)", re.I)

_NAMED = {"white": "#ffffff", "black": "#000000", "#fff": "#ffffff", "#000": "#000000"}


def _norm_color(c: str) -> str:
    c = c.strip().lower().replace(" ", "")
    return _NAMED.get(c, c)


def _fenced_ranges(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in _FENCE.finditer(text)]


def _in_ranges(pos: int, ranges: list[tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in ranges)


def _assess(content: str) -> tuple[Severity, list[str], bool]:
    signals = instruction_signals(content)
    imperative = any(IMPERATIVE_START.search(l) for l in content.splitlines()) or bool(
        re.search(r"\b(?:assistant|the\s+ai|the\s+model|the\s+agent|llm)\b", content, re.I)
    )
    if signals:
        return Severity.high, signals, imperative
    if imperative:
        return Severity.medium, signals, imperative
    return Severity.informational, signals, imperative


def scan(text: str, sink: AnnotationSink) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    fences = _fenced_ranges(text)

    # --- HTML comments -------------------------------------------------------
    pos = 0
    while True:
        s = text.find("<!--", pos)
        if s < 0:
            break
        if _in_ranges(s, fences):
            pos = s + 4
            continue
        e = text.find("-->", s + 4)
        unterminated = e < 0
        end = len(text) if unterminated else e + 3
        content = text[s + 4: (len(text) if unterminated else e)]
        pos = end
        if not content.strip() and not unterminated:
            continue
        sev, signals, imperative = _assess(content)
        if unterminated and sev in (Severity.informational, Severity.low):
            sev = Severity.medium
        note = ("Unterminated comment: everything after '<!--' may be hidden in rendered views. " if unterminated else "") + (
            f"Hidden content matches rules {', '.join(signals)}." if signals
            else "Contains instruction-like language." if imperative else "Ordinary comment text."
        )
        aid = sink.add("html_comment", s, end, DETECTOR_COMMENT, sev, note)
        if unterminated:
            title = "Unterminated HTML comment"
        elif signals:
            title = "Suspicious instruction hidden in HTML comment"
        elif imperative:
            title = "Instruction-like text in HTML comment"
        else:
            title = "Non-empty HTML comment (hidden in rendered view)"
        matches.append(hidden_match(
            "SS-HID-003" if unterminated else "SS-HID-001", "hidden_comment", title, sev, s, end,
            "Text inside <!-- --> is not shown in typical rendered Markdown but is present in the source a model "
            "may read. " + ("Its content contains directives aimed at the agent." if (signals or imperative)
                            else "Ordinary comments are usually benign editorial notes."),
            "Move legitimate notes into visible text or delete the comment; never place agent directives in comments.",
            f"Comment content (escaped): {escape_invisibles(content.strip(), 300)!r}", [aid],
            hidden_content=content.strip()[:2000], inner_rule_ids=signals,
        ))

    # --- Hidden HTML styling -------------------------------------------------
    for m in _OPEN_TAG.finditer(text):
        if _in_ranges(m.start(), fences) or text.startswith("<!--", m.start()):
            continue
        attrs = m.group("attrs")
        reasons: list[str] = []
        sm = _STYLE_ATTR.search(attrs)
        style = (sm.group(1) or sm.group(2) or "") if sm else ""
        for rx, label in _HIDDEN_DECLS:
            if style and rx.search(style + ";"):
                reasons.append(label)
        if style:
            cm, bm = _COLOR.search(style + ";"), _BG.search(style + ";")
            if cm and bm and _norm_color(cm.group(1)) == _norm_color(bm.group(1)):
                reasons.append(f"same foreground/background colour ({cm.group(1).strip()})")
        if _HIDDEN_ATTR.search(attrs):
            reasons.append("hidden attribute")
        if not reasons:
            continue
        tag = m.group("tag").lower()
        close = re.compile(rf"</{tag}\s*>", re.I).search(text, m.end())
        end = close.end() if close else min(len(text), m.end() + 500)
        inner = text[m.end(): close.start() if close else end]
        inner_text = re.sub(r"<[^>]+>", "", inner).strip()
        sev, signals, imperative = _assess(inner_text)
        sev = Severity.high if signals else (Severity.medium if (imperative or inner_text) else Severity.low)
        aid = sink.add("hidden_html", m.start(), end, DETECTOR_STYLE, sev,
                       f"Hidden via {', '.join(reasons)}. {LIMITATION}")
        matches.append(hidden_match(
            "SS-HID-002", "hidden_html", "Content hidden with HTML/CSS styling", sev, m.start(), end,
            f"<{tag}> uses {', '.join(reasons)}, so its text may be invisible in rendered views while remaining in "
            f"the source. {LIMITATION}" + (f" Hidden text matches rules: {', '.join(signals)}." if signals else ""),
            "Remove hidden elements; any guidance for the agent should be visible to human reviewers.",
            f"Hidden element text (escaped): {escape_invisibles(inner_text, 300)!r}", [aid],
            hidden_content=inner_text[:2000], inner_rule_ids=signals,
        ))
    return matches

