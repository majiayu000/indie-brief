from __future__ import annotations

import json

import httpx

from indie_brief.errors import BriefError


def fetch_today(
    focus: str,
    *,
    url: str,
    api_key: str,
    timeout: float = 20.0,
    transport: httpx.BaseTransport | None = None,
) -> str:
    if not api_key:
        raise BriefError("NO_KEYS", "没有设置 INDIE_BRIEF_API_KEY")
    if not url:
        raise BriefError("NO_URL", "没有设置 INDIE_BRIEF_API_URL")
    endpoint = url.rstrip("/") + "/v1/today"
    params = {"focus": focus} if focus else None
    try:
        with httpx.Client(transport=transport, timeout=timeout) as client:
            response = client.get(
                endpoint,
                params=params,
                headers={"Authorization": f"Bearer {api_key}"},
            )
    except httpx.HTTPError as exc:
        raise BriefError("CONNECTION", f"连不上简报接口 {endpoint}: {exc}") from exc
    if response.status_code != 200:
        raise BriefError(
            "API_ERROR",
            f"简报接口返回 {response.status_code}: {_error_message(response)}",
        )
    return response.text


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        text = response.text.strip()
        return text or "空响应"
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message
        detail = payload.get("detail")
        if isinstance(detail, dict):
            nested = detail.get("message")
            if isinstance(nested, str) and nested.strip():
                return nested
    return "空响应"
