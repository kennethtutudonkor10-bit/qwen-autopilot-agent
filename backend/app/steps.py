"""Pipeline step executors: language work (pipeline) + IO (OSS, run store).

Shared by both the deterministic orchestrator (production path) and the
Qwen-Agent BaseTool skills (agentic surface), so the two never drift. Kept free
of any agent-framework import so the orchestrator stays lightweight.
"""
from __future__ import annotations

from typing import Any

from . import pipeline, store
from .aliyun import oss


def do_ingest(run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    data = oss.get_bytes(run["manuscript_uri"])
    text = pipeline.extract_text(data, run["manuscript_uri"])
    extracted = pipeline.ingest(text)
    store.update_run(run_id, status=store.DRAFT, step=store.DRAFT)
    store.append_trace(run_id, store.INTAKE, extracted)
    return extracted


def do_draft(run_id: str, extracted: dict[str, Any]) -> dict[str, Any]:
    listing = pipeline.draft_listing(extracted)
    store.update_run(run_id, status=store.DRAFT, step=store.DRAFT, draft_listing=listing)
    store.append_trace(run_id, store.DRAFT, listing)
    return listing


def do_quality(run_id: str, extracted: dict[str, Any]) -> list[dict[str, Any]]:
    run = store.get_run(run_id)
    flags = pipeline.quality_checks(run.get("draft_listing") or {}, extracted.get("excerpt", ""))
    store.update_run(run_id, status=store.QUALITY, step=store.QUALITY, quality_flags=flags)
    store.append_trace(run_id, store.QUALITY, flags)
    return flags


def do_publish(run_id: str, listing: dict[str, Any]) -> dict[str, Any]:
    # TODO(day5): insert into Supabase `books` (status='approved') + publish file to public bucket.
    book_id = ""
    store.update_run(run_id, status=store.PUBLISH, step=store.PUBLISH, book_id=book_id)
    store.append_trace(run_id, store.PUBLISH, {"book_id": book_id})
    return {"book_id": book_id, "listing": listing}
