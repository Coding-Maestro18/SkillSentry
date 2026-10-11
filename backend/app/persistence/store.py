"""Local JSON artifact store: one directory per scan."""

from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path
from typing import Optional

from ..schemas import ScanReport

_ID = re.compile(r"^scan_[0-9a-f]{12}$")
_ARTIFACT_KINDS = {"campaigns", "red_team"}
_ARTIFACT_ID = re.compile(r"^[a-z]+_[0-9a-f]{12}$")


class ScanStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._reports: dict[str, ScanReport] = {}
        self._files: dict[str, dict[str, str]] = {}

    def _dir(self, scan_id: str) -> Path:
        if not _ID.match(scan_id):
            raise KeyError(scan_id)
        return self.root / scan_id

    def save(self, report: ScanReport) -> None:
        with self._lock:
            self._reports[report.scan_id] = report
            d = self._dir(report.scan_id)
            d.mkdir(parents=True, exist_ok=True)
            tmp = d / "report.json.tmp"
            tmp.write_text(report.model_dump_json(indent=1), encoding="utf-8")
            tmp.replace(d / "report.json")

    def save_files(self, scan_id: str, files: dict[str, str]) -> None:
        with self._lock:
            self._files[scan_id] = files
            d = self._dir(scan_id)
            d.mkdir(parents=True, exist_ok=True)
            # ensure_ascii keeps every invisible code point as an explicit \\uXXXX escape on disk
            (d / "files.json").write_text(json.dumps(files, ensure_ascii=True), encoding="utf-8")

    def get(self, scan_id: str) -> Optional[ScanReport]:
        with self._lock:
            if scan_id in self._reports:
                return self._reports[scan_id]
            try:
                p = self._dir(scan_id) / "report.json"
            except KeyError:
                return None
            if not p.exists():
                return None
            rep = ScanReport.model_validate_json(p.read_text(encoding="utf-8"))
            self._reports[scan_id] = rep
            return rep

    def get_files(self, scan_id: str) -> dict[str, str]:
        with self._lock:
            if scan_id in self._files:
                return self._files[scan_id]
            try:
                p = self._dir(scan_id) / "files.json"
            except KeyError:
                return {}
            if not p.exists():
                return {}
            files = json.loads(p.read_text(encoding="utf-8"))
            self._files[scan_id] = files
            return files

    # -- policy revisions: immutable, numbered; the latest is the current one ---------
    def _policy_dir(self, scan_id: str) -> Path:
        return self._dir(scan_id) / "policies"

    def save_policy(self, scan_id: str, policy_yaml: str) -> int:
        """Store a new immutable policy revision and return its number (1-based)."""
        with self._lock:
            d = self._policy_dir(scan_id)
            d.mkdir(parents=True, exist_ok=True)
            rev = len(self.policy_revisions(scan_id)) + 1
            (d / f"r{rev:03d}.yaml").write_text(policy_yaml, encoding="utf-8")
            return rev

    def policy_revisions(self, scan_id: str) -> list[int]:
        try:
            d = self._policy_dir(scan_id)
        except KeyError:
            return []
        if not d.exists():
            return []
        return sorted(int(p.stem[1:]) for p in d.glob("r[0-9][0-9][0-9].yaml"))

    def get_policy(self, scan_id: str, revision: Optional[int] = None) -> Optional[tuple[int, str]]:
        """Return ``(revision, yaml)`` for the given or latest revision."""
        with self._lock:
            revs = self.policy_revisions(scan_id)
            if not revs:
                return None
            rev = revision if revision is not None else revs[-1]
            if rev not in revs:
                return None
            return rev, (self._policy_dir(scan_id) / f"r{rev:03d}.yaml").read_text(encoding="utf-8")

    # -- extension artifacts (campaigns, adaptive red-team runs) ---------------------
    def _artifact_path(self, kind: str, artifact_id: str) -> Path:
        if kind not in _ARTIFACT_KINDS or not _ARTIFACT_ID.match(artifact_id):
            raise KeyError(artifact_id)
        return self.root / "_" / kind / f"{artifact_id}.json"

    def save_artifact(self, kind: str, artifact_id: str, data_json: str) -> None:
        with self._lock:
            p = self._artifact_path(kind, artifact_id)
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(data_json, encoding="utf-8")
            tmp.replace(p)

    def get_artifact(self, kind: str, artifact_id: str) -> Optional[str]:
        with self._lock:
            try:
                p = self._artifact_path(kind, artifact_id)
            except KeyError:
                return None
            return p.read_text(encoding="utf-8") if p.exists() else None

    def delete_artifact(self, kind: str, artifact_id: str) -> None:
        with self._lock:
            try:
                p = self._artifact_path(kind, artifact_id)
            except KeyError:
                return
            p.unlink(missing_ok=True)

    def list_artifacts(self, kind: str) -> list[str]:
        d = self.root / "_" / kind
        if kind not in _ARTIFACT_KINDS or not d.exists():
            return []
        return [p.read_text(encoding="utf-8") for p in sorted(d.glob("*.json"))]

    def link_extension(self, scan_id: str, key: str, value: str) -> None:
        """Record an extension artifact ID on the scan report (``report.extensions[key]``)."""
        with self._lock:
            rep = self.get(scan_id)
            if rep is None:
                return
            ids = rep.extensions.setdefault(key, [])
            if value not in ids:
                ids.append(value)
                self.save(rep)


    def unlink_extension(self, scan_id: str, key: str, value: str) -> None:
        with self._lock:
            rep = self.get(scan_id)
            if rep is not None and value in rep.extensions.get(key, []):
                rep.extensions[key].remove(value)
                self.save(rep)

    def delete(self, scan_id: str) -> bool:
        with self._lock:
            self._reports.pop(scan_id, None)
            self._files.pop(scan_id, None)
            try:
                d = self._dir(scan_id)
            except KeyError:
                return False
            if d.exists():
                shutil.rmtree(d)
                return True
            return False

    def list_ids(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir() and _ID.match(p.name))
