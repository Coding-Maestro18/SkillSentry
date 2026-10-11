"""Invisible Content & Unicode Deception Scanner (orchestrator)."""

from __future__ import annotations

from ..parser.source_map import SourceMap
from ..schemas import FileAnnotation
from . import confusables, invisible_chars, markdown_hidden, whitespace
from .common import UNICODE_VERSION, AnnotationSink
from .static_rules import RuleMatch

SCANNER_VERSION = "hidden-content-1.0"


def scan_file(file_id: str, path: str, text: str, smap: SourceMap | None = None) -> tuple[list[FileAnnotation], list[RuleMatch]]:
    smap = smap or SourceMap(text)
    sink = AnnotationSink(file_id=file_id, path=path, smap=smap)
    matches: list[RuleMatch] = []
    matches += invisible_chars.scan(text, sink)
    matches += confusables.scan(text, sink)
    matches += markdown_hidden.scan(text, sink)
    matches += whitespace.scan(text, sink)
    return sink.items, matches


def versions() -> dict[str, str]:
    return {
        "scanner": SCANNER_VERSION,
        "unicode": UNICODE_VERSION,
        "confusables": confusables.CONFUSABLES_VERSION,
        "whitespace_decoder": whitespace.DECODER,
    }
