"""JSON ベースのタイムライン永続化。"""
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ENTRIES_DIR, INDEX_FILE, TASKS_FILE, ensure_dirs


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_entry_id(recorded_at: datetime, title: str) -> str:
    """日付 + スラグから一意のエントリIDを生成する。"""
    date_part = recorded_at.strftime("%Y-%m-%d")
    slug = _slugify(title) or "entry"
    return f"{date_part}_{slug}"


def save_entry(entry: dict) -> Path:
    """エントリを保存し、index.json と tasks.json を更新する。"""
    ensure_dirs()
    entry_id = entry["id"]
    path = ENTRIES_DIR / f"{entry_id}.json"
    _dump_json(path, entry)

    _update_index(entry)
    _update_tasks(entry)
    return path


def load_entry(entry_id: str) -> dict:
    path = ENTRIES_DIR / f"{entry_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"entry not found: {entry_id}")
    return _load_json(path)


def list_entries(limit: int | None = None) -> list[dict]:
    """index.json から新しい順にエントリを返す。"""
    index = _load_json(INDEX_FILE) if INDEX_FILE.exists() else []
    if not isinstance(index, list):
        return []
    index.sort(key=lambda e: e.get("recorded_at", ""), reverse=True)
    if limit:
        return index[:limit]
    return index


def list_open_tasks(include_done: bool = False) -> list[dict]:
    data = _load_json(TASKS_FILE) if TASKS_FILE.exists() else []
    if not isinstance(data, list):
        return []
    if include_done:
        tasks = data
    else:
        tasks = [t for t in data if t.get("status") != "done"]
    tasks.sort(
        key=lambda t: (
            _PRIORITY_ORDER.get(t.get("priority", "medium"), 1),
            t.get("due") or "9999-99-99",
        )
    )
    return tasks


# ---------- 内部ヘルパー ----------

def _update_index(entry: dict) -> None:
    index: list[dict] = []
    if INDEX_FILE.exists():
        loaded = _load_json(INDEX_FILE)
        if isinstance(loaded, list):
            index = [e for e in loaded if e.get("id") != entry["id"]]

    index.append({
        "id": entry["id"],
        "title": entry.get("title", ""),
        "recorded_at": entry.get("recorded_at"),
        "headline": entry.get("lifelog", {}).get("headline", ""),
        "tags": entry.get("lifelog", {}).get("tags", []),
        "task_count": len(entry.get("tasks", [])),
    })
    _dump_json(INDEX_FILE, index)


def _update_tasks(entry: dict) -> None:
    tasks: list[dict] = []
    if TASKS_FILE.exists():
        loaded = _load_json(TASKS_FILE)
        if isinstance(loaded, list):
            # 同じエントリ由来のタスクを一旦除去して再登録
            tasks = [
                t for t in loaded if t.get("source_entry_id") != entry["id"]
            ]

    for t in entry.get("tasks", []):
        tasks.append(t)

    _dump_json(TASKS_FILE, tasks)


def _dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(text: str) -> str:
    """タイトルをファイル名に使える短い識別子に変換する。"""
    nfkd = unicodedata.normalize("NFKC", text)
    nfkd = nfkd.strip().lower()
    # 空白→ハイフン、ファイル名に使えない文字を除去
    nfkd = re.sub(r"\s+", "-", nfkd)
    nfkd = re.sub(r"[\\/:*?\"<>|]", "", nfkd)
    nfkd = nfkd.strip("-._")
    return nfkd[:40]
