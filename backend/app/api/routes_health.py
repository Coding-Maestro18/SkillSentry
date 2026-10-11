from __future__ import annotations

from fastapi import APIRouter

from ..analyzers import unicode_hidden_content
from ..config import ANALYZER_VERSION, RULESET_VERSION, SUITE_VERSION
from ..model_adapter.local_model import get_adapter
from .deps import settings

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    s = settings()
    return {
        "api": "ok",
        "analyzer_version": ANALYZER_VERSION,
        "ruleset_version": RULESET_VERSION,
        "suite_version": SUITE_VERSION,
        "detectors": unicode_hidden_content.versions(),
        "model": get_adapter(s).health().model_dump(),
        "limits": {
            "max_upload_mb": s.max_upload_bytes // (1024 * 1024),
            "max_extracted_mb": s.max_extracted_bytes // (1024 * 1024),
            "max_files": s.max_files,
            "max_text_file_kb": s.max_text_file_bytes // 1024,
        },
    }
