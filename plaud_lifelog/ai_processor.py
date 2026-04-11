"""Claude API でライフログとタスクを生成する。"""
import json
from typing import Any

from .config import AI_ENABLED, AI_MODEL, AI_TIMEOUT, ANTHROPIC_API_KEY
from .models import ParsedDoc

# 入力テキストが長すぎる場合の上限（トークン削減のため）
_MAX_INPUT_CHARS = 12000


def generate_lifelog(parsed: ParsedDoc) -> dict:
    """要約・文字起こしからライフログ風のメタデータを生成する。"""
    if not AI_ENABLED:
        return _fallback_lifelog(parsed)
    try:
        return _call_lifelog_api(parsed)
    except Exception as e:
        print(f"  [AI] lifelog 生成失敗: {e}")
        return _fallback_lifelog(parsed)


def extract_tasks(parsed: ParsedDoc) -> dict:
    """要約・文字起こしからタスクを抽出し、優先度を分析する。"""
    if not AI_ENABLED:
        return _fallback_tasks(parsed)
    try:
        return _call_tasks_api(parsed)
    except Exception as e:
        print(f"  [AI] タスク抽出失敗: {e}")
        return _fallback_tasks(parsed)


# ---------- Claude API 呼び出し ----------

def _call_lifelog_api(parsed: ParsedDoc) -> dict:
    import anthropic

    user_prompt = _build_input_block(parsed)
    system = (
        "あなたはライフログエディタです。"
        "入力された会話・会議の要約と文字起こしから、"
        "本人が後で読み返したくなる日記風のナラティブとメタデータを生成してください。"
        "必ず以下の JSON 形式のみで回答してください（他の文章は禁止）:\n"
        '{"headline": "30字以内の見出し",'
        ' "narrative": "2〜4文の日記風本文",'
        ' "tags": ["タグ1", "タグ2"],'
        ' "people": ["登場人物"],'
        ' "locations": ["場所"],'
        ' "mood": "気分の一言",'
        ' "key_points": ["重要ポイント1", "重要ポイント2"]}'
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=800,
        timeout=AI_TIMEOUT,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    data = _parse_json_response(response.content[0].text)
    return {
        "headline": str(data.get("headline", parsed.title))[:80],
        "narrative": str(data.get("narrative", "")),
        "tags": _as_str_list(data.get("tags")),
        "people": _as_str_list(data.get("people")),
        "locations": _as_str_list(data.get("locations")),
        "mood": str(data.get("mood", "")),
        "key_points": _as_str_list(data.get("key_points")),
        "source": "claude_api",
    }


def _call_tasks_api(parsed: ParsedDoc) -> dict:
    import anthropic

    user_prompt = _build_input_block(parsed)
    system = (
        "あなたはタスク抽出アシスタントです。"
        "会話や会議の内容からアクションアイテム（TODO）を抽出し、"
        "優先度 (high/medium/low)、期限 (YYYY-MM-DD / 不明なら null)、"
        "カテゴリ（仕事 / プライベート / 学習 / 健康 など）を推定してください。"
        "必ず以下の JSON 形式のみで回答してください:\n"
        '{"tasks": ['
        '{"title": "タスク名", "priority": "high|medium|low",'
        ' "due": "YYYY-MM-DD or null", "category": "カテゴリ"}'
        '],'
        ' "analysis": {"effort_summary": "全体の所感", "blockers": ["ブロッカー"]}}'
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=1200,
        timeout=AI_TIMEOUT,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    data = _parse_json_response(response.content[0].text)
    raw_tasks = data.get("tasks") or []
    tasks: list[dict] = []
    for t in raw_tasks:
        if not isinstance(t, dict):
            continue
        title = str(t.get("title", "")).strip()
        if not title:
            continue
        tasks.append({
            "title": title,
            "priority": _normalize_priority(t.get("priority")),
            "due": t.get("due") or None,
            "category": str(t.get("category", "")).strip() or None,
        })

    analysis = data.get("analysis") or {}
    return {
        "tasks": tasks,
        "analysis": {
            "effort_summary": str(analysis.get("effort_summary", "")),
            "blockers": _as_str_list(analysis.get("blockers")),
        },
        "source": "claude_api",
    }


# ---------- フォールバック（APIキー無し/失敗時） ----------

def _fallback_lifelog(parsed: ParsedDoc) -> dict:
    body = parsed.summary or parsed.transcript or parsed.raw_text
    snippet = body.strip().replace("\n", " ")[:180]
    return {
        "headline": parsed.title[:40],
        "narrative": snippet,
        "tags": ["plaud"],
        "people": [],
        "locations": [],
        "mood": "",
        "key_points": [],
        "source": "fallback",
    }


def _fallback_tasks(parsed: ParsedDoc) -> dict:
    return {
        "tasks": [],
        "analysis": {
            "effort_summary": "(AI 未使用のためタスク抽出はスキップ)",
            "blockers": [],
        },
        "source": "fallback",
    }


# ---------- ユーティリティ ----------

def _build_input_block(parsed: ParsedDoc) -> str:
    summary = (parsed.summary or "").strip()
    transcript = (parsed.transcript or "").strip()
    if len(transcript) > _MAX_INPUT_CHARS:
        transcript = transcript[:_MAX_INPUT_CHARS] + "\n…(以下略)…"
    return (
        f"# タイトル\n{parsed.title}\n\n"
        f"# 収録日\n{parsed.recorded_at.date().isoformat()}\n\n"
        f"# 要約\n{summary or '(要約セクションなし)'}\n\n"
        f"# 文字起こし\n{transcript or '(本文なし)'}\n"
    )


def _parse_json_response(text: str) -> dict[str, Any]:
    """Claude レスポンスから JSON 部分を抽出する（ai_advisor.py と同じ方式）。"""
    if not text:
        return {}
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return {}


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _normalize_priority(value: Any) -> str:
    v = str(value or "").strip().lower()
    if v in ("high", "medium", "low"):
        return v
    if v in ("高", "中", "低"):
        return {"高": "high", "中": "medium", "低": "low"}[v]
    return "medium"
