"""Runtime configuration loaded from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ANALYZER_VERSION = "0.1.0"
RULESET_VERSION = "2026.10-r1"
SUITE_VERSION = "suite-v1"
ADAPTER_VERSION = "0.1.0"

SUPPORTED_TEXT_EXTENSIONS = (".md", ".txt", ".yaml", ".yml", ".json", ".toml")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _load_dotenv() -> None:
    """Minimal .env loader so the app runs without python-dotenv."""
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"):
        if not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        break


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    storage_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("SKILLSENTRY_DATA_DIR", Path(__file__).resolve().parents[2] / "data" / "scans")
        )
    )
    max_upload_bytes: int = field(default_factory=lambda: _env_int("SKILLSENTRY_MAX_UPLOAD_MB", 10) * 1024 * 1024)
    max_extracted_bytes: int = field(
        default_factory=lambda: _env_int("SKILLSENTRY_MAX_EXTRACTED_MB", 25) * 1024 * 1024
    )
    max_files: int = field(default_factory=lambda: _env_int("SKILLSENTRY_MAX_FILES", 500))
    max_text_file_bytes: int = field(
        default_factory=lambda: _env_int("SKILLSENTRY_MAX_TEXT_FILE_KB", 2048) * 1024
    )
    model_provider: str = field(default_factory=lambda: os.getenv("SKILLSENTRY_MODEL_PROVIDER", "ollama"))
    model_name: str = field(default_factory=lambda: os.getenv("SKILLSENTRY_MODEL_NAME", "qwen2.5:7b-instruct"))
    model_license: str = field(default_factory=lambda: os.getenv("SKILLSENTRY_MODEL_LICENSE", "Apache-2.0"))
    model_revision: str = field(default_factory=lambda: os.getenv("SKILLSENTRY_MODEL_REVISION", "unknown"))
    model_base_url: str = field(
        default_factory=lambda: os.getenv("SKILLSENTRY_MODEL_BASE_URL", "http://localhost:11434")
    )
    model_timeout_seconds: int = field(default_factory=lambda: _env_int("SKILLSENTRY_MODEL_TIMEOUT_SECONDS", 45))
    enable_model_analysis: bool = field(
        default_factory=lambda: _env_bool("SKILLSENTRY_ENABLE_MODEL_ANALYSIS", True)
    )
    model_cache_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("SKILLSENTRY_MODEL_CACHE_DIR", Path(__file__).resolve().parents[2] / "data" / "model_cache")
        )
    )
    max_excerpt_chars: int = field(default_factory=lambda: _env_int("SKILLSENTRY_MODEL_MAX_EXCERPT_CHARS", 12000))


def get_settings() -> Settings:
    return Settings()
