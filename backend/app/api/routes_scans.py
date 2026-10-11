from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from ..analyzers.forensic_view import PREVIEW_NOTE, build_preview, build_reveal
from ..harness.runner import run_test
from ..ingest.archive_validator import IngestError, RawFile, read_zip
from ..pipeline import create_report, new_scan_id, run_pipeline
from ..schemas import FileView, RerunRequest, ScanState, ScanStatus, TestResult
from .deps import ApiError, get_report_or_404, settings, store

router = APIRouter()


async def _read_capped(upload: UploadFile, limit: int) -> bytes:
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise ApiError(413, "UPLOAD_TOO_LARGE", f"Upload exceeds {limit // (1024 * 1024)} MB.")
    return data


def _start(raw: list[RawFile], kind: str, background: BackgroundTasks, parent: Optional[str] = None, suite=None) -> ScanStatus:
    report = create_report(new_scan_id(), kind, parent)
    report.status = ScanState.validating
    report.stage_detail = "Upload validated"
    store().save(report)
    background.add_task(run_pipeline, report, raw, store(), settings(), suite)
    return ScanStatus(scan_id=report.scan_id, status=report.status, stage_detail=report.stage_detail,
                      parent_scan_id=parent)


@router.post("/api/scans", response_model=ScanStatus, status_code=202)
async def create_scan(
    background: BackgroundTasks,
    file: Optional[UploadFile] = File(default=None),
    skill_text: Optional[str] = Form(default=None),
) -> ScanStatus:
    s = settings()
    if file is not None and file.filename:
        data = await _read_capped(file, s.max_upload_bytes)
        try:
            raw = read_zip(data, s)
        except IngestError as exc:
            raise ApiError(400, exc.code, exc.message, exc.details) from exc
        if not raw:
            raise ApiError(400, "EMPTY_ARCHIVE", "The archive contains no files.")
        return _start(raw, "zip", background)
    if skill_text is not None and skill_text.strip():
        encoded = skill_text.encode("utf-8")
        if len(encoded) > s.max_text_file_bytes:
            raise ApiError(413, "TEXT_TOO_LARGE", "Pasted SKILL.md exceeds the text size limit.")
        return _start([RawFile(path="SKILL.md", data=encoded)], "text", background)
    raise ApiError(400, "NO_INPUT", "Upload a ZIP file (field 'file') or paste SKILL.md (field 'skill_text').")


@router.get("/api/scans", response_model=list[ScanStatus])
def list_scans() -> list[ScanStatus]:
    out = []
    for sid in store().list_ids()[-50:]:
        r = store().get(sid)
        if r:
            out.append(ScanStatus(scan_id=r.scan_id, status=r.status, stage_detail=r.stage_detail, error=r.error,
                                  parent_scan_id=r.parent_scan_id, skill_name=r.skill_name, created_at=r.created_at))
    return out


@router.get("/api/scans/{scan_id}", response_model=ScanStatus)
def scan_status(scan_id: str) -> ScanStatus:
    r = get_report_or_404(scan_id)
    return ScanStatus(scan_id=r.scan_id, status=r.status, stage_detail=r.stage_detail, error=r.error,
                      parent_scan_id=r.parent_scan_id)


@router.delete("/api/scans/{scan_id}")
def delete_scan(scan_id: str) -> dict:
    get_report_or_404(scan_id)
    store().delete(scan_id)
    return {"deleted": scan_id}


@router.get("/api/scans/{scan_id}/files")
def scan_files(scan_id: str) -> dict:
    r = get_report_or_404(scan_id)
    return {"files": [f.model_dump() for f in r.files],
            "coverage": {"scanned": sum(f.scanned for f in r.files), "total": len(r.files)}}


@router.get("/api/scans/{scan_id}/files/{file_id}/view", response_model=FileView)
def file_view(scan_id: str, file_id: str) -> FileView:
    r = get_report_or_404(scan_id)
    entry = next((f for f in r.files if f.file_id == file_id), None)
    if entry is None:
        raise ApiError(404, "FILE_NOT_FOUND", "No file with that ID in this scan.", {"file_id": file_id})
    if not entry.scanned:
        raise ApiError(409, "FILE_NOT_SCANNED", entry.skip_reason or "File was not scanned.")
    text = store().get_files(scan_id).get(entry.relative_path, "")
    anns = [a for a in r.annotations if a.file_id == file_id]
    return FileView(file_id=file_id, relative_path=entry.relative_path, raw=text, reveal=build_reveal(text, anns),
                    preview=build_preview(text, anns), annotations=anns, preview_note=PREVIEW_NOTE)


@router.post("/api/scans/{scan_id}/tests/{test_id}/run", response_model=TestResult)
def run_one(scan_id: str, test_id: str) -> TestResult:
    r = get_report_or_404(scan_id)
    if r.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Scan has not completed yet.")
    test = next((t for t in r.tests if t.test_id == test_id), None)
    if test is None:
        raise ApiError(404, "TEST_NOT_FOUND", "No validated test with that ID.", {"test_id": test_id})
    result = run_test(test, store().get_files(scan_id), r.findings)
    r.results = [result if x.test_id == test_id else x for x in r.results]
    store().save(r)
    return result


@router.post("/api/scans/{scan_id}/rerun", response_model=ScanStatus, status_code=202)
def rerun(scan_id: str, body: RerunRequest, background: BackgroundTasks) -> ScanStatus:
    """Rerun the exact same suite against a revised copy. The original scan is untouched."""
    r = get_report_or_404(scan_id)
    if r.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Original scan has not completed yet.")
    s = settings()
    original = dict(store().get_files(scan_id))
    for path, content in body.files.items():
        if path not in original:
            raise ApiError(400, "UNKNOWN_FILE", "Revisions may only replace files from the original scan.", {"path": path})
        if len(content.encode("utf-8")) > s.max_text_file_bytes:
            raise ApiError(413, "TEXT_TOO_LARGE", "Revised file exceeds the text size limit.", {"path": path})
        original[path] = content
    # Unscanned files (scripts/assets) are carried over as empty inventory-only placeholders.
    raw = [RawFile(path=p, data=t.encode("utf-8")) for p, t in original.items()]
    known = set(original)
    for f in r.files:
        if f.relative_path not in known:
            raw.append(RawFile(path=f.relative_path, data=b""))
    return _start(raw, "revision", background, parent=scan_id, suite=r.tests)
