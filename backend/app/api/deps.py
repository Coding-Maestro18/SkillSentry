"""Shared API state and error helpers."""

from __future__ import annotations

import secrets
from functools import lru_cache

from fastapi import HTTPException

from ..config import Settings, get_settings
from ..persistence.store import ScanStore
from ..schemas import ScanReport


class ApiError(HTTPException):
    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=status, detail={"code": code, "message": message, "details": details or {}})


def request_id() -> str:
    return "req_" + secrets.token_hex(6)


@lru_cache
def settings() -> Settings:
    return get_settings()


@lru_cache
def store() -> ScanStore:
    return ScanStore(settings().storage_dir)


def get_report_or_404(scan_id: str) -> ScanReport:
    rep = store().get(scan_id)
    if rep is None:
        raise ApiError(404, "SCAN_NOT_FOUND", "No scan with that ID.", {"scan_id": scan_id})
    return rep
