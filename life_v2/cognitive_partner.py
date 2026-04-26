"""Cognitive Continuity Partner: Claude API オーケストレータ。

入力: 自由記述テキスト or Plaud V1 の entry JSON
出力: CoachOutput（スコアカード + dropped + 最大3件のNext Actions）

設計原則:
  - AI失敗時は必ずヒューリスティックでフォールバック（停止しない）
  - 出力は常に「即実行可能」: one_minute_action と calendar_dict を必ず含む
  - JSON 解析は寛容に: コードブロック・前後の文章を許容
"""
from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from .config import AI_ENABLED, AI_MODEL, AI_TIMEOUT, ANTHROPIC_API_KEY, MAX_NEXT_ACTIONS
from .models import CoachOutput, DroppedTask, Scorecard, ValuedTask
from .prompts import (
    COACH_SYSTEM_PROMPT,
    DISTILL_SYSTEM_PROMPT,
    EVENING_RITUAL_SYSTEM_PROMPT,
    MORNING_RITUAL_SYSTEM_PROMPT,
    TRIAGE_SYSTEM_PROMPT,
)
from .scorecard import heuristic_distill, heuristic_score_from_text
from .value_filter import (
    heuristic_filter,
    is_obvious_drop,
    parse_duration,
    split_high_leverage,
)

_MAX_INPUT_CHARS = 16000


def coach(text: str, source_entry_id: str | None = None) -> CoachOutput:
    """ライフログ風テキストから即実行可能な CoachOutput を返す。"""
    if not text or not text.strip():
        return _empty_coach_output()

    if AI_ENABLED:
        try:
            return _coach_via_api(text, source_entry_id)
        except Exception as e:
            print(f"[life_v2] AI coach 失敗: {e} → フォールバック")
    return _coach_via_heuristic(text, source_entry_id)


def triage(open_tasks: list[dict]) -> tuple[list[ValuedTask], list[DroppedTask]]:
    """オープンタスク群を high_leverage / dropped に強制振り分け。"""
    if not open_tasks:
        return [], []
    if AI_ENABLED:
        try:
            return _triage_via_api(open_tasks)
        except Exception as e:
            print(f"[life_v2] AI triage 失敗: {e} → ヒューリスティック")
    return split_high_leverage(open_tasks)


def distill_aesthetic(scorecards_payload: list[dict]) -> dict:
    """過去スコアカード履歴から美学を抽出する。"""
    from .models import Scorecard as _S
    cards = []
    for d in scorecards_payload:
        try:
            cards.append(_S(**d))
        except TypeError:
            continue
    if AI_ENABLED and cards:
        try:
            return _distill_via_api(cards)
        except Exception as e:
            print(f"[life_v2] AI distill 失敗: {e} → ヒューリスティック")
    return heuristic_distill(cards)


def morning_ritual(yesterday_card: dict | None, today_plan_text: str) -> dict:
    if AI_ENABLED:
        try:
            return _morning_via_api(yesterday_card, today_plan_text)
        except Exception as e:
            print(f"[life_v2] AI morning 失敗: {e}")
    return _heuristic_morning(yesterday_card, today_plan_text)


def evening_ritual(today_text: str) -> dict:
    if AI_ENABLED:
        try:
            return _evening_via_api(today_text)
        except Exception as e:
            print(f"[life_v2] AI evening 失敗: {e}")
    return _heuristic_evening(today_text)


# ========== Claude API 経路 ==========

def _client():
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _coach_via_api(text: str, source_entry_id: str | None) -> CoachOutput:
    body = _truncate(text)
    user = (
        f"# 今日 ({date.today().isoformat()}) のライフログ\n\n{body}\n\n"
        f"上記から、捨てるべきタスクと最大{MAX_NEXT_ACTIONS}件のNext Actionsを返してください。"
    )
    response = _client().messages.create(
        model=AI_MODEL,
        max_tokens=2000,
        timeout=AI_TIMEOUT,
        system=COACH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    data = _parse_json(response.content[0].text)
    return _build_coach_output(data, source_entry_id)


def _triage_via_api(open_tasks: list[dict]) -> tuple[list[ValuedTask], list[DroppedTask]]:
    summary = "\n".join(
        f"- [{t.get('priority','medium')}] {t.get('title','')}"
        + (f" (entry={t.get('source_entry_id','')})" if t.get("source_entry_id") else "")
        for t in open_tasks[:80]
    )
    user = f"# オープンタスク({len(open_tasks)}件)\n{summary}\n\n3フィルタで強制振り分け。"
    response = _client().messages.create(
        model=AI_MODEL,
        max_tokens=2400,
        timeout=AI_TIMEOUT,
        system=TRIAGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    data = _parse_json(response.content[0].text)
    high = [_build_valued_task(d) for d in (data.get("high_leverage") or [])]
    dropped = [_build_dropped_task(d) for d in (data.get("dropped") or [])]
    return high, dropped


def _distill_via_api(cards: list[Scorecard]) -> dict:
    body = json.dumps([c.to_dict() for c in cards], ensure_ascii=False, indent=2)
    user = f"# 過去 {len(cards)} 日分のスコアカード\n```json\n{body}\n```"
    response = _client().messages.create(
        model=AI_MODEL,
        max_tokens=1200,
        timeout=AI_TIMEOUT,
        system=DISTILL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    data = _parse_json(response.content[0].text)
    if not data:
        return heuristic_distill(cards)
    return data


def _morning_via_api(yesterday_card: dict | None, today_plan_text: str) -> dict:
    yc = json.dumps(yesterday_card, ensure_ascii=False) if yesterday_card else "(なし)"
    user = (
        f"# 昨日のスコアカード\n{yc}\n\n"
        f"# 今日の予定/メモ\n{_truncate(today_plan_text, 6000)}\n"
    )
    response = _client().messages.create(
        model=AI_MODEL,
        max_tokens=900,
        timeout=AI_TIMEOUT,
        system=MORNING_RITUAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    return _parse_json(response.content[0].text) or _heuristic_morning(yesterday_card, today_plan_text)


def _evening_via_api(today_text: str) -> dict:
    user = f"# 今日のライフログ\n{_truncate(today_text)}"
    response = _client().messages.create(
        model=AI_MODEL,
        max_tokens=900,
        timeout=AI_TIMEOUT,
        system=EVENING_RITUAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user}],
    )
    return _parse_json(response.content[0].text) or _heuristic_evening(today_text)


# ========== フォールバック経路 ==========

def _coach_via_heuristic(text: str, source_entry_id: str | None) -> CoachOutput:
    today = date.today().isoformat()
    card = heuristic_score_from_text(text)
    card.source_entry_ids = [source_entry_id] if source_entry_id else []

    candidate_tasks = _extract_tasks_from_text(text, source_entry_id)
    high, dropped = split_high_leverage(candidate_tasks, max_keep=MAX_NEXT_ACTIONS)

    headline = "両手を空けて1ブロックに集中"
    one_minute = "カレンダーを開いて、最重要1ブロックの開始時刻を確定する"
    aesthetic = "他者評価ではなく、4軸の自分のスコアだけを尺度にする"

    return CoachOutput(
        date=today,
        scorecard=card,
        dropped=dropped,
        next_actions=high,
        headline=headline,
        one_minute_action=one_minute,
        aesthetic_signal=aesthetic,
    )


def _heuristic_morning(yesterday_card: dict | None, today_plan_text: str) -> dict:
    return {
        "intention": "今日は1ブロックだけ深く",
        "two_handed_block": {
            "start": "09:00",
            "duration_minutes": 90,
            "task": "今日唯一の高価値タスクに着手",
            "preflight": [
                "通知をオフにする",
                "机の上を空にする（両手を空ける）",
                "タイマーを90分にセット",
            ],
        },
        "drop_today": [
            "返信のための返信",
            "前例踏襲の書類確認",
        ],
        "family_share": "夕食時に今日学んだことを1つだけ家族に話す",
        "source": "heuristic",
    }


def _heuristic_evening(today_text: str) -> dict:
    card = heuristic_score_from_text(today_text)
    return {
        "scorecard": {
            "systemize": card.systemize, "systemize_note": card.systemize_note,
            "declutter": card.declutter, "declutter_note": card.declutter_note,
            "two_handed": card.two_handed, "two_handed_note": card.two_handed_note,
            "knowledge_share": card.knowledge_share, "knowledge_share_note": card.knowledge_share_note,
        },
        "what_worked": "(ヒューリスティック) 仕組みに関わる時間が確保できた程度",
        "what_was_drag": "(ヒューリスティック) 片手間タスクの侵食が懸念される",
        "tomorrow_first_move": "明日朝、カレンダーで90分ブロックを先取りする",
        "source": "heuristic",
    }


# ========== 入力テキスト → タスク候補抽出（フォールバック用） ==========

_TASK_LINE_PATTERN = re.compile(
    r"^\s*(?:[-*・●]\s+|\d+[.)]\s+|TODO[:：]\s*|やる[:：]\s*)(.+)$",
    re.MULTILINE,
)


def _extract_tasks_from_text(text: str, source_entry_id: str | None) -> list[dict]:
    """箇条書き・TODO/やる: などの行をタスク候補として吸い上げる。"""
    candidates: list[dict] = []
    for m in _TASK_LINE_PATTERN.finditer(text):
        title = m.group(1).strip().rstrip("。.")
        if not title or len(title) < 3:
            continue
        candidates.append({
            "title": title[:80],
            "description": "",
            "source_entry_id": source_entry_id,
        })
    return candidates[:30]


# ========== JSON パース ==========

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def _parse_json(text: str) -> dict[str, Any]:
    if not text:
        return {}
    m = _JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            return {}
    return {}


# ========== AI レスポンス → モデル変換 ==========

def _build_coach_output(data: dict, source_entry_id: str | None) -> CoachOutput:
    today = date.today().isoformat()
    sc_data = data.get("scorecard") or {}
    card = Scorecard(
        date=today,
        systemize=_int_or_zero(sc_data.get("systemize")),
        declutter=_int_or_zero(sc_data.get("declutter")),
        two_handed=_int_or_zero(sc_data.get("two_handed")),
        knowledge_share=_int_or_zero(sc_data.get("knowledge_share")),
        systemize_note=str(sc_data.get("systemize_note", ""))[:200],
        declutter_note=str(sc_data.get("declutter_note", ""))[:200],
        two_handed_note=str(sc_data.get("two_handed_note", ""))[:200],
        knowledge_share_note=str(sc_data.get("knowledge_share_note", ""))[:200],
        source_entry_ids=[source_entry_id] if source_entry_id else [],
    )
    dropped = [_build_dropped_task(d) for d in (data.get("dropped") or [])]
    raw_actions = data.get("next_actions") or []
    actions = [_build_valued_task(d) for d in raw_actions[:MAX_NEXT_ACTIONS]]
    overflow = raw_actions[MAX_NEXT_ACTIONS:]
    for d in overflow:
        dropped.append(DroppedTask(
            title=str(d.get("title", ""))[:80],
            reason=f"{MAX_NEXT_ACTIONS}件の枠から漏れたため後回し",
            disposition="defer",
        ))

    return CoachOutput(
        date=today,
        headline=str(data.get("headline", ""))[:30],
        one_minute_action=str(data.get("one_minute_action", ""))[:120],
        aesthetic_signal=str(data.get("aesthetic_signal", ""))[:200],
        scorecard=card,
        dropped=dropped,
        next_actions=actions,
    )


def _build_valued_task(d: dict) -> ValuedTask:
    title = str(d.get("title", "")).strip()[:80] or "(無題)"
    description = str(d.get("description", "")).strip()[:200]
    duration = parse_duration(d.get("duration_minutes", 30))
    priority = str(d.get("priority", "Medium")).strip().capitalize()
    if priority not in ("High", "Medium", "Low"):
        priority = "Medium"
    return ValuedTask(
        title=title,
        description=description,
        duration_minutes=duration,
        priority=priority,
        leverage=bool(d.get("leverage", False)),
        mission=bool(d.get("mission", False)),
        uniqueness=bool(d.get("uniqueness", False)),
        source_entry_id=d.get("source_entry_id"),
    )


def _build_dropped_task(d: dict) -> DroppedTask:
    title = str(d.get("title", "")).strip()[:80] or "(無題)"
    reason = str(d.get("reason", "")).strip()[:200] or "3フィルタ未該当"
    disposition = str(d.get("disposition", "drop")).strip().lower()
    if disposition not in ("drop", "automate", "delegate", "defer"):
        disposition = "drop"
    return DroppedTask(
        title=title,
        reason=reason,
        disposition=disposition,
        source_entry_id=d.get("source_entry_id"),
    )


def _int_or_zero(v: Any) -> int:
    try:
        return max(0, min(10, int(v)))
    except (TypeError, ValueError):
        return 0


def _truncate(text: str, limit: int = _MAX_INPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…(以下略)…"


def _empty_coach_output() -> CoachOutput:
    today = date.today().isoformat()
    return CoachOutput(
        date=today,
        scorecard=Scorecard(date=today),
        dropped=[],
        next_actions=[],
        headline="入力なし",
        one_minute_action="ライフログを録音または貼り付けてください",
        aesthetic_signal="",
    )
