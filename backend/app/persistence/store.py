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

    def save_policy(self, scan_id: str, policy_yaml: str) -> None:
        with self._lock:
            d = self._dir(scan_id)
            d.mkdir(parents=True, exist_ok=True)
            (d / "SKILL_POLICY.yaml").write_text(policy_yaml, encoding="utf-8")

    def get_policy(self, scan_id: str) -> Optional[str]:
        with self._lock:
            try:
                p = self._dir(scan_id) / "SKILL_POLICY.yaml"
            except KeyError:
                return None
            if not p.exists():
                return None
            return p.read_text(encoding="utf-8")


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
