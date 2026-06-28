"""Author notification: in-app (Supabase notifications) + email (Resend).

Both channels fail soft — a delivery problem must not crash a run that has
already published a book. Returns what actually happened so the orchestrator can
record it in the run trace.
"""
from __future__ import annotations

from typing import Any

from . import db
from .config import get_settings

RESEND_ENDPOINT = "https://api.resend.com/emails"


def send_author_notification(
    author_id: str,
    subject: str,
    body: str,
    *,
    book_id: str | None = None,
) -> dict[str, Any]:
    s = get_settings()
    link = f"{s.app_url}/book/{book_id}" if book_id else None
    result = {"notified_in_app": False, "emailed": False}

    if not db.is_configured():
        return result

    # ── in-app notification ──
    try:
        db.client().table("notifications").insert(
            {"user_id": author_id, "title": subject, "body": body,
             "type": "success", "link": link}
        ).execute()
        result["notified_in_app"] = True
    except Exception:  # noqa: BLE001 — fail soft
        pass

    # ── email via Resend ──
    if s.resend_api_key:
        try:
            res = db.client().table("users").select("email").eq("id", author_id).execute()
            to = res.data[0]["email"] if res.data else None
            if to:
                result["emailed"] = _send_email(to, subject, body, link, s)
        except Exception:  # noqa: BLE001 — fail soft
            pass

    return result


def _send_email(to: str, subject: str, body: str, link: str | None, s) -> bool:
    import httpx  # bundled with the supabase SDK

    html = f"<p>{body}</p>"
    if link:
        html += f'<p><a href="{link}">View your book on GHAMAZON</a></p>'
    resp = httpx.post(
        RESEND_ENDPOINT,
        headers={"Authorization": f"Bearer {s.resend_api_key}",
                 "Content-Type": "application/json"},
        json={"from": s.resend_from, "to": to, "subject": subject, "html": html},
        timeout=15,
    )
    return resp.status_code < 300
