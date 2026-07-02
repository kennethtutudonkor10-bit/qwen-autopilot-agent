"""Alibaba Cloud Object Storage Service (OSS) integration.

This module is the concrete proof that the backend uses Alibaba Cloud services
and APIs (a hackathon submission requirement). Uploaded manuscripts and
agent-generated covers are stored in an OSS bucket; the agent works off the
returned object keys / signed URLs.

When OSS is not configured (e.g. a quick demo deploy with only a Qwen key), it
transparently falls back to an in-process store so the whole pipeline still runs
on a single-instance server. Configure OSS for durable, multi-instance storage.

Docs: https://www.alibabacloud.com/help/en/oss/developer-reference/python
"""
from __future__ import annotations

from ..config import get_settings

# In-process fallback used only when OSS credentials aren't set.
_LOCAL: dict[str, bytes] = {}


def is_configured() -> bool:
    s = get_settings()
    return bool(s.oss_access_key_id and s.oss_access_key_secret)


def _bucket():
    import oss2  # imported lazily so non-OSS code paths / tests need no native deps

    s = get_settings()
    auth = oss2.Auth(s.oss_access_key_id, s.oss_access_key_secret)
    return oss2.Bucket(auth, s.oss_endpoint, s.oss_bucket)


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> str:
    """Store an object (OSS if configured, else in-process) and return its key."""
    if not is_configured():
        _LOCAL[key] = data
        return key
    headers = {"Content-Type": content_type} if content_type else None
    _bucket().put_object(key, data, headers=headers)
    return key


def get_bytes(key: str) -> bytes:
    if not is_configured():
        return _LOCAL[key]
    return _bucket().get_object(key).read()


def signed_url(key: str, expires_seconds: int = 3600) -> str:
    """Return a time-limited signed URL the model / client can read."""
    if not is_configured():
        return f"local://{key}"
    return _bucket().sign_url("GET", key, expires_seconds)
