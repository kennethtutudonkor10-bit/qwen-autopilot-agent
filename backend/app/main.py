"""FastAPI surface for the Qwen Autopilot Agent.

Endpoints:
  POST /runs                 start a run from an uploaded manuscript
  GET  /runs/{id}            poll run state + trace (for the dashboard)
  POST /runs/{id}/resume     human checkpoint: approve/edit/reject
  GET  /healthz
"""
from __future__ import annotations

import os
import uuid

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

from . import orchestrator, store
from .aliyun import oss
from .config import get_settings

settings = get_settings()
app = FastAPI(title="Qwen Autopilot Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def console() -> FileResponse:
    """Serve the standalone, no-login Agent Console (demo surface)."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "qwen-autopilot-agent"}


def _run_pipeline(run_id: str) -> None:
    """Run intake -> draft -> quality in the background so the console can animate
    each step as it completes. Errors are recorded on the run for the UI to show."""
    try:
        orchestrator.start(run_id)
    except Exception as e:  # noqa: BLE001 — record on the run instead of crashing
        trace = list((store.get_run(run_id) or {}).get("trace") or [])
        trace.append({"step": "error", "detail": f"{type(e).__name__}: {e}"})
        store.update_run(run_id, status="error", trace=trace)


@app.post("/runs")
async def start_run(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    author_id: str = Form(...),
) -> dict:
    data = await file.read()
    key = f"manuscripts/{author_id}/{uuid.uuid4()}-{file.filename}"
    try:
        oss.upload_bytes(key, data, content_type=file.content_type)
        run = store.create_run(author_id=author_id, manuscript_uri=key)
    except Exception as e:  # upload/create failures still surface immediately
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
    # Kick off the pipeline in the background; return the run at 'intake' right away
    # so the UI can poll and animate the steps as they complete.
    background_tasks.add_task(_run_pipeline, run["id"])
    return run


@app.get("/runs")
def list_runs() -> list[dict]:
    return store.list_runs()


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    return run


class ResumeBody(BaseModel):
    decision: str  # 'approve' | 'reject'
    approved_listing: dict | None = None
    approved_email: dict | None = None


@app.post("/runs/{run_id}/resume")
def resume_run(run_id: str, body: ResumeBody) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run["status"] != store.AWAITING_APPROVAL:
        raise HTTPException(409, "run is not awaiting approval")
    try:
        return orchestrator.resume(run_id, body.decision, body.approved_listing, body.approved_email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
