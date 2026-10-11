"""Stable mapping between character offsets and 1-based line/column positions.

Offsets are Python code-point indices into the decoded original text. Columns
are 1-based code-point columns. CRLF line endings are handled: the ``\\r`` belongs
to the line it terminates and is never counted as a column of the next line.
"""

from __future__ import annotations

import bisect


class SourceMap:
    def __init__(self, text: str):
        self.text = text
        self.line_starts = [0]
        for i, ch in enumerate(text):
            if ch == "\n":
                self.line_starts.append(i + 1)

    def position(self, offset: int) -> tuple[int, int]:
        offset = max(0, min(offset, len(self.text)))
        line_idx = bisect.bisect_right(self.line_starts, offset) - 1
        return line_idx + 1, offset - self.line_starts[line_idx] + 1

    def line_text(self, line: int) -> str:
        start = self.line_starts[line - 1]
        end = self.line_starts[line] - 1 if line < len(self.line_starts) else len(self.text)
        return self.text[start:end].rstrip("\r")

    @property
    def line_count(self) -> int:
        return len(self.line_starts)

    def lines(self) -> list[str]:
        return [self.line_text(i) for i in range(1, self.line_count + 1)]

    def utf8_byte_offset(self, offset: int) -> int:
        return len(self.text[:offset].encode("utf-8"))
