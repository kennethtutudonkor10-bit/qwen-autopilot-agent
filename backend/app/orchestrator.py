"""Orchestrator: the durable, resumable publishing state machine.

The pipeline runs autonomously up to a human checkpoint, persists what the human
must approve, and returns. A later ``resume`` call rehydrates the run from the
store and continues — so checkpoints survive restarts and the Function Compute
request lifecycle.

    start(run)        intake -> draft -> quality -> [HITL #1: review_listing]
    resume(approve)   publish -> [HITL #2: approve_notification]
    resume(approve)   notify -> done

The deterministic state machine owns sequencing (production-readiness); each step
delegates the language work to Qwen via the registered skills / pipeline.
"""
from __future__ import annotations

from . import notify, pipeline, steps, store

# Human-in-the-loop checkpoint identifiers
CK_REVIEW_LISTING = "review_listing"
CK_APPROVE_NOTIFICATION = "approve_notification"


def start(run_id: str) -> dict:
    """Run intake -> draft -> quality, then pause at the listing-review checkpoint."""
    extracted = steps.do_ingest(run_id)
    steps.do_draft(run_id, extracted)
    steps.do_quality(run_id, extracted)

    run = store.get_run(run_id)
    return store.update_run(
        run_id,
        status=store.AWAITING_APPROVAL,
        step=store.QUALITY,
        pending_action={
            "checkpoint": CK_REVIEW_LISTING,
            "listing": run.get("draft_listing"),
            "flags": run.get("quality_flags"),
        },
    )


def resume(
    run_id: str,
    decision: str,
    approved_listing: dict | None = None,
    approved_email: dict | None = None,
) -> dict:
    """Continue a run after a human checkpoint. decision: 'approve' | 'reject'.

    The human may edit the listing (checkpoint 1) or the author email (checkpoint 2)
    before approving; the edited version is what's used.
    """
    run = store.get_run(run_id)
    if run is None:
        raise ValueError(f"run {run_id} not found")
    checkpoint = (run.get("pending_action") or {}).get("checkpoint")

    if decision == "reject":
        store.append_trace(run_id, store.REJECTED, {"checkpoint": checkpoint})
        return store.update_run(run_id, status=store.REJECTED, pending_action=None)

    if decision != "approve":
        raise ValueError(f"unknown decision: {decision}")

    if checkpoint == CK_REVIEW_LISTING:
        return _resume_after_listing(run_id, run, approved_listing)
    if checkpoint == CK_APPROVE_NOTIFICATION:
        return _resume_after_notification(run_id, run, approved_email)
    raise ValueError(f"cannot resume from checkpoint: {checkpoint}")


def _resume_after_listing(run_id: str, run: dict, approved_listing: dict | None) -> dict:
    """HITL #1 approved: publish the book, then pause for notification approval."""
    listing = approved_listing or run.get("draft_listing") or {}
    steps.do_publish(run_id, listing)

    email = pipeline.draft_author_email(listing)
    store.append_trace(run_id, store.PUBLISH, {"title": listing.get("title")})
    return store.update_run(
        run_id,
        status=store.AWAITING_APPROVAL,
        step=store.NOTIFY,
        pending_action={"checkpoint": CK_APPROVE_NOTIFICATION, "email": email},
    )


def _resume_after_notification(run_id: str, run: dict, approved_email: dict | None = None) -> dict:
    """HITL #2 approved: send the (possibly human-edited) author notification and finish."""
    email = approved_email or (run.get("pending_action") or {}).get("email") or {}
    sent = notify.send_author_notification(
        run.get("author_id"),
        email.get("subject", "Your book is live on GHAMAZON"),
        email.get("body", ""),
        book_id=run.get("book_id"),
    )
    store.append_trace(run_id, store.NOTIFY, {"subject": email.get("subject"), **sent})
    # Auto-advertise: generate an ad with Qwen and hand it to the posting bot (best-effort).
    steps.do_promote(run_id, run.get("draft_listing") or {}, run.get("book_id"))
    return store.update_run(run_id, status=store.DONE, step=store.DONE, pending_action=None)
