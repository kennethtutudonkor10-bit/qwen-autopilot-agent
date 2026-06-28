"""Alibaba Cloud Object Storage Service (OSS) integration.

This module is the concrete proof that the backend uses Alibaba Cloud services
and APIs (a hackathon submission requirement). Uploaded manuscripts and
agent-generated covers are stored in an OSS bucket; the agent works off the
returned object keys / signed URLs.

Docs: https://www.alibabacloud.com/help/en/oss/developer-reference/python
"""
from __future__ import annotations

import oss2

from ..config import get_settings


def _bucket() -> oss2.Bucket:
    s = get_settings()
    auth = oss2.Auth(s.oss_access_key_id, s.oss_access_key_secret)
    return oss2.Bucket(auth, s.oss_endpoint, s.oss_bucket)


def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> str:
    """Store an object in OSS and return its key."""
    headers = {"Content-Type": content_type} if content_type else None
    _bucket().put_object(key, data, headers=headers)
    return key


def signed_url(key: str, expires_seconds: int = 3600) -> str:
    """Return a time-limited signed URL the model / client can read."""
    return _bucket().sign_url("GET", key, expires_seconds)


def get_bytes(key: str) -> bytes:
    return _bucket().get_object(key).read()
