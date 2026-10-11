from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from ..model_adapter.local_model import get_adapter
from ..reports.export import compare, to_json, to_markdown
from ..reports.fixes import clean_model_revision, deterministic_fix, unified_diff
from ..reports.sarif_export import to_sarif, validate_sarif
from ..schemas import Comparison, FixSuggestion, ScanReport, ScanState
from .deps import ApiError, get_report_or_404, settings, store

router = APIRouter()


@router.get("/api/scans/{scan_id}/report", response_model=ScanReport)
def report(scan_id: str) -> ScanReport:
    return get_report_or_404(scan_id)


@router.get("/api/scans/{scan_id}/export")
def export(scan_id: str, format: str = Query("json", pattern="^(json|markdown|sarif)$")):
    r = get_report_or_404(scan_id)
    name = f"skillsentry-{scan_id}"
    if format == "markdown":
        return PlainTextResponse(to_markdown(r), media_type="text/markdown; charset=utf-8",
                                 headers={"Content-Disposition": f'attachment; filename="{name}.md"'})
    if format == "sarif":
        sarif_data = to_sarif(r)
        valid, errs = validate_sarif(sarif_data)
        if not valid:
            raise ApiError(500, "SARIF_VALIDATION_FAILED", "Generated SARIF failed validation.", {"errors": errs[:20]})
        return JSONResponse(sarif_data, media_type="application/sarif+json",
                            headers={"Content-Disposition": f'attachment; filename="{name}.sarif"'})
    return JSONResponse(to_json(r), headers={"Content-Disposition": f'attachment; filename="{name}.json"'})



class FixRequest(BaseModel):
    finding_ids: Optional[list[str]] = None
    use_model: bool = True


@router.post("/api/scans/{scan_id}/fix-suggestion", response_model=FixSuggestion)
def fix_suggestion(scan_id: str, body: FixRequest) -> FixSuggestion:
    r = get_report_or_404(scan_id)
    if r.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Scan has not completed yet.")
    files = store().get_files(scan_id)
    findings = [f for f in r.findings if not body.finding_ids or f.finding_id in body.finding_ids]
    det = deterministic_fix(files, findings, r.annotations)
    if not body.use_model:
        return det
    adapter = get_adapter(settings())
    touched = {f.source_file for f in findings} & set(files)
    res = adapter.suggest_fix({p: files[p] for p in touched}, [f.model_dump(mode="json") for f in findings])
    if res.fix is None:
        det.model_status = f"{res.info.status}: {res.info.status_detail} Deterministic rule-based fix shown instead."
        return det
    revised = {}
    rationale = []
    for ff in res.fix.files:
        if ff.path in files:
            revised[ff.path] = clean_model_revision(ff.revised_content)
            rationale.append(f"{ff.path}: {ff.rationale}")
    if not revised:
        det.model_status = "Model fix referenced no known files; deterministic fix shown instead."
        return det
    return FixSuggestion(
        origin="model", model_status="ok (model-proposed; review before applying)",
        finding_ids=[f.finding_id for f in findings], rationale=rationale, revised_files=revised,
        diffs={p: unified_diff(p, files[p], t) for p, t in revised.items()},
    )


@router.get("/api/scans/{scan_id}/comparison", response_model=Comparison)
def comparison(scan_id: str) -> Comparison:
    revised = get_report_or_404(scan_id)
    if not revised.parent_scan_id:
        raise ApiError(400, "NOT_A_REVISION", "This scan is not a rerun of another scan.")
    if revised.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Revision scan has not completed yet.")
    original = get_report_or_404(revised.parent_scan_id)
    return compare(original, revised)
