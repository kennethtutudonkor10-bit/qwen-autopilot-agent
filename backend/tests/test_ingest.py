"""Routing tests: text extraction vs. Qwen-VL fallback for scanned PDFs."""
from __future__ import annotations

from app import pipeline


def _stub(monkeypatch, text):
    monkeypatch.setattr(pipeline, "extract_text", lambda d, n: text)
    monkeypatch.setattr(pipeline, "ingest", lambda t: {"source": "text"})
    monkeypatch.setattr(pipeline, "ingest_from_images", lambda d, n: {"source": "vision"})


def test_text_pdf_uses_text_path(monkeypatch):
    _stub(monkeypatch, "x" * 500)
    assert pipeline.ingest_auto(b"...", "book.pdf")["source"] == "text"


def test_scanned_pdf_uses_vision_path(monkeypatch):
    _stub(monkeypatch, "   ")  # almost no extractable text
    assert pipeline.ingest_auto(b"...", "scan.pdf")["source"] == "vision"


def test_non_pdf_never_uses_vision(monkeypatch):
    _stub(monkeypatch, "")  # even empty text
    assert pipeline.ingest_auto(b"...", "notes.txt")["source"] == "text"


def test_is_scanned_threshold():
    assert pipeline.is_scanned("   \n  ")
    assert not pipeline.is_scanned("a" * 300)
