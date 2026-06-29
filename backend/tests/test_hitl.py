"""HITL state-machine tests — no network, no Supabase/OSS.

Stubs the Qwen-backed pipeline functions and OSS read, runs against the in-memory
store, and asserts the two human-in-the-loop checkpoints behave correctly.

    cd backend && pip install -r requirements.txt pytest && pytest
"""
from __future__ import annotations

import pytest

from app import db, orchestrator, pipeline, store
from app.aliyun import oss

LISTING = {"title": "The Harmattan Letters", "category": "Fiction", "suggested_price_ghs": 25}


@pytest.fixture(autouse=True)
def stub_qwen_and_oss(monkeypatch):
    monkeypatch.setattr(oss, "get_bytes", lambda key: b"manuscript text")
    monkeypatch.setattr(pipeline, "ingest_auto", lambda data, name: {"excerpt": "x", "language": "English"})
    monkeypatch.setattr(pipeline, "draft_listing", lambda extracted: dict(LISTING))
    monkeypatch.setattr(pipeline, "quality_checks", lambda listing, excerpt: [])
    monkeypatch.setattr(
        pipeline, "draft_author_email",
        lambda listing: {"subject": "Your book is live", "body": "Congrats!"},
    )


def _new_run() -> str:
    return store.create_run(author_id="author-1", manuscript_uri="manuscripts/x.txt")["id"]


def test_happy_path_two_checkpoints():
    run_id = _new_run()

    # Autonomous phase pauses at checkpoint #1
    run = orchestrator.start(run_id)
    assert run["status"] == store.AWAITING_APPROVAL
    assert run["pending_action"]["checkpoint"] == orchestrator.CK_REVIEW_LISTING
    assert run["draft_listing"]["title"] == LISTING["title"]

    # Approve listing -> publishes, pauses at checkpoint #2 with a drafted email
    run = orchestrator.resume(run_id, "approve")
    assert run["status"] == store.AWAITING_APPROVAL
    assert run["pending_action"]["checkpoint"] == orchestrator.CK_APPROVE_NOTIFICATION
    assert run["pending_action"]["email"]["subject"] == "Your book is live"

    # Approve notification -> done
    run = orchestrator.resume(run_id, "approve")
    assert run["status"] == store.DONE
    assert run["pending_action"] is None


def test_admin_edits_listing_before_publish():
    run_id = _new_run()
    orchestrator.start(run_id)
    edited = {**LISTING, "suggested_price_ghs": 40}
    run = orchestrator.resume(run_id, "approve", approved_listing=edited)
    assert run["status"] == store.AWAITING_APPROVAL
    assert run["pending_action"]["checkpoint"] == orchestrator.CK_APPROVE_NOTIFICATION


def test_reject_at_first_checkpoint():
    run_id = _new_run()
    orchestrator.start(run_id)
    run = orchestrator.resume(run_id, "reject")
    assert run["status"] == store.REJECTED
    assert run["pending_action"] is None


def test_resume_with_unknown_decision_raises():
    run_id = _new_run()
    orchestrator.start(run_id)
    with pytest.raises(ValueError):
        orchestrator.resume(run_id, "maybe")


def test_publish_inserts_book_row(monkeypatch):
    """When Supabase is configured, approving the listing inserts an approved book."""
    captured: dict = {}

    class FakeTable:
        def __init__(self, name):
            captured["table"] = name

        def insert(self, row):
            captured["row"] = row
            return self

        def select(self, *_):
            return self

        def eq(self, *_):
            return self

        def execute(self):
            return type("R", (), {"data": [{"id": "book-123", "email": "a@b.com"}]})()

    monkeypatch.setattr(db, "is_configured", lambda: True)
    monkeypatch.setattr(db, "client", lambda: type("C", (), {"table": lambda self, n: FakeTable(n)})())

    run_id = _new_run()
    orchestrator.start(run_id)
    run = orchestrator.resume(run_id, "approve")  # approve listing -> publish

    assert captured["table"] == "books"
    assert captured["row"]["status"] == "approved"
    assert captured["row"]["author_id"] == "author-1"
    assert run["book_id"] == "book-123"
    assert run["pending_action"]["checkpoint"] == orchestrator.CK_APPROVE_NOTIFICATION
