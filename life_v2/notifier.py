"""Discord webhook への投稿。

Plaud V1 の notifier を踏襲しつつ、life_v2 の coach/morning/evening 専用の
整形を提供する。webhook 未設定時はコンソール出力のみで終わる（エラーにしない）。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

WEBHOOK_ENV = "LIFE_V2_DISCORD_WEBHOOK_URL"
FALLBACK_ENV = "PLAUD_DISCORD_WEBHOOK_URL"
_DISCORD_LIMIT = 1900


def post(text: str, *, prefix: str = "") -> bool:
    url = os.environ.get(WEBHOOK_ENV) or os.environ.get(FALLBACK_ENV)
    if not url:
        print("[notifier] webhook 未設定。コンソールに出力します:")
        print(f"{prefix}\n{text}")
        return False
    body = f"{prefix}\n{text}" if prefix else text
    chunks = _split(body)
    for chunk in chunks:
        payload = json.dumps({"content": chunk}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 300:
                    print(f"[notifier] HTTP {resp.status}")
                    return False
        except urllib.error.URLError as e:
            print(f"[notifier] error: {e}")
            return False
    return True


def _split(text: str, limit: int = _DISCORD_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    rest = text
    while rest:
        chunks.append(rest[:limit])
        rest = rest[limit:]
    return chunks
