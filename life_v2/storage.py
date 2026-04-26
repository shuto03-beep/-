"""life_v2 のストレージ層と Plaud V1 連携ヘルパ。"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import (
    DISTILL_FILE,
    PLAUD_ENTRIES_DIR,
    PLAUD_TASKS_FILE,
    TRIAGE_DIR,
    ensure_dirs,
)
from .models import CoachOutput


def save_coach_output(output: CoachOutput) -> Path:
    ensure_dirs()
    path = TRIAGE_DIR / f"{output.date}_coach.json"
    path.write_text(
        json.dumps(output.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def save_aesthetic(payload: dict) -> Path:
    ensure_dirs()
    DISTILL_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return DISTILL_FILE


def load_aesthetic() -> dict | None:
    if not DISTILL_FILE.exists():
        return None
    return json.loads(DISTILL_FILE.read_text(encoding="utf-8"))


# ---------- Plaud V1 連携 ----------

def load_plaud_entry(entry_id: str) -> dict | None:
    path = PLAUD_ENTRIES_DIR / f"{entry_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def plaud_entry_to_text(entry: dict) -> str:
    """Plaud entry JSON から coach に投入するテキストを組み立てる。"""
    parts = []
    title = entry.get("title")
    if title:
        parts.append(f"# {title}")
    lifelog = entry.get("lifelog") or {}
    if lifelog.get("headline"):
        parts.append(f"見出し: {lifelog['headline']}")
    if lifelog.get("narrative"):
        parts.append(lifelog["narrative"])
    key_points = lifelog.get("key_points") or []
    if key_points:
        parts.append("## 重要ポイント")
        parts.extend(f"- {kp}" for kp in key_points)
    raw = entry.get("raw") or {}
    if raw.get("summary"):
        parts.append("## 要約")
        parts.append(raw["summary"])
    if raw.get("transcript"):
        parts.append("## 文字起こし")
        parts.append(raw["transcript"])
    tasks = entry.get("tasks") or []
    if tasks:
        parts.append("## 既存タスク（参考）")
        for t in tasks:
            parts.append(f"- {t.get('title','')}")
    return "\n\n".join(parts)


def load_open_plaud_tasks(limit: int = 80) -> list[dict]:
    """Plaud V1 の tasks.json から open のものを返す。"""
    if not PLAUD_TASKS_FILE.exists():
        return []
    raw = json.loads(PLAUD_TASKS_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    open_tasks = [t for t in raw if t.get("status") != "done"]
    return open_tasks[:limit]


def collect_recent_plaud_text(days: int = 1) -> str:
    """直近 N 日の Plaud entries をまとめて1テキストにする。"""
    if not PLAUD_ENTRIES_DIR.exists():
        return ""
    cutoff = date.today() - timedelta(days=days)
    parts: list[str] = []
    for path in sorted(PLAUD_ENTRIES_DIR.glob("*.json")):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        recorded = entry.get("recorded_at", "")
        try:
            d = datetime.fromisoformat(recorded.replace("Z", "+00:00")).date()
        except ValueError:
            continue
        if d < cutoff:
            continue
        parts.append(plaud_entry_to_text(entry))
    return "\n\n---\n\n".join(parts)
