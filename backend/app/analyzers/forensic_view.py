"""Build UI-safe forensic views. The original source is never modified.

* ``reveal`` – per-line segments; invisible characters become explicit labels like
  ``[U+200B ZERO WIDTH SPACE]``; flagged trailing whitespace shows ``·`` and ``⇥``.
* ``preview`` – an approximate rendered view: HTML comments and hidden elements
  removed, invisible characters dropped, tags stripped. Plain text; the frontend
  never renders it as HTML.
"""

from __future__ import annotations

import re

from ..schemas import FileAnnotation
from .common import cp_label, needs_escape
from .confusables import CONFUSABLE_MAP, skeleton

PREVIEW_NOTE = (
    "Approximate rendered view: comments and hidden-styled elements removed, invisible characters dropped, "
    "HTML tags stripped. Not a browser rendering engine; shown as plain text."
)


def build_reveal(text: str, annotations: list[FileAnnotation]) -> list[list[dict[str, str]]]:
    region_kind = [""] * len(text)
    region_label = [""] * len(text)
    ws_marked = [False] * len(text)
    for a in annotations:
        if a.annotation_type in ("html_comment", "hidden_html"):
            for k in range(a.start_offset, min(a.end_offset, len(text))):
                region_kind[k] = "comment" if a.annotation_type == "html_comment" else "hidden"
                region_label[k] = a.annotation_id
        elif a.annotation_type == "whitespace_anomaly":
            for k in range(a.start_offset, min(a.end_offset, len(text))):
                ws_marked[k] = True

    out: list[list[dict[str, str]]] = []
    line: list[dict[str, str]] = []

    def push(seg_text: str, kind: str, label: str = "") -> None:
        if line and line[-1]["kind"] == kind and kind in ("text", "comment", "hidden", "whitespace") and line[-1]["label"] == label:
            line[-1]["text"] += seg_text
        else:
            line.append({"text": seg_text, "kind": kind, "label": label})

    for i, ch in enumerate(text):
        if ch == "\n":
            out.append(line)
            line = []
            continue
        if ch == "\r":
            push("␍", "control", "U+000D CARRIAGE RETURN (CRLF line ending)")
            continue
        base_kind = region_kind[i] or "text"
        if needs_escape(ch):
            push(f"[{cp_label(ch)}]", "invisible", cp_label(ch))
        elif ch in CONFUSABLE_MAP:
            push(ch, "confusable", f"{cp_label(ch)} — looks like '{skeleton(ch)}'")
        elif ws_marked[i] and ch in " \t":
            push("·" if ch == " " else "⇥", "whitespace", "trailing whitespace anomaly")
        else:
            push(ch, base_kind, region_label[i] if base_kind != "text" else "")
    out.append(line)
    return out


def build_preview(text: str, annotations: list[FileAnnotation]) -> str:
    keep = [True] * len(text)
    for a in annotations:
        if a.annotation_type in ("html_comment", "hidden_html"):
            for k in range(a.start_offset, min(a.end_offset, len(text))):
                keep[k] = False
    visible = "".join(c for c, k in zip(text, keep) if k and not (needs_escape(c) and c not in "\u00a0\u3000"))
    visible = re.sub(r"<[^>\n]{1,200}>", "", visible)
    visible = visible.replace("\r\n", "\n")
    return re.sub(r"\n{3,}", "\n\n", visible)
