"""Run the deterministic analyzers over labelled fixtures and report honest counts.

Usage: python scripts/evaluate.py
Counts are per (fixture, expected rule). This is a tiny labelled set, NOT a
measure of general security accuracy.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.ingest.archive_validator import RawFile  # noqa: E402
from app.persistence.store import ScanStore  # noqa: E402
from app.pipeline import create_report, new_scan_id, run_pipeline  # noqa: E402


def main() -> int:
    import os
    import tempfile

    os.environ["SKILLSENTRY_ENABLE_MODEL_ANALYSIS"] = "false"
    labels = json.loads((ROOT / "tests/fixtures/labels.json").read_text())
    store = ScanStore(Path(tempfile.mkdtemp()))
    settings = get_settings()
    tp = fn = fp_benign = 0
    benign_total = 0
    rows = []
    times = []
    for name, lab in labels.items():
        base = ROOT / "tests/fixtures" / name
        raw = [RawFile(path=p.relative_to(base).as_posix(), data=p.read_bytes()) for p in base.rglob("*") if p.is_file()]
        t0 = time.monotonic()
        rep = run_pipeline(create_report(new_scan_id(), "zip"), raw, store, settings)
        times.append((time.monotonic() - t0) * 1000)
        got = {f.rule_id for f in rep.findings if f.severity.value in ("low", "medium", "high")}
        exp = set(lab["expected_rules"])
        hit, miss = exp & got, exp - got
        tp += len(hit)
        fn += len(miss)
        if lab["benign"]:
            benign_total += 1
            high_med = [f.rule_id for f in rep.findings if f.severity.value in ("medium", "high")]
            if high_med:
                fp_benign += 1
        fails = [r.test_id for r in rep.results if r.status == "fail"]
        rows.append((name, sorted(hit), sorted(miss), sorted(got - exp), fails))
    for name, hit, miss, extra, fails in rows:
        print(f"{name:38} hit={hit} missed={miss} extra={extra} failing_tests={fails}")
    print()
    print(f"Expected detections found: {tp}/{tp + fn}")
    print(f"Benign fixtures with any medium/high finding: {fp_benign}/{benign_total}")
    times.sort()
    print(f"Deterministic scan time (ms): median={times[len(times)//2]:.1f} max={times[-1]:.1f} (n={len(times)})")
    return 0 if fn == 0 and fp_benign == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
