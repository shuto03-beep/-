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
FALLBACK_ENVS = ("PLAUD_DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOK_URL")
_DISCORD_LIMIT = 1900


def post(text: str, *, prefix: str = "") -> bool:
    url = os.environ.get(WEBHOOK_ENV)
    if not url:
        for env in FALLBACK_ENVS:
            url = os.environ.get(env)
            if url:
                break
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
            headers={
                "Content-Type": "application/json",
                # Discord は Python のデフォルト UA (Python-urllib/...) を
                # bot 風 UA とみなして 403 を返すため、明示的に設定する。
                "User-Agent": "life_v2-notifier/2.0 (+https://github.com/shuto03-beep/-)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 300:
                    print(f"[notifier] HTTP {resp.status}")
                    return False
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", errors="replace")[:200]
            except Exception:
                detail = ""
            print(f"[notifier] HTTP {e.code} {e.reason}: {detail}")
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
