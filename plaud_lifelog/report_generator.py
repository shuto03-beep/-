"""期間レポート（週次ライフログ）を生成する。"""
import json
from datetime import datetime, timedelta
from typing import Any

from .config import AI_ENABLED, AI_MODEL, AI_TIMEOUT, ANTHROPIC_API_KEY

# レポート用プロンプトに渡す 1 エントリあたりの要約最大文字数
_PER_ENTRY_CHARS = 1200


def build_report(entries: list[dict], start: datetime, end: datetime) -> dict:
    """期間内のエントリからレポート dict を構築する。"""
    period = f"{start.date().isoformat()}_to_{(end - timedelta(days=1)).date().isoformat()}"

    tasks_flat: list[dict] = []
    headlines: list[dict] = []
    tag_counter: dict[str, int] = {}
    mood_counter: dict[str, int] = {}

    for e in entries:
        lifelog = e.get("lifelog") or {}
        headlines.append({
            "id": e.get("id"),
            "date": (e.get("recorded_at") or "")[:10],
            "title": e.get("title", ""),
            "headline": lifelog.get("headline", ""),
        })
        for tag in lifelog.get("tags") or []:
            tag_counter[tag] = tag_counter.get(tag, 0) + 1
        mood = lifelog.get("mood") or ""
        if mood:
            mood_counter[mood] = mood_counter.get(mood, 0) + 1
        for t in e.get("tasks") or []:
            tasks_flat.append(t)

    open_tasks = [t for t in tasks_flat if t.get("status") != "done"]
    done_tasks = [t for t in tasks_flat if t.get("status") == "done"]

    task_by_priority = {"high": 0, "medium": 0, "low": 0}
    for t in open_tasks:
        p = t.get("priority", "medium")
        task_by_priority[p] = task_by_priority.get(p, 0) + 1

    narrative = _generate_narrative(entries, start, end)

    return {
        "period": period,
        "start": start.date().isoformat(),
        "end": (end - timedelta(days=1)).date().isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "entry_count": len(entries),
        "headlines": headlines,
        "top_tags": sorted(tag_counter.items(), key=lambda kv: -kv[1])[:10],
        "moods": mood_counter,
        "tasks": {
            "total": len(tasks_flat),
            "open": len(open_tasks),
            "done": len(done_tasks),
            "by_priority": task_by_priority,
            "open_list": sorted(
                open_tasks,
                key=lambda t: (
                    {"high": 0, "medium": 1, "low": 2}.get(
                        t.get("priority", "medium"), 1
                    ),
                    t.get("due") or "9999-99-99",
                ),
            ),
        },
        "narrative": narrative,
    }


# ---------- ナラティブ生成（Claude / フォールバック） ----------

def _generate_narrative(entries: list[dict], start: datetime, end: datetime) -> dict:
    if not entries:
        return {
            "summary": "(期間内にエントリがありません)",
            "highlights": [],
            "next_focus": [],
            "source": "empty",
        }
    if not AI_ENABLED:
        return _fallback_narrative(entries, start, end)
    try:
        return _call_narrative_api(entries, start, end)
    except Exception as e:
        print(f"  [AI] report narrative 生成失敗: {e}")
        return _fallback_narrative(entries, start, end)


def _call_narrative_api(entries: list[dict], start: datetime, end: datetime) -> dict:
    import anthropic

    user_prompt = _build_report_prompt(entries, start, end)
    system = (
        "あなたは個人のライフログを振り返るアシスタントです。"
        "入力された期間の複数エントリを俯瞰し、"
        "本人向けに温かみのある振り返りを生成してください。"
        "必ず以下の JSON 形式のみで回答してください:\n"
        '{"summary": "5〜8文の振り返り本文",'
        ' "highlights": ["ハイライト1", "ハイライト2", "ハイライト3"],'
        ' "next_focus": ["次の注力テーマ1", "次の注力テーマ2"]}'
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=1500,
        timeout=AI_TIMEOUT,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )

    data = _parse_json(response.content[0].text)
    return {
        "summary": str(data.get("summary", "")),
        "highlights": _as_str_list(data.get("highlights")),
        "next_focus": _as_str_list(data.get("next_focus")),
        "source": "claude_api",
    }


def _fallback_narrative(entries: list[dict], start: datetime, end: datetime) -> dict:
    lines = []
    for e in entries[:10]:
        date = (e.get("recorded_at") or "")[:10]
        headline = (e.get("lifelog") or {}).get("headline") or e.get("title", "")
        lines.append(f"- {date}: {headline}")
    summary = (
        f"{start.date().isoformat()}〜{(end - timedelta(days=1)).date().isoformat()} の "
        f"{len(entries)} 件のエントリ。"
    )
    return {
        "summary": summary,
        "highlights": lines,
        "next_focus": [],
        "source": "fallback",
    }


def _build_report_prompt(entries: list[dict], start: datetime, end: datetime) -> str:
    parts = [
        f"# 対象期間\n{start.date().isoformat()} 〜 {(end - timedelta(days=1)).date().isoformat()}\n",
        f"# エントリ総数\n{len(entries)}\n",
        "# 各エントリ（日付 / タイトル / 要約 / タスク）",
    ]
    for e in entries:
        date = (e.get("recorded_at") or "")[:10]
        title = e.get("title", "")
        lifelog = e.get("lifelog") or {}
        summary = lifelog.get("narrative") or (e.get("raw") or {}).get("summary") or ""
        if len(summary) > _PER_ENTRY_CHARS:
            summary = summary[:_PER_ENTRY_CHARS] + "…"
        task_lines = []
        for t in e.get("tasks") or []:
            task_lines.append(
                f"  - [{t.get('status', 'open')}] ({t.get('priority', 'medium')}) "
                f"{t.get('title', '')}"
            )
        block = [f"\n## {date} {title}", f"{summary}"]
        if task_lines:
            block.append("tasks:")
            block.extend(task_lines)
        parts.append("\n".join(block))
    return "\n".join(parts)


def _parse_json(text: str) -> dict[str, Any]:
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
