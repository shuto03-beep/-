"""蓄積したライフログを俯瞰する集計ロジック。"""
import json
from pathlib import Path
from typing import Any

from .config import AI_ENABLED, AI_MODEL, AI_TIMEOUT, ANTHROPIC_API_KEY, ENTRIES_DIR
from .storage import load_json


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


def generate_trend_analysis(stats_data: dict) -> dict[str, Any]:
    """統計データから Claude で傾向分析コメントを生成する。

    APIキー未設定時・失敗時は簡易ヒューリスティックで代替。
    """
    if stats_data.get("entry_count", 0) == 0:
        return {
            "summary": "(エントリがまだありません)",
            "observations": [],
            "suggestions": [],
            "source": "empty",
        }
    if not AI_ENABLED:
        return _fallback_trend(stats_data)
    try:
        return _call_trend_api(stats_data)
    except Exception as e:  # noqa: BLE001
        print(f"  [AI] trend 分析失敗: {e}")
        return _fallback_trend(stats_data)


def _call_trend_api(stats_data: dict) -> dict[str, Any]:
    import anthropic

    # Claude に渡す簡潔な統計サマリ
    payload = {
        "entry_count": stats_data.get("entry_count"),
        "span": stats_data.get("span"),
        "tasks": stats_data.get("tasks"),
        "priority_breakdown": stats_data.get("priority_breakdown"),
        "top_tags": stats_data.get("top_tags"),
        "top_categories": stats_data.get("top_categories"),
        "moods": stats_data.get("moods"),
        "monthly": stats_data.get("monthly"),
    }

    system = (
        "あなたは個人のライフログを俯瞰するコーチです。"
        "与えられた集計データから、傾向の観察と具体的な次のアクション提案を"
        "温かみのあるトーンで返してください。"
        "必ず以下の JSON 形式のみで回答してください:\n"
        '{"summary": "3〜5文の全体所感",'
        ' "observations": ["気づき1", "気づき2", "気づき3"],'
        ' "suggestions": ["次にやると良いこと1", "次にやると良いこと2"]}'
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=1200,
        timeout=AI_TIMEOUT,
        system=system,
        messages=[{
            "role": "user",
            "content": (
                "以下は個人のライフログの集計データです（JSON）。\n\n"
                + json.dumps(payload, ensure_ascii=False, indent=2)
            ),
        }],
    )

    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return _fallback_trend(stats_data)
    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError:
        return _fallback_trend(stats_data)

    return {
        "summary": str(data.get("summary", "")),
        "observations": _as_str_list(data.get("observations")),
        "suggestions": _as_str_list(data.get("suggestions")),
        "source": "claude_api",
    }


def _fallback_trend(stats_data: dict) -> dict[str, Any]:
    """API キー未設定時のローカル簡易分析。"""
    tasks = stats_data.get("tasks") or {}
    rate = tasks.get("completion_rate", 0.0)
    entry_count = stats_data.get("entry_count", 0)
    top_tag = (stats_data.get("top_tags") or [("(なし)", 0)])[0]
    top_cat = (stats_data.get("top_categories") or [("(なし)", 0)])[0]
    monthly = stats_data.get("monthly") or {}

    observations = []
    if entry_count:
        observations.append(f"エントリ {entry_count} 件が蓄積されている")
    observations.append(
        f"タスク完了率は {rate * 100:.0f}%（done {tasks.get('done', 0)} / "
        f"total {tasks.get('total', 0)}）"
    )
    if top_tag[1] > 0:
        observations.append(f"最も多いタグは `{top_tag[0]}`（{top_tag[1]}回）")
    if top_cat[1] > 0:
        observations.append(f"最も多いカテゴリは `{top_cat[0]}`（{top_cat[1]}回）")
    if len(monthly) >= 2:
        items = list(monthly.items())
        prev, curr = items[-2], items[-1]
        diff = curr[1]["entries"] - prev[1]["entries"]
        arrow = "増加" if diff > 0 else ("減少" if diff < 0 else "横ばい")
        observations.append(
            f"{prev[0]}→{curr[0]} のエントリ数は {arrow}（{diff:+d} 件）"
        )

    suggestions = []
    if tasks.get("open", 0) > tasks.get("done", 0):
        suggestions.append("オープン中のタスクを棚卸しして完了・キャンセル判定を入れる")
    if rate < 0.5 and tasks.get("total", 0) > 0:
        suggestions.append("完了率が低めなのでタスクを小さく分割してみる")
    if entry_count < 7:
        suggestions.append("まずは1週間毎日1エントリ取り込んでベースラインを作る")

    return {
        "summary": (
            f"{entry_count} 件のエントリから俯瞰した簡易分析。"
            f"タスク完了率 {rate * 100:.0f}%、主要テーマは `{top_tag[0]}`。"
        ),
        "observations": observations,
        "suggestions": suggestions,
        "source": "fallback",
    }


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _load_all_entries() -> list[dict]:
    entries: list[dict] = []
    if not ENTRIES_DIR.exists():
        return entries
    for path in sorted(ENTRIES_DIR.glob("*.json")):
        try:
            entries.append(load_json(Path(path)))
        except Exception:  # noqa: BLE001
            continue
    return entries


def _top_n(counter: dict[str, int], n: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def _span(dates: list[str]) -> dict[str, str] | None:
    if not dates:
        return None
    return {"first": min(dates), "last": max(dates)}
