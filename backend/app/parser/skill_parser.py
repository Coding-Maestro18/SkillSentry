"""Parse SKILL.md frontmatter as inert data (never as executable configuration)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_FRONTMATTER = re.compile(r"\A\ufeff?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_KEY = re.compile(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$")


@dataclass
class ParsedSkill:
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body_offset: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def name(self) -> str | None:
        v = self.frontmatter.get("name")
        return str(v) if isinstance(v, (str, int, float)) else None

    @property
    def description(self) -> str | None:
        v = self.frontmatter.get("description")
        return str(v) if isinstance(v, (str, int, float)) else None

    @property
    def declared_tools(self) -> list[str]:
        for key in ("allowed-tools", "allowed_tools", "tools"):
            v = self.frontmatter.get(key)
            if isinstance(v, list):
                return [str(x) for x in v]
            if isinstance(v, str) and v.strip():
                return [t.strip() for t in re.split(r"[,\s]+", v) if t.strip()]
        return []


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def parse_frontmatter_block(block: str) -> tuple[dict[str, Any], list[str]]:
    """Tiny YAML subset: scalars, quoted scalars, ``- item`` lists, ``|``/``>`` blocks, inline ``[a, b]``."""
    data: dict[str, Any] = {}
    problems: list[str] = []
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = _KEY.match(line)
        if not m or line[:1].isspace():
            problems.append(f"Unrecognized frontmatter line {i + 2}: {line.strip()[:60]!r}")
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if value in ("|", ">", "|-", ">-"):
            buf = []
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            data[key] = ("\n" if value.startswith("|") else " ").join(buf).strip()
            continue
        if value == "":
            items = []
            nested: dict[str, str] = {}
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or not lines[i].strip()):
                s = lines[i].strip()
                if s.startswith("- "):
                    items.append(_scalar(s[2:]))
                elif s and _KEY.match(s):
                    km = _KEY.match(s)
                    nested[km.group(1)] = _scalar(km.group(2))  # type: ignore[union-attr]
                i += 1
            data[key] = items if items else (nested if nested else "")
            continue
        if value.startswith("[") and value.endswith("]"):
            data[key] = [_scalar(x) for x in value[1:-1].split(",") if x.strip()]
        else:
            data[key] = _scalar(value)
        i += 1
    return data, problems


def parse_skill(text: str) -> ParsedSkill:
    parsed = ParsedSkill()
    m = _FRONTMATTER.match(text)
    if not m:
        if text.lstrip("\ufeff").startswith("---"):
            parsed.problems.append("Frontmatter starts with '---' but is not terminated.")
        else:
            parsed.problems.append("SKILL.md has no YAML frontmatter block.")
        return parsed
    data, problems = parse_frontmatter_block(m.group(1))
    parsed.frontmatter = data
    parsed.body_offset = m.end()
    parsed.problems.extend(problems)
    if not parsed.name:
        parsed.problems.append("Frontmatter is missing required field 'name'.")
    if not parsed.description:
        parsed.problems.append("Frontmatter is missing required field 'description'.")
    return parsed
