"""API router for multi-skill attack chains (Feature A)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from ..campaigns.coordinator import create_campaign, get_campaign, list_campaigns, simulate_campaign
from ..campaigns.schemas import Campaign, CampaignReport, CreateCampaignRequest
from ..reports.sarif_export import campaign_to_sarif, validate_sarif
from .deps import ApiError, store

router = APIRouter()


def _campaign_or_404(campaign_id: str) -> Campaign:
    camp = get_campaign(campaign_id, store())
    if not camp:
        raise ApiError(404, "CAMPAIGN_NOT_FOUND", f"Campaign '{campaign_id}' not found.")
    return camp


@router.post("/api/campaigns", response_model=Campaign)
def create_campaign_endpoint(req: CreateCampaignRequest) -> Campaign:
    try:
        return create_campaign(
            store=store(),
            scan_ids=req.scan_ids,
            handoff_fixture_id=req.handoff_fixture_id or "handoff_fixture_001",
            handoff_content=req.handoff_content,
            campaign_name=req.campaign_name,
        )
    except KeyError as exc:
        raise ApiError(404, "SCAN_NOT_FOUND", str(exc).strip("'\""))
    except ValueError as exc:
        raise ApiError(400, "INVALID_CAMPAIGN", str(exc))


@router.get("/api/campaigns", response_model=list[Campaign])
def list_campaigns_endpoint() -> list[Campaign]:
    return list_campaigns(store())


@router.get("/api/campaigns/{campaign_id}", response_model=Campaign)
def get_campaign_endpoint(campaign_id: str) -> Campaign:
    return _campaign_or_404(campaign_id)


@router.post("/api/campaigns/{campaign_id}/simulate", response_model=Campaign)
def simulate_campaign_endpoint(campaign_id: str) -> Campaign:
    _campaign_or_404(campaign_id)
    try:
        return simulate_campaign(store=store(), campaign_id=campaign_id)
    except KeyError as exc:
        raise ApiError(404, "SCAN_NOT_FOUND", str(exc).strip("'\""))


@router.get("/api/campaigns/{campaign_id}/report", response_model=CampaignReport)
def get_campaign_report_endpoint(campaign_id: str) -> CampaignReport:
    camp = _campaign_or_404(campaign_id)
    scans_meta: list[dict[str, Any]] = []
    findings_by_scan: dict[str, list] = {}
    for sid in camp.scan_ids:
        r = store().get(sid)
        if r:
            scans_meta.append({
                "scan_id": r.scan_id,
                "skill_name": r.skill_name,
                "files_count": len(r.files),
                "findings_count": len(r.findings),
            })
            findings_by_scan[sid] = r.findings
    return CampaignReport(
        campaign=camp,
        participating_scans=scans_meta,
        findings_by_scan=findings_by_scan,
        traces=[ev for res in camp.results for ev in res.events],
    )


@router.get("/api/campaigns/{campaign_id}/export")
def export_campaign(campaign_id: str, format: str = Query("sarif", pattern="^sarif$")):
    camp = _campaign_or_404(campaign_id)
    reports = [r for r in (store().get(sid) for sid in camp.scan_ids) if r]
    sarif = campaign_to_sarif(campaign_id, reports)
    valid, errs = validate_sarif(sarif)
    if not valid:
        raise ApiError(500, "SARIF_VALIDATION_FAILED", "Generated SARIF failed validation.", {"errors": errs[:20]})
    return JSONResponse(sarif, media_type="application/sarif+json",
                        headers={"Content-Disposition": f'attachment; filename="skillsentry-{campaign_id}.sarif"'})
