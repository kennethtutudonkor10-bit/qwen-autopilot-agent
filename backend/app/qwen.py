"""Thin client for Qwen models on Alibaba Cloud Model Studio (DashScope).

Uses the OpenAI-compatible endpoint, so the official ``openai`` SDK talks to Qwen
directly. Two helpers cover everything the pipeline needs: a strict-JSON
completion (for structured listings / flags) and a plain-text completion.
"""
from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from .config import get_settings


def _parse_json_lenient(raw: str) -> dict[str, Any]:
    """Parse JSON, tolerating prose/markdown fences around it (VL models often add some)."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"No JSON found in model output: {raw[:300]}")


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


def complete_json_vision(
    model: str,
    system: str,
    user: str,
    image_urls: list[str],
    *,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """JSON completion over one or more images (data: URLs or http URLs).

    Used for scanned/image manuscripts via a Qwen-VL model. VL models don't
    reliably support json_object mode, so we parse leniently.
    """
    client = get_client()
    content: list[dict[str, Any]] = [{"type": "text", "text": user}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        temperature=temperature,
    )
    return _parse_json_lenient(resp.choices[0].message.content or "")


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
