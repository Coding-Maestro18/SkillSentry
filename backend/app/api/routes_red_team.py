"""API routes for bounded adaptive red-team testing (Feature E)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..model_adapter.local_model import get_adapter
from ..schemas import ScanState
from ..test_generation.adaptive import (
    AdaptiveRedTeamRun,
    advance_red_team_run,
    create_red_team_run,
    get_run,
    list_runs_for_scan,
    rerun_accepted,
    stop_red_team_run,
)
from .deps import ApiError, get_report_or_404, settings, store

router = APIRouter()


class StartRedTeamRequest(BaseModel):
    advance_first_round: bool = True


def _run_or_404(run_id: str) -> AdaptiveRedTeamRun:
    run = get_run(run_id, store())
    if not run:
        raise ApiError(404, "RUN_NOT_FOUND", f"Adaptive run '{run_id}' not found.")
    return run


@router.post("/api/scans/{scan_id}/red-team-runs", response_model=AdaptiveRedTeamRun)
def start_red_team(scan_id: str, req: StartRedTeamRequest) -> AdaptiveRedTeamRun:
    report = get_report_or_404(scan_id)
    if report.status != ScanState.completed:
        raise ApiError(409, "SCAN_NOT_READY", "Scan has not completed yet.")
    run = create_red_team_run(report, store())
    if req.advance_first_round:
        run = advance_red_team_run(run, report, store().get_files(scan_id), get_adapter(settings()), store())
    return run


@router.get("/api/scans/{scan_id}/red-team-runs", response_model=list[AdaptiveRedTeamRun])
def list_red_team_runs(scan_id: str) -> list[AdaptiveRedTeamRun]:
    get_report_or_404(scan_id)
    return list_runs_for_scan(scan_id, store())


@router.get("/api/red-team-runs/{run_id}", response_model=AdaptiveRedTeamRun)
def get_red_team_run(run_id: str) -> AdaptiveRedTeamRun:
    return _run_or_404(run_id)


@router.post("/api/red-team-runs/{run_id}/advance", response_model=AdaptiveRedTeamRun)
def advance_round(run_id: str) -> AdaptiveRedTeamRun:
    run = _run_or_404(run_id)
    if run.status in ("completed", "stopped", "failed"):
        return run
    if run.current_round >= run.max_rounds:
        raise ApiError(400, "ADAPTIVE_BUDGET_EXCEEDED", f"All {run.max_rounds} rounds have already run.")
    report = get_report_or_404(run.scan_id)
    return advance_red_team_run(run, report, store().get_files(run.scan_id), get_adapter(settings()), store())


@router.post("/api/red-team-runs/{run_id}/rerun", response_model=AdaptiveRedTeamRun)
def rerun_run(run_id: str) -> AdaptiveRedTeamRun:
    """Re-run accepted candidates from their saved definitions (no model call)."""
    run = _run_or_404(run_id)
    report = get_report_or_404(run.scan_id)
    return rerun_accepted(run, report, store().get_files(run.scan_id), store())


@router.post("/api/red-team-runs/{run_id}/stop", response_model=AdaptiveRedTeamRun)
def stop_round(run_id: str) -> AdaptiveRedTeamRun:
    _run_or_404(run_id)
    return stop_red_team_run(run_id, store())
