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
from .config import get_settings

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
        cover = _attach_cover(book_id, listing)
        store.append_trace(run_id, "cover", {"cover_url": cover or "skipped"})
    store.update_run(run_id, status=store.PUBLISH, step=store.PUBLISH, book_id=book_id)
    store.append_trace(run_id, store.PUBLISH, {"book_id": book_id})
    return {"book_id": book_id, "listing": listing}


def do_promote(run_id: str, listing: dict[str, Any], book_id: str | None) -> dict | None:
    """Generate a social-media ad with Qwen and hand it to the posting bot.

    Fully best-effort: skipped if no PROMO_WEBHOOK_URL is set, and any failure
    (generation or POST) is swallowed so it never affects the published book.
    """
    s = get_settings()
    if not s.promo_webhook_url:
        return None
    try:
        ad = pipeline.generate_ad(listing)
        cover_url = None
        if book_id and db.is_configured():
            try:
                res = db.client().table("books").select("cover_url").eq("id", book_id).execute()
                cover_url = (res.data or [{}])[0].get("cover_url")
            except Exception:  # noqa: BLE001
                pass
        payload = {
            "book_id": book_id,
            "title": listing.get("title"),
            "buy_url": f"{s.app_url}/book/{book_id}" if book_id else s.app_url,
            "cover_url": cover_url,
            "ad": ad,  # hook, script, youtube_title, description, hashtags
        }
        import httpx

        headers = {"X-Promo-Secret": s.promo_shared_secret} if s.promo_shared_secret else {}
        httpx.post(s.promo_webhook_url, json=payload, headers=headers, timeout=20)
        store.append_trace(run_id, "promote", {"youtube_title": ad.get("youtube_title"), "sent": True})
        return ad
    except Exception:  # noqa: BLE001 — advertising is best-effort
        store.append_trace(run_id, "promote", {"sent": False})
        return None


def _attach_cover(book_id: str, listing: dict[str, Any]) -> str | None:
    """Generate a cover with Qwen, upload it to the book-covers bucket, set cover_url.

    Entirely best-effort — any failure leaves the book cover-less and the run intact.
    """
    try:
        img = pipeline.generate_cover(listing)
        if not img:
            return None
        path = f"covers/{book_id}.png"
        sb = db.client()
        sb.storage.from_("book-covers").upload(
            path, img, {"content-type": "image/png", "upsert": "true"}
        )
        url = sb.storage.from_("book-covers").get_public_url(path)
        sb.table("books").update({"cover_url": url}).eq("id", book_id).execute()
        return url
    except Exception:  # noqa: BLE001 — cover art must never break publishing
        return None
