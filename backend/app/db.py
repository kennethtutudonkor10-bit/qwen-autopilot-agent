"""Shared Supabase (GHAMAZON Postgres) client.

Used for the book/user/notification tables that always live in Supabase. Agent
run-state goes through ``app.store`` (which falls back to in-memory when Supabase
is unconfigured). Import of the supabase SDK is lazy so non-DB paths and tests
need no dependency.
"""
from __future__ import annotations

from functools import lru_cache

from .config import get_settings


def is_configured() -> bool:
    s = get_settings()
    return bool(s.supabase_url and s.supabase_service_role_key)


@lru_cache
def client():
    from supabase import create_client

    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)
