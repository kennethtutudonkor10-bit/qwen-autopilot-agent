"""Durable agent run-state, persisted in Supabase.

The run is the unit of work. It survives process restarts and the Function
Compute request lifecycle, which is what makes the human-in-the-loop
checkpoints resumable: the agent writes its proposed action and returns; a human
approves later; we rehydrate and continue.
"""
from __future__ import annotations

from typing import Any

from supabase import Client, create_client

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


def _client() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


def create_run(author_id: str, manuscript_uri: str) -> dict[str, Any]:
    res = (
        _client()
        .table("agent_runs")
        .insert(
            {
                "status": INTAKE,
                "step": INTAKE,
                "manuscript_uri": manuscript_uri,
                "trace": [],
            }
        )
        .execute()
    )
    return res.data[0]


def get_run(run_id: str) -> dict[str, Any] | None:
    res = _client().table("agent_runs").select("*").eq("id", run_id).execute()
    return res.data[0] if res.data else None


def update_run(run_id: str, **fields: Any) -> dict[str, Any]:
    res = _client().table("agent_runs").update(fields).eq("id", run_id).execute()
    return res.data[0]


def append_trace(run_id: str, step: str, detail: Any) -> None:
    """Append a reasoning step so the dashboard can visualize the agent's logic."""
    run = get_run(run_id) or {"trace": []}
    trace = list(run.get("trace") or [])
    trace.append({"step": step, "detail": detail})
    update_run(run_id, trace=trace)
