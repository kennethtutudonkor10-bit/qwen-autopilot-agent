"""Durable agent run-state.

Persists to Supabase when configured; otherwise falls back to an in-memory store
so the pipeline and the human-in-the-loop state machine can be run and tested
without any infrastructure (just a DashScope key, or fully stubbed in tests).

The run is the unit of work. It survives process restarts and the Function
Compute request lifecycle, which is what makes the human-in-the-loop checkpoints
resumable: the agent writes its proposed action and returns; a human approves
later; we rehydrate and continue.
"""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from . import db
from .config import get_settings

# Pipeline states — see docs/architecture.md
INTAKE = "intake"
DRAFT = "draft"
QUALITY = "quality"
AWAITING_APPROVAL = "awaiting_approval"
PUBLISH = "publish"
NOTIFY = "notify"
DONE = "done"
REJECTED = "rejected"

_MEM: dict[str, dict[str, Any]] = {}


def _use_supabase() -> bool:
    # Read settings directly (not db.is_configured) so the run-store's backend
    # choice is independent of the books/notifications client — important for tests.
    s = get_settings()
    return bool(s.supabase_url and s.supabase_service_role_key)


def _supabase():
    return db.client()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── public API ────────────────────────────────────────────────────────────────
def create_run(author_id: str, manuscript_uri: str) -> dict[str, Any]:
    row = {
        "status": INTAKE,
        "step": INTAKE,
        "author_id": author_id,
        "manuscript_uri": manuscript_uri,
        "trace": [],
    }
    if _use_supabase():
        return _supabase().table("agent_runs").insert(row).execute().data[0]
    row = {**row, "id": str(uuid.uuid4()), "created_at": _now(), "updated_at": _now()}
    _MEM[row["id"]] = row
    return copy.deepcopy(row)


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    if _use_supabase():
        res = (
            _supabase().table("agent_runs").select("*")
            .order("created_at", desc=True).limit(limit).execute()
        )
        return res.data or []
    runs = sorted(_MEM.values(), key=lambda r: r["created_at"], reverse=True)
    return [copy.deepcopy(r) for r in runs[:limit]]


def get_run(run_id: str) -> dict[str, Any] | None:
    if _use_supabase():
        res = _supabase().table("agent_runs").select("*").eq("id", run_id).execute()
        return res.data[0] if res.data else None
    row = _MEM.get(run_id)
    return copy.deepcopy(row) if row else None


def update_run(run_id: str, **fields: Any) -> dict[str, Any]:
    if _use_supabase():
        return _supabase().table("agent_runs").update(fields).eq("id", run_id).execute().data[0]
    _MEM[run_id].update(fields)
    _MEM[run_id]["updated_at"] = _now()
    return copy.deepcopy(_MEM[run_id])


def append_trace(run_id: str, step: str, detail: Any) -> None:
    """Append a reasoning step so the dashboard can visualize the agent's logic."""
    run = get_run(run_id) or {"trace": []}
    trace = list(run.get("trace") or [])
    trace.append({"step": step, "detail": detail, "at": _now()})
    update_run(run_id, trace=trace)
