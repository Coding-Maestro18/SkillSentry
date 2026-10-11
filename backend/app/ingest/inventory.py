"""Classify files, decode supported text and record scan coverage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from ..config import SUPPORTED_TEXT_EXTENSIONS, Settings
from ..schemas import FileEntry
from .archive_validator import RawFile


@dataclass
class TextFile:
    file_id: str
    path: str
    text: str  # decoded original; never mutated
    role: str


@dataclass
class Inventory:
    entries: list[FileEntry] = field(default_factory=list)
    texts: list[TextFile] = field(default_factory=list)


def _role(path: str) -> str:
    if path == "SKILL.md":
        return "skill_md"
    top = path.split("/", 1)[0]
    if top == "references":
        return "reference"
    if top == "scripts":
        return "script"
    if top == "assets":
        return "asset"
    return "other"


def _line_ending(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    if crlf and lf:
        return "mixed"
    if crlf:
        return "CRLF"
    return "LF" if lf else "none"


def build_inventory(raw_files: list[RawFile], settings: Settings) -> Inventory:
    inv = Inventory()
    for idx, rf in enumerate(sorted(raw_files, key=lambda f: (f.path != "SKILL.md", f.path))):
        file_id = f"file_{idx:03d}"
        role = _role(rf.path)
        sha = hashlib.sha256(rf.data).hexdigest()
        lower = rf.path.lower()
        in_scope = role in ("skill_md", "reference") and lower.endswith(SUPPORTED_TEXT_EXTENSIONS)
        entry = FileEntry(
            file_id=file_id,
            relative_path=rf.path,
            size_bytes=len(rf.data),
            scanned=False,
            role=role,  # type: ignore[arg-type]
            sha256=sha,
        )
        if not in_scope:
            if role == "script":
                entry.skip_reason = "Script inventoried only; SkillSentry never executes or scans scripts in the MVP."
            elif role in ("skill_md", "reference"):
                entry.skip_reason = "Unsupported file extension for text scanning."
            else:
                entry.skip_reason = "Outside SKILL.md and references/; inventoried only."
            inv.entries.append(entry)
            continue
        if len(rf.data) > settings.max_text_file_bytes:
            entry.skip_reason = f"Text file exceeds {settings.max_text_file_bytes // 1024} KB scan limit."
            inv.entries.append(entry)
            continue
        if b"\x00" in rf.data[:8192]:
            entry.skip_reason = "File appears to be binary (NUL bytes)."
            inv.entries.append(entry)
            continue
        try:
            text = rf.data.decode("utf-8")
            entry.encoding = "utf-8-bom" if text.startswith("\ufeff") else "utf-8"
        except UnicodeDecodeError as exc:
            # Preserve content for review instead of silently dropping bytes.
            text = rf.data.decode("utf-8", errors="replace")
            entry.encoding = "utf-8 (with replacement)"
            entry.warnings.append(
                f"Invalid UTF-8 at byte {exc.start}; undecodable bytes shown as U+FFFD for review."
            )
        entry.scanned = True
        entry.line_ending = _line_ending(text)
        if not text.strip():
            entry.warnings.append("File is empty or whitespace-only.")
        inv.entries.append(entry)
        inv.texts.append(TextFile(file_id=file_id, path=rf.path, text=text, role=role))
    return inv
