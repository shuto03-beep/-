"""3フィルタによる高価値タスク判定。

filter1: leverage    - 一度の労力が未来の時間を生む（仕組み化・テンプレ化）
filter2: mission     - 教育環境の再構築・家族の知的成長に直結
filter3: uniqueness  - メタ認知・AI活用・哲学思考を持つこのユーザーにしかできない

AI 分析が利用できない場合のフォールバック判定にも使う。
キーワード・ヒューリスティックは保守的に、過大評価しない方向で設計する。
"""
from __future__ import annotations

import re

from .models import DroppedTask, ValuedTask

# キーワード辞書（簡易ヒューリスティック）
_LEVERAGE_KEYWORDS = (
    "テンプレ", "仕組み", "自動化", "automation", "ワークフロー", "workflow",
    "プロンプト", "スクリプト", "macro", "マクロ", "再利用",
    "チェックリスト", "ナレッジベース", "vault", "obsidian",
)
_MISSION_KEYWORDS = (
    "いなチャレ", "部活", "地域移行", "教育", "授業", "生徒", "保護者",
    "家族", "息子", "娘", "妻", "夫", "子供", "学校", "PTA",
)
_UNIQUENESS_KEYWORDS = (
    "AI", "Claude", "Gemini", "プロンプト", "メタ認知", "哲学",
    "弁証法", "Obsidian", "PLAUD", "ブレイン", "知的",
)
_DROP_KEYWORDS = (
    "出席する", "確認する", "返信する", "書類", "申請書",
    "印刷", "コピー", "並び替え", "片付け", "整理整頓",
)


def heuristic_filter(text: str) -> tuple[bool, bool, bool]:
    """テキストから3フィルタの該当を保守的に判定する。

    全マッチしないことも普通にあり得る（その場合 dropped 行き）。
    """
    if not text:
        return False, False, False
    t = text.lower()
    leverage = any(k.lower() in t for k in _LEVERAGE_KEYWORDS)
    mission = any(k.lower() in t for k in _MISSION_KEYWORDS)
    uniqueness = any(k.lower() in t for k in _UNIQUENESS_KEYWORDS)
    return leverage, mission, uniqueness


def is_obvious_drop(title: str) -> bool:
    """明らかに低価値（雑務）と判定できるタイトルか。"""
    if not title:
        return False
    t = title.lower()
    return any(k.lower() in t for k in _DROP_KEYWORDS)


def split_high_leverage(tasks: list[dict], max_keep: int = 5) -> tuple[list[ValuedTask], list[DroppedTask]]:
    """フォールバック: AIなしで dict 形式のタスク群を強制振り分け。

    Args:
        tasks: 各 dict は最低 "title" を持つ。"description" や "source_entry_id" は任意。
        max_keep: high_leverage に残す上限件数（捨てる装置）。

    Returns:
        (high_leverage, dropped) のタプル。
    """
    scored: list[tuple[int, ValuedTask]] = []
    dropped: list[DroppedTask] = []

    for raw in tasks:
        title = str(raw.get("title", "")).strip()
        if not title:
            continue
        desc = str(raw.get("description", "")).strip()
        src = raw.get("source_entry_id")

        if is_obvious_drop(title):
            dropped.append(DroppedTask(
                title=title,
                reason="雑務カテゴリ。仕組み化・委任・後回しの対象。",
                disposition="defer",
                source_entry_id=src,
            ))
            continue

        leverage, mission, uniqueness = heuristic_filter(f"{title} {desc}")
        count = int(leverage) + int(mission) + int(uniqueness)
        if count == 0:
            dropped.append(DroppedTask(
                title=title,
                reason="3フィルタ(leverage/mission/uniqueness)に1つも合致せず。",
                disposition="drop",
                source_entry_id=src,
            ))
            continue

        priority = "High" if count >= 2 else "Medium"
        duration = _guess_duration(title, desc)
        valued = ValuedTask(
            title=title,
            description=desc or _build_default_description(leverage, mission, uniqueness),
            duration_minutes=duration,
            priority=priority,
            leverage=leverage,
            mission=mission,
            uniqueness=uniqueness,
            source_entry_id=src,
        )
        scored.append((count, valued))

    # フィルタ該当数の多い順に並び替え、上位 max_keep のみ残す
    scored.sort(key=lambda pair: (-pair[0], -pair[1].duration_minutes))
    keep = [v for _, v in scored[:max_keep]]
    overflow = scored[max_keep:]
    for _, v in overflow:
        dropped.append(DroppedTask(
            title=v.title,
            reason=f"上位{max_keep}件枠から漏れたため後回し。",
            disposition="defer",
            source_entry_id=v.source_entry_id,
        ))
    return keep, dropped


def _guess_duration(title: str, description: str) -> int:
    """ヒューリスティックなブロック長推定。"""
    text = f"{title} {description}".lower()
    if any(k in text for k in ("レビュー", "確認", "返信")):
        return 15
    if any(k in text for k in ("設計", "構想", "プロンプト", "テンプレ")):
        return 60
    if any(k in text for k in ("執筆", "原稿", "提案書", "資料作成")):
        return 90
    return 30


def _build_default_description(leverage: bool, mission: bool, uniqueness: bool) -> str:
    parts = []
    if leverage:
        parts.append("レバレッジ")
    if mission:
        parts.append("使命")
    if uniqueness:
        parts.append("独自性")
    return f"フィルタ({'・'.join(parts)})に合致。"


_TIME_REGEX = re.compile(r"(\d+)\s*分")


def parse_duration(raw) -> int:
    """duration_minutes を頑健にパース。"""
    if isinstance(raw, int):
        return max(5, min(180, raw))
    if isinstance(raw, float):
        return max(5, min(180, int(raw)))
    if isinstance(raw, str):
        m = _TIME_REGEX.search(raw)
        if m:
            return max(5, min(180, int(m.group(1))))
        try:
            return max(5, min(180, int(raw.strip())))
        except ValueError:
            return 30
    return 30
