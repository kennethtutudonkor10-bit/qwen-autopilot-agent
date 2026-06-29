"""Pipeline step executors: language work (pipeline) + IO (OSS, run store).

Shared by both the deterministic orchestrator (production path) and the
Qwen-Agent BaseTool skills (agentic surface), so the two never drift. Kept free
of any agent-framework import so the orchestrator stays lightweight.
"""
from __future__ import annotations

import os
from typing import Any

from . import db, pipeline, store
from .aliyun import oss

_FILE_TYPES = {".pdf": "PDF", ".docx": "DOCX", ".epub": "EPUB"}


def _file_type(uri: str | None) -> str:
    return _FILE_TYPES.get(os.path.splitext(uri or "")[1].lower(), "PDF")


def do_ingest(run_id: str) -> dict[str, Any]:
    run = store.get_run(run_id)
    data = oss.get_bytes(run["manuscript_uri"])
    extracted = pipeline.ingest_auto(data, run["manuscript_uri"])
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
    """Insert the approved listing into GHAMAZON's books table (status='approved')."""
    run = store.get_run(run_id)
    book_id = ""
    if db.is_configured():
        price = float(listing.get("suggested_price_ghs") or 0)
        row = {
            "title": listing.get("title") or "Untitled",
            "author_id": run.get("author_id"),
            "description": listing.get("synopsis") or listing.get("back_cover") or "",
            "price_ghs": price,
            "language": listing.get("language") or "English",
            "category": listing.get("category") or "General",
            "file_url": run.get("manuscript_uri"),  # OSS object key
            "file_type": _file_type(run.get("manuscript_uri")),
            "status": "approved",
            "is_free": price == 0,
        }
        book_id = db.client().table("books").insert(row).execute().data[0]["id"]
    store.update_run(run_id, status=store.PUBLISH, step=store.PUBLISH, book_id=book_id)
    store.append_trace(run_id, store.PUBLISH, {"book_id": book_id})
    return {"book_id": book_id, "listing": listing}
