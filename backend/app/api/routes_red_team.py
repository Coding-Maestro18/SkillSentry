"""API routes for bounded adaptive red-team testing (Feature E)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..schemas import ScanState
from ..test_generation.adaptive import (
    AdaptiveRedTeamRun,
    advance_red_team_run,
    create_red_team_run,
    get_run,
    stop_red_team_run,
)
from .deps import ApiError, get_report_or_404, store

router = APIRouter()


class StartRedTeamRequest(BaseModel):
    advance_first_round: bool = True


@router.post("/api/scans/{scan_id}/red-team-runs", response_model=AdaptiveRedTeamRun)
def start_red_team(scan_id: str, req: StartRedTeamRequest) -> AdaptiveRedTeamRun:
    report = get_report_or_404(scan_id)
    if report.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Scan has not completed yet.")

    files = store().get_files(scan_id)
    run = create_red_team_run(report)

    if req.advance_first_round:
        run = advance_red_team_run(run, report, files)

    return run


@router.get("/api/red-team-runs/{run_id}", response_model=AdaptiveRedTeamRun)
def get_red_team_run(run_id: str) -> AdaptiveRedTeamRun:
    run = get_run(run_id)
    if not run:
        raise ApiError(404, "RUN_NOT_FOUND", f"Adaptive run '{run_id}' not found.")
    return run


@router.post("/api/red-team-runs/{run_id}/advance", response_model=AdaptiveRedTeamRun)
def advance_round(run_id: str) -> AdaptiveRedTeamRun:
    run = get_run(run_id)
    if not run:
        raise ApiError(404, "RUN_NOT_FOUND", f"Adaptive run '{run_id}' not found.")

    if run.status in ("completed", "stopped"):
        return run

    if run.current_round >= run.max_rounds:
        raise ApiError(400, "ADAPTIVE_BUDGET_EXCEEDED", "Maximum 3 rounds already completed.")

    report = get_report_or_404(run.scan_id)
    files = store().get_files(run.scan_id)
    return advance_red_team_run(run, report, files)


@router.post("/api/red-team-runs/{run_id}/stop", response_model=AdaptiveRedTeamRun)
def stop_round(run_id: str) -> AdaptiveRedTeamRun:
    run = stop_red_team_run(run_id)
    if not run:
        raise ApiError(404, "RUN_NOT_FOUND", f"Adaptive run '{run_id}' not found.")
    return run
