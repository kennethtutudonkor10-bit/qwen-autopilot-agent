"""Pure publishing-pipeline logic — no Supabase/OSS IO.

These functions take plain inputs and return plain dicts, so they are testable
and runnable from the CLI dry-run with only a DashScope key. The Qwen-Agent
skills (skills/manuscript.py) wrap these with run-state and OSS IO.
"""
from __future__ import annotations

import base64
import io
from typing import Any

from . import qwen
from .config import get_settings

EXCERPT_CHARS = 6000   # how much manuscript text we feed the model
MIN_TEXT_CHARS = 200   # below this, a PDF is treated as scanned -> use vision
VISION_MAX_PAGES = 4   # pages rendered for the VL model


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
def is_scanned(text: str) -> bool:
    """A PDF that yields almost no extractable text is image-based (scanned)."""
    return len(text.strip()) < MIN_TEXT_CHARS


def ingest_auto(data: bytes, filename: str) -> dict[str, Any]:
    """Entry point: extract text, falling back to Qwen-VL for scanned PDFs."""
    text = extract_text(data, filename)
    if filename.lower().endswith(".pdf") and is_scanned(text):
        return ingest_from_images(data, filename)
    return ingest(text)


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
    result["source"] = "text"
    return result


def _render_pdf_images(data: bytes, max_pages: int = VISION_MAX_PAGES) -> list[str]:
    """Render the first pages of a PDF to PNG data: URLs (via PyMuPDF, no native binaries)."""
    import fitz  # PyMuPDF

    urls: list[str] = []
    with fitz.open(stream=data, filetype="pdf") as doc:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            png = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)).tobytes("png")
            urls.append("data:image/png;base64," + base64.b64encode(png).decode())
    return urls


def ingest_from_images(data: bytes, filename: str) -> dict[str, Any]:
    """Read a scanned/image manuscript with Qwen-VL."""
    s = get_settings()
    urls = _render_pdf_images(data)
    if not urls:
        return {"detected_title": None, "language": None, "excerpt": "",
                "char_count": 0, "source": "vision", "note": "no renderable pages"}
    system = (
        "You are a publishing analyst reading scanned manuscript pages. "
        "Return JSON only; never invent content you cannot see."
    )
    user = (
        "From these manuscript page images, return JSON with keys: "
        "detected_title (string|null), language, genre (string|null), "
        "themes (string[]), tone (string), one_line_premise (string), "
        "transcribed_excerpt (the readable text from the pages)."
    )
    result = qwen.complete_json_vision(s.model_vision, system, user, urls)
    result["excerpt"] = result.get("transcribed_excerpt", "") or ""
    result["char_count"] = len(result["excerpt"])
    result["source"] = "vision"
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


# ── step 5: draft the author notification (for the 2nd human checkpoint) ──────
def draft_author_email(listing: dict[str, Any]) -> dict[str, str]:
    """Draft the 'your book is live' email an admin approves before it's sent."""
    s = get_settings()
    system = (
        "You write warm, professional emails for GHAMAZON to its authors. "
        "Return JSON only."
    )
    user = (
        "An author's book has just been approved and published on GHAMAZON. "
        "Return JSON with keys: subject (string), body (string, 80-130 words, "
        "congratulatory, mentions the title, invites them to share their store "
        "link, signed 'The GHAMAZON Team'). Use the listing below.\n\n"
        f"LISTING:\n{listing}"
    )
    return qwen.complete_json(s.model_reason, system, user)
