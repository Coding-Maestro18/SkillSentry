"""Helpers shared by the hidden-content detectors."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from ..parser.source_map import SourceMap
from ..schemas import FileAnnotation, Severity
from .static_rules import RuleMatch

UNICODE_VERSION = unicodedata.unidata_version


def cp_label(ch: str) -> str:
    name = unicodedata.name(ch, None)
    if name is None:
        if 0xE0000 <= ord(ch) <= 0xE007F:
            name = "TAG CHARACTER"
        else:
            name = unicodedata.category(ch)
    return f"U+{ord(ch):04X} {name}"


def cp(ch: str) -> str:
    return f"U+{ord(ch):04X}"


def needs_escape(ch: str) -> bool:
    if ch in ("\n", "\t", " "):
        return False
    cat = unicodedata.category(ch)
    if cat in ("Cf", "Cc", "Co", "Cn", "Zl", "Zp"):
        return True
    if cat == "Zs":
        return True  # every non-ASCII space separator (ASCII space handled above)
    o = ord(ch)
    return o in (0x034F, 0x115F, 0x1160, 0x3164, 0xFFA0) or 0xFE00 <= o <= 0xFE0F or 0xE0100 <= o <= 0xE01EF


def escape_invisibles(s: str, limit: Optional[int] = None) -> str:
    out = []
    for ch in s:
        if ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        elif needs_escape(ch):
            out.append(f"[{cp_label(ch)}]")
        else:
            out.append(ch)
    res = "".join(out)
    if limit and len(res) > limit:
        res = res[:limit] + "…"
    return res


def excerpt(text: str, start: int, end: int, pad: int = 30) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    snippet = text[s:e].replace("\n", "⏎")
    return ("…" if s > 0 else "") + escape_invisibles(snippet, 400) + ("…" if e < len(text) else "")


@dataclass
class AnnotationSink:
    file_id: str
    path: str
    smap: SourceMap
    items: list[FileAnnotation] = field(default_factory=list)

    def add(
        self,
        annotation_type: str,
        start: int,
        end: int,
        detector_id: str,
        severity: Severity,
        notes: str = "",
        code_point: Optional[str] = None,
        unicode_name: Optional[str] = None,
        skeleton: Optional[str] = None,
    ) -> str:
        line, col = self.smap.position(start)
        eline, ecol = self.smap.position(max(start, end - 1))
        aid = f"A-{self.file_id[5:]}-{len(self.items) + 1:04d}"
        self.items.append(
            FileAnnotation(
                annotation_id=aid, file_id=self.file_id, relative_path=self.path, line=line, column=col,
                end_line=eline, end_column=ecol + 1, start_offset=start, end_offset=end,
                annotation_type=annotation_type,  # type: ignore[arg-type]
                code_point=code_point, unicode_name=unicode_name,
                escaped_excerpt=excerpt(self.smap.text, start, end), detector_id=detector_id,
                severity=severity, notes=notes, skeleton=skeleton,
            )
        )
        return aid


def hidden_match(
    rule_id: str, category: str, title: str, severity: Severity, start: int, end: int, rationale: str,
    remediation: str, observed: str, annotation_ids: list[str], **extra,
) -> RuleMatch:
    decoded = extra.pop("decoded_payload", None)
    decoder = extra.pop("decoder", None)
    return RuleMatch(
        rule_id=rule_id, category=category, title=title, severity=severity, start=start, end=end,
        rationale=rationale, remediation=remediation, observed=observed, decoded_payload=decoded,
        decoder=decoder, extra={"annotation_ids": annotation_ids, **extra},
    )
