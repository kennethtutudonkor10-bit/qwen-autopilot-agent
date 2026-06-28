"""Pure publishing-pipeline logic — no Supabase/OSS IO.

These functions take plain inputs and return plain dicts, so they are testable
and runnable from the CLI dry-run with only a DashScope key. The Qwen-Agent
skills (skills/manuscript.py) wrap these with run-state and OSS IO.
"""
from __future__ import annotations

import io
from typing import Any

from . import qwen
from .config import get_settings

EXCERPT_CHARS = 6000  # how much manuscript text we feed the model


# ── text extraction ──────────────────────────────────────────────────────────
def extract_text(data: bytes, filename: str) -> str:
    """Extract plain text from an uploaded manuscript (PDF or text/markdown)."""
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    # .txt / .md / .epub-as-text fallback
    return data.decode("utf-8", errors="replace")


# ── step 1: ingest ───────────────────────────────────────────────────────────
def ingest(text: str) -> dict[str, Any]:
    """Detect basic structure from raw manuscript text."""
    s = get_settings()
    excerpt = text[:EXCERPT_CHARS]
    system = (
        "You are a publishing analyst. Read a manuscript excerpt and return JSON "
        "describing it. Never invent content; if unknown, use null."
    )
    user = (
        "From this manuscript excerpt, return JSON with keys: "
        "detected_title (string|null), language (e.g. 'English', 'Twi'), "
        "genre (string|null), themes (string[]), tone (string), "
        "one_line_premise (string).\n\n"
        f"EXCERPT:\n{excerpt}"
    )
    result = qwen.complete_json(s.model_reason, system, user)
    result["char_count"] = len(text)
    result["excerpt"] = excerpt
    return result


# ── step 2: draft the store listing ──────────────────────────────────────────
def draft_listing(extracted: dict[str, Any]) -> dict[str, Any]:
    """Produce a complete GHAMAZON store listing from the ingest result."""
    s = get_settings()
    system = (
        "You are GHAMAZON's listings editor for a Ghanaian book marketplace. "
        "Write a compelling, accurate store listing as JSON. Do not fabricate plot "
        "details beyond what the premise/themes support. Prices are in Ghana Cedis (GHS)."
    )
    user = (
        "Using this analysis, return JSON with keys: title (string), "
        "synopsis (120-180 words), back_cover (60-90 words, punchy), "
        "category (one of: Fiction, Non-Fiction, Education, Religion & Theology, "
        "Children, Poetry, Business, History), language (string), "
        "keywords (string[], 5-8 items), suggested_price_ghs (number, 0 means free).\n\n"
        f"ANALYSIS:\n{extracted}"
    )
    return qwen.complete_json(s.model_structured, system, user)


# ── step 3: quality + appropriateness checks ─────────────────────────────────
def quality_checks(listing: dict[str, Any], excerpt: str) -> list[dict[str, Any]]:
    """Return reviewer flags. Empty list == clean."""
    s = get_settings()
    system = (
        "You are a content-safety and quality reviewer for a book marketplace. "
        "Flag only real concerns. Return JSON."
    )
    user = (
        "Review this listing and manuscript excerpt. Return JSON with a single key "
        "'flags', an array of objects {code, severity, note}. Valid codes: "
        "low_quality, inappropriate, hate_or_violence, possible_plagiarism, "
        "metadata_mismatch, incomplete. severity is 'info' | 'warn' | 'block'. "
        "If nothing is wrong, return {\"flags\": []}.\n\n"
        f"LISTING:\n{listing}\n\nEXCERPT:\n{excerpt[:3000]}"
    )
    result = qwen.complete_json(s.model_reason, system, user)
    return result.get("flags", [])
