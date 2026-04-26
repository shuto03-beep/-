"""Next Action のカレンダー登録用 JSON 出力。

「分析→実行」の摩擦を消すため、出力は3形式に固定:
  1. 仕様プロンプトと完全互換の JSON（コピペでカレンダー登録スクリプトに通せる）
  2. .ics（iCalendar）一括ダウンロード形式
  3. CLI 表示用の人間可読サマリー（実行確認の Yes/No だけ求める）
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from .config import DAILY_HIGH_LEVERAGE_BUDGET_MIN
from .models import ValuedTask


def to_calendar_json(tasks: Iterable[ValuedTask], indent: int = 2) -> str:
    """ユーザー仕様の JSON 配列形式で出力する。"""
    payload = [t.to_calendar_dict() for t in tasks]
    return json.dumps(payload, ensure_ascii=False, indent=indent)


def to_ics(
    tasks: Iterable[ValuedTask],
    start_at: datetime | None = None,
    gap_minutes: int = 10,
) -> str:
    """直列で並べた .ics（iCalendar）テキストを返す。

    最初のタスクを start_at から開始し、各タスクの所要時間 + gap_minutes 後に
    次のタスクを配置する。デフォルトの start_at は「今から30分後の0/30分丸め」。
    """
    if start_at is None:
        now = datetime.now() + timedelta(minutes=30)
        # 0分か30分丸め
        start_at = now.replace(minute=(0 if now.minute < 30 else 30), second=0, microsecond=0)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//life_v2//Cognitive Continuity Partner//JP",
        "CALSCALE:GREGORIAN",
    ]
    cursor = start_at
    for task in tasks:
        end = cursor + timedelta(minutes=int(task.duration_minutes))
        uid = f"{uuid4()}@life_v2"
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{cursor.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{_ics_escape(task.title)}",
            f"DESCRIPTION:{_ics_escape(_ics_description(task))}",
            f"PRIORITY:{_priority_to_ics(task.priority)}",
            "END:VEVENT",
        ])
        cursor = end + timedelta(minutes=gap_minutes)
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def to_human_summary(tasks: Iterable[ValuedTask], one_minute_action: str = "") -> str:
    """端末表示用の人間可読サマリ。Yes/No 承認だけ求める形に整形。"""
    out = ["⚡ Next Actions"]
    items = list(tasks)
    if not items:
        out.append("  (高価値タスクは検出されませんでした。今日は『戦略的休息』を選んでください)")
        return "\n".join(out)

    total_min = sum(int(t.duration_minutes) for t in items)
    over = total_min - DAILY_HIGH_LEVERAGE_BUDGET_MIN
    for i, t in enumerate(items, 1):
        flags = []
        if t.leverage:
            flags.append("L")
        if t.mission:
            flags.append("M")
        if t.uniqueness:
            flags.append("U")
        flag_str = f"[{'/'.join(flags)}]" if flags else "[-]"
        out.append(
            f"  {i}. {flag_str} {t.title}  ({t.duration_minutes}分 / {t.priority})"
        )
        if t.description:
            out.append(f"      → {t.description}")
    out.append("")
    out.append(f"  合計: {total_min}分 / 1日予算 {DAILY_HIGH_LEVERAGE_BUDGET_MIN}分")
    if over > 0:
        out.append(f"  ⚠ 予算超過 +{over}分。1件は明日に回すべき。")
    if one_minute_action:
        out.append("")
        out.append(f"  🔘 1分以内の最初の一手: {one_minute_action}")
        out.append("  → これに着手するなら Y、しないなら N を返してください。")
    return "\n".join(out)


def write_calendar_json(tasks: Iterable[ValuedTask], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_calendar_json(tasks), encoding="utf-8")
    return path


def write_ics(tasks: Iterable[ValuedTask], path: Path, **kwargs) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_ics(tasks, **kwargs), encoding="utf-8")
    return path


# ---------- 内部ユーティリティ ----------

def _ics_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _ics_description(task: ValuedTask) -> str:
    flags = []
    if task.leverage:
        flags.append("leverage")
    if task.mission:
        flags.append("mission")
    if task.uniqueness:
        flags.append("uniqueness")
    flag_part = ",".join(flags) or "n/a"
    return f"{task.description}\n[filters: {flag_part}]"


def _priority_to_ics(priority: str) -> int:
    p = (priority or "").lower()
    if p == "high":
        return 1
    if p == "low":
        return 9
    return 5
