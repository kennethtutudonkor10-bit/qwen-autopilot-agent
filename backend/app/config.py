"""Runtime configuration for the Qwen Autopilot Agent.

All secrets come from the environment. On Alibaba Cloud Function Compute these
are set as function environment variables; locally they come from `.env`.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Qwen via DashScope (Alibaba Cloud Model Studio) ──────────────────────
    # OpenAI-compatible endpoint. Pick the region you deployed in:
    #   Singapore    https://dashscope-intl.aliyuncs.com/compatible-mode/v1
    #   Beijing (CN) https://dashscope.aliyuncs.com/compatible-mode/v1
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    # Model routing — one job per model.
    model_reason: str = "qwen-plus"          # planning / reasoning
    model_structured: str = "qwen3-coder-plus"  # strict JSON listing output
    model_vision: str = "qwen-vl-plus"       # read manuscript pages / covers

    # ── Alibaba Cloud OSS (manuscripts + generated covers) ───────────────────
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_endpoint: str = "https://oss-ap-southeast-1.aliyuncs.com"
    oss_bucket: str = "ghamazon-manuscripts"

    # ── Supabase (book/user data + agent run-state) ──────────────────────────
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # ── Email (Resend) — author notifications ────────────────────────────────
    resend_api_key: str = ""
    resend_from: str = "GHAMAZON <noreply@ghamazon.com>"

    # ── App ──────────────────────────────────────────────────────────────────
    app_url: str = "https://ghamazon.pages.dev"
    cors_origins: str = "http://localhost:5173,https://ghamazon.pages.dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()
