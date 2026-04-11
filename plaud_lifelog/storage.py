"""JSON ベースのタイムライン永続化。"""
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ENTRIES_DIR, INDEX_FILE, REPORTS_DIR, TASKS_FILE, ensure_dirs


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


def update_task_status(task_id: str, status: str) -> dict:
    """指定タスクの status を更新し、同期的にエントリJSONにも反映する。"""
    if status not in ("open", "done"):
        raise ValueError(f"status must be 'open' or 'done', got: {status!r}")

    # tasks.json を更新
    if not TASKS_FILE.exists():
        raise FileNotFoundError("tasks.json が存在しません。先に ingest してください。")
    tasks = _load_json(TASKS_FILE)
    if not isinstance(tasks, list):
        raise RuntimeError("tasks.json が不正な形式です")

    target: dict | None = None
    for t in tasks:
        if t.get("id") == task_id:
            t["status"] = status
            target = t
            break
    if target is None:
        raise KeyError(f"task not found: {task_id}")
    _dump_json(TASKS_FILE, tasks)

    # 元エントリの tasks 配列にも反映
    entry_id = target.get("source_entry_id")
    if entry_id:
        entry_path = ENTRIES_DIR / f"{entry_id}.json"
        if entry_path.exists():
            entry = _load_json(entry_path)
            for t in entry.get("tasks", []):
                if t.get("id") == task_id:
                    t["status"] = status
            _dump_json(entry_path, entry)

    return target


def iter_entries_in_range(start: datetime, end: datetime) -> list[dict]:
    """[start, end) の範囲に収まるエントリの完全版をリストで返す。"""
    if not INDEX_FILE.exists():
        return []
    index = _load_json(INDEX_FILE)
    if not isinstance(index, list):
        return []

    selected: list[dict] = []
    for meta in index:
        rec = meta.get("recorded_at") or ""
        try:
            dt = datetime.fromisoformat(rec)
        except ValueError:
            continue
        if start <= dt < end:
            try:
                selected.append(load_entry(meta["id"]))
            except FileNotFoundError:
                continue
    selected.sort(key=lambda e: e.get("recorded_at", ""))
    return selected


def load_report(period: str) -> dict:
    """期間指定でレポート JSON を読み込む。"""
    path = REPORTS_DIR / f"{period}.json"
    if not path.exists():
        raise FileNotFoundError(f"report not found: {period}")
    return _load_json(path)


def search_entries(keyword: str, limit: int | None = None) -> list[dict]:
    """エントリ全件を走査して、キーワードを含むものを返す。

    検索対象: title / headline / narrative / tags / raw.summary /
    raw.transcript / tasks[].title

    戻り値は `{id, date, title, headline, field, snippet}` のリスト。
    """
    if not keyword:
        return []
    needle = keyword.lower()
    ensure_dirs()

    results: list[dict] = []
    for path in sorted(ENTRIES_DIR.glob("*.json"), reverse=True):
        try:
            entry = _load_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        hit = _match_entry(entry, needle)
        if hit is None:
            continue
        results.append({
            "id": entry.get("id"),
            "date": (entry.get("recorded_at") or "")[:10],
            "title": entry.get("title", ""),
            "headline": (entry.get("lifelog") or {}).get("headline", ""),
            "field": hit[0],
            "snippet": hit[1],
        })
        if limit and len(results) >= limit:
            break
    return results


def _match_entry(entry: dict, needle: str) -> tuple[str, str] | None:
    """エントリ内の検索対象フィールドを順に調べ、最初にヒットしたものを返す。"""
    lifelog = entry.get("lifelog") or {}
    raw = entry.get("raw") or {}

    candidates: list[tuple[str, str]] = [
        ("title", str(entry.get("title", ""))),
        ("headline", str(lifelog.get("headline", ""))),
        ("narrative", str(lifelog.get("narrative", ""))),
        ("tags", ",".join(lifelog.get("tags") or [])),
        ("summary", str(raw.get("summary", ""))),
        ("transcript", str(raw.get("transcript", ""))),
    ]
    for t in entry.get("tasks") or []:
        candidates.append(("task", str(t.get("title", ""))))

    for field, text in candidates:
        if not text:
            continue
        low = text.lower()
        idx = low.find(needle)
        if idx >= 0:
            return field, _make_snippet(text, idx, len(needle))
    return None


def _make_snippet(text: str, idx: int, needle_len: int, width: int = 40) -> str:
    start = max(0, idx - width)
    end = min(len(text), idx + needle_len + width)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    snippet = text[start:end].replace("\n", " ")
    return f"{prefix}{snippet}{suffix}"


def save_report(report: dict) -> Path:
    """週次/期間レポートを data/plaud/reports/<period>.json に保存する。"""
    ensure_dirs()
    period = report.get("period") or datetime.now().strftime("%Y-%m-%d")
    path = REPORTS_DIR / f"{period}.json"
    _dump_json(path, report)
    return path


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
