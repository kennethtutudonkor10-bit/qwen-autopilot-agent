"""Thin client for Qwen models on Alibaba Cloud Model Studio (DashScope).

Uses the OpenAI-compatible endpoint, so the official ``openai`` SDK talks to Qwen
directly. Two helpers cover everything the pipeline needs: a strict-JSON
completion (for structured listings / flags) and a plain-text completion.
"""
from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .config import get_settings


def get_client() -> OpenAI:
    s = get_settings()
    return OpenAI(api_key=s.dashscope_api_key, base_url=s.dashscope_base_url)


def complete_json(
    model: str,
    system: str,
    user: str,
    *,
    temperature: float = 0.2,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Return parsed JSON from the model, retrying if it emits non-JSON.

    The system prompt must instruct the model to respond in JSON (DashScope's
    json_object mode requires the word "json" to appear in the conversation).
    """
    client = get_client()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    last = ""
    for _ in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        last = resp.choices[0].message.content or ""
        try:
            return json.loads(last)
        except json.JSONDecodeError:
            messages.append({"role": "assistant", "content": last})
            messages.append({"role": "user", "content": "Respond with ONLY valid JSON."})
    raise ValueError(f"Model did not return valid JSON. Last output: {last[:300]}")


def complete_text(model: str, system: str, user: str, *, temperature: float = 0.3) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return (resp.choices[0].message.content or "").strip()
