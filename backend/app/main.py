"""SkillSentry FastAPI application."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import (
    routes_campaigns,
    routes_health,
    routes_policy,
    routes_red_team,
    routes_reports,
    routes_scans,
)
from .api.deps import request_id
from .config import ANALYZER_VERSION

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("skillsentry")

app = FastAPI(
    title="SkillSentry",
    version=ANALYZER_VERSION,
    description="Security testing workbench for AI Agent Skills. Analyzes untrusted content, simulates behaviour "
    "with mock tools, never executes uploaded code.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if not request.url.path.startswith(("/docs", "/redoc")):  # Swagger UI loads its assets from a CDN
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'",
        )
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "HTTP_ERROR", "message": str(exc.detail), "details": {}}
    return JSONResponse(status_code=exc.status_code, content={"error": {**detail, "request_id": request_id()}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    errs = [{"loc": [str(x) for x in e.get("loc", [])], "msg": e.get("msg", "")} for e in exc.errors()][:10]
    return JSONResponse(status_code=422, content={"error": {"code": "INVALID_REQUEST", "message": "Request validation failed.",
                                                            "details": {"errors": errs}, "request_id": request_id()}})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    rid = request_id()
    log.exception("unhandled error %s", rid)
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error.",
                                                            "details": {}, "request_id": rid}})


app.include_router(routes_health.router)
app.include_router(routes_scans.router)
app.include_router(routes_reports.router)
app.include_router(routes_policy.router)
app.include_router(routes_red_team.router)
app.include_router(routes_campaigns.router)




# Serve the built frontend (frontend/dist) when present, so one process runs the whole app.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_DIST / "index.html")
