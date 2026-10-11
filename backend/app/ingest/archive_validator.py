"""Safe ZIP validation and in-memory extraction.

Nothing is ever written to disk and nothing is executed. Entry sizes are
enforced while streaming, so lying headers (zip bombs) cannot bypass limits.
"""

from __future__ import annotations

import io
import posixpath
import stat
import unicodedata
import zipfile
from dataclasses import dataclass

from ..config import Settings


class IngestError(Exception):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class RawFile:
    path: str  # normalized, relative, forward slashes, skill root stripped
    data: bytes


_SUSPICIOUS_COMPONENTS = {"", ".", ".."}


def _validate_entry_name(name: str) -> str:
    if "\x00" in name:
        raise IngestError("INVALID_ARCHIVE", "Archive entry contains a NUL byte.", {"entry": repr(name)})
    if "\\" in name:
        raise IngestError("INVALID_ARCHIVE", "Archive entry uses backslash separators.", {"entry": name})
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        raise IngestError("INVALID_ARCHIVE", "Archive contains an absolute path.", {"entry": name})
    stripped = name.rstrip("/")
    parts = stripped.split("/")
    if any(p in ("..",) for p in parts):
        raise IngestError("INVALID_ARCHIVE", "The ZIP contains an unsupported or unsafe path.", {"entry": name})
    if any(p in _SUSPICIOUS_COMPONENTS for p in parts):
        raise IngestError("INVALID_ARCHIVE", "Archive entry has an empty or '.' path component.", {"entry": name})
    if any(unicodedata.category(c) in ("Cc", "Cf") for c in stripped):
        raise IngestError(
            "INVALID_ARCHIVE", "Archive entry name contains control/format characters.", {"entry": repr(name)}
        )
    normalized = posixpath.normpath(stripped)
    if normalized.startswith("..") or normalized.startswith("/"):
        raise IngestError("INVALID_ARCHIVE", "The ZIP contains an unsupported or unsafe path.", {"entry": name})
    return normalized


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def read_zip(data: bytes, settings: Settings) -> list[RawFile]:
    if len(data) > settings.max_upload_bytes:
        raise IngestError(
            "UPLOAD_TOO_LARGE",
            f"Compressed upload exceeds {settings.max_upload_bytes // (1024 * 1024)} MB.",
            {"size_bytes": len(data)},
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise IngestError("INVALID_ARCHIVE", "The upload is not a valid ZIP file.") from exc

    infos = zf.infolist()
    file_infos = [i for i in infos if not i.is_dir()]
    if len(file_infos) > settings.max_files:
        raise IngestError(
            "TOO_MANY_FILES", f"Archive contains more than {settings.max_files} files.", {"count": len(file_infos)}
        )

    seen: dict[str, str] = {}
    files: list[RawFile] = []
    total = 0
    for info in infos:
        name = _validate_entry_name(info.filename)
        if _is_symlink(info):
            raise IngestError("INVALID_ARCHIVE", "Archive contains a symbolic link.", {"entry": info.filename})
        if info.flag_bits & 0x1:
            raise IngestError("INVALID_ARCHIVE", "Encrypted archive entries are not supported.", {"entry": name})
        if info.is_dir():
            continue
        collision_key = unicodedata.normalize("NFC", name).casefold()
        if collision_key in seen:
            raise IngestError(
                "INVALID_ARCHIVE",
                "Archive contains duplicate or colliding paths.",
                {"entry": name, "collides_with": seen[collision_key]},
            )
        seen[collision_key] = name

        remaining = settings.max_extracted_bytes - total
        chunks: list[bytes] = []
        read = 0
        with zf.open(info) as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                read += len(chunk)
                if read > remaining:
                    raise IngestError(
                        "EXTRACTED_TOO_LARGE",
                        f"Extracted content exceeds {settings.max_extracted_bytes // (1024 * 1024)} MB.",
                        {"entry": name},
                    )
                chunks.append(chunk)
        total += read
        files.append(RawFile(path=name, data=b"".join(chunks)))

    return _strip_single_root(files)


def _strip_single_root(files: list[RawFile]) -> list[RawFile]:
    """Accept either ``SKILL.md`` at the archive root or a single top-level skill folder."""
    if any(f.path == "SKILL.md" for f in files):
        return files
    tops = {f.path.split("/", 1)[0] for f in files if "/" in f.path}
    root_files = [f for f in files if "/" not in f.path]
    if len(tops) == 1 and not root_files:
        prefix = tops.pop() + "/"
        return [RawFile(path=f.path[len(prefix):], data=f.data) for f in files]
    return files
