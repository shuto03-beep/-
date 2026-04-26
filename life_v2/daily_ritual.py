"""朝・夜の儀式（Morning Set / Evening Ledger）の永続化。

Three-Beat Rhythm:
  - 朝(Morning Set): 昨日のスコアカード + 今日の予定 → 意図 / 90分ブロック / 捨てる候補
  - 昼(Midday Pivot): 仕様省略（朝のブロック終了後にオプションで挟める）
  - 夜(Evening Ledger): 今日のライフログ → スコアカード採点 + 明日の最初の一手

朝は「両手を空ける」を物理的に実行できる preflight を必ず含み、
夜は「明日カレンダーを開いて押すボタン」を1つだけ確定させる。
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .config import RITUAL_DIR, ensure_dirs


def save_ritual(kind: str, payload: dict) -> Path:
    """kind は 'morning' or 'evening'。日付ファイルに JSON で保存。"""
    if kind not in ("morning", "evening"):
        raise ValueError(f"unknown ritual kind: {kind}")
    ensure_dirs()
    today = date.today().isoformat()
    path = RITUAL_DIR / f"{today}_{kind}.json"
    record = {
        "kind": kind,
        "date": today,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "payload": payload,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_latest(kind: str) -> dict | None:
    if not RITUAL_DIR.exists():
        return None
    matches = sorted(RITUAL_DIR.glob(f"*_{kind}.json"), reverse=True)
    if not matches:
        return None
    return json.loads(matches[0].read_text(encoding="utf-8"))


def format_morning(payload: dict) -> str:
    """朝の儀式結果を端末表示用に整形。"""
    lines = ["🌅 Morning Set"]
    intention = payload.get("intention", "")
    if intention:
        lines.append(f"  意図: {intention}")
    block = payload.get("two_handed_block") or {}
    if block:
        start = block.get("start", "??:??")
        dur = block.get("duration_minutes", 0)
        task = block.get("task", "")
        lines.append(f"  両手ブロック: {start} から {dur}分 — {task}")
        for pf in block.get("preflight", []) or []:
            lines.append(f"    ☐ {pf}")
    drop = payload.get("drop_today") or []
    if drop:
        lines.append("  今日捨てるもの:")
        for d in drop:
            lines.append(f"    🗑 {d}")
    family = payload.get("family_share")
    if family:
        lines.append(f"  家族と共有: {family}")
    return "\n".join(lines)


def format_evening(payload: dict) -> str:
    """夜の儀式結果を端末表示用に整形。"""
    lines = ["🌙 Evening Ledger"]
    sc = payload.get("scorecard") or {}
    lines.append("  内的スコアカード:")
    for axis, label in (
        ("systemize", "仕組み化"),
        ("declutter", "断捨離"),
        ("two_handed", "両手タスク"),
        ("knowledge_share", "知の共有"),
    ):
        score = sc.get(axis, 0)
        note = sc.get(f"{axis}_note", "")
        lines.append(f"    {label:>6}: {score}/10 — {note}")
    worked = payload.get("what_worked")
    drag = payload.get("what_was_drag")
    if worked:
        lines.append(f"  機能した仕組み: {worked}")
    if drag:
        lines.append(f"  摩擦源        : {drag}")
    move = payload.get("tomorrow_first_move")
    if move:
        lines.append("")
        lines.append(f"  🔘 明日の最初の一手: {move}")
    return "\n".join(lines)
