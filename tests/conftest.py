import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("SKILLSENTRY_ENABLE_MODEL_ANALYSIS", "false")
os.environ.setdefault("SKILLSENTRY_DATA_DIR", tempfile.mkdtemp(prefix="skillsentry-test-"))

FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict[str, str]:
    base = FIXTURES / name
    return {p.relative_to(base).as_posix(): p.read_text(encoding="utf-8") for p in base.rglob("*") if p.is_file()}
