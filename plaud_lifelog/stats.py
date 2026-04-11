"""蓄積したライフログを俯瞰する集計ロジック。"""
from pathlib import Path
from typing import Any

from .config import ENTRIES_DIR
from .storage import _load_json  # type: ignore[attr-defined]


def compute_stats() -> dict[str, Any]:
    """data/plaud/entries/ 配下を走査して各種統計を返す。"""
    entries = _load_all_entries()
    if not entries:
        return {
            "entry_count": 0,
            "tasks": {"total": 0, "done": 0, "open": 0, "completion_rate": 0.0},
            "top_tags": [],
            "top_categories": [],
            "moods": {},
            "monthly": {},
            "priority_breakdown": {"high": 0, "medium": 0, "low": 0},
            "span": None,
        }

    task_total = 0
    task_done = 0
    tag_counter: dict[str, int] = {}
    category_counter: dict[str, int] = {}
    mood_counter: dict[str, int] = {}
    monthly: dict[str, dict[str, int]] = {}
    priority_counter: dict[str, int] = {"high": 0, "medium": 0, "low": 0}

    dates: list[str] = []
    for e in entries:
        lifelog = e.get("lifelog") or {}
        rec = (e.get("recorded_at") or "")[:10]
        if rec:
            dates.append(rec)
        month = rec[:7] if len(rec) >= 7 else "unknown"
        m = monthly.setdefault(month, {"entries": 0, "tasks": 0, "done": 0})
        m["entries"] += 1

        for tag in lifelog.get("tags") or []:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
        mood = lifelog.get("mood") or ""
        if mood:
            mood_counter[mood] = mood_counter.get(mood, 0) + 1

        for t in e.get("tasks") or []:
            task_total += 1
            m["tasks"] += 1
            if t.get("status") == "done":
                task_done += 1
                m["done"] += 1
            pri = t.get("priority", "medium")
            priority_counter[pri] = priority_counter.get(pri, 0) + 1
            cat = t.get("category") or "(未分類)"
            category_counter[cat] = category_counter.get(cat, 0) + 1

    completion_rate = (task_done / task_total) if task_total else 0.0

    return {
        "entry_count": len(entries),
        "tasks": {
            "total": task_total,
            "done": task_done,
            "open": task_total - task_done,
            "completion_rate": round(completion_rate, 3),
        },
        "priority_breakdown": priority_counter,
        "top_tags": _top_n(tag_counter, 10),
        "top_categories": _top_n(category_counter, 10),
        "moods": mood_counter,
        "monthly": dict(sorted(monthly.items())),
        "span": _span(dates),
    }


def _load_all_entries() -> list[dict]:
    entries: list[dict] = []
    if not ENTRIES_DIR.exists():
        return entries
    for path in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            entries.append(_load_json(Path(path)))
        except Exception:  # noqa: BLE001
            continue
    return entries


def _top_n(counter: dict[str, int], n: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def _span(dates: list[str]) -> dict[str, str] | None:
    if not dates:
        return None
    return {"first": min(dates), "last": max(dates)}
