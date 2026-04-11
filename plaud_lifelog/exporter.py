"""エントリ / レポートを Markdown にレンダリングする。"""
from typing import Iterable


def entry_to_markdown(entry: dict) -> str:
    """1 エントリを読み返し用の Markdown に整形する。"""
    lifelog = entry.get("lifelog") or {}
    raw = entry.get("raw") or {}
    tasks = entry.get("tasks") or []
    analysis = entry.get("task_analysis") or {}

    lines: list[str] = []
    title = entry.get("title", "(無題)")
    date = (entry.get("recorded_at") or "")[:10]
    lines.append(f"# {title}")
    lines.append("")

    # メタ情報
    meta_bits = [f"**日付**: {date}"]
    if lifelog.get("mood"):
        meta_bits.append(f"**気分**: {lifelog['mood']}")
    if lifelog.get("tags"):
        meta_bits.append(f"**タグ**: {', '.join(lifelog['tags'])}")
    if lifelog.get("people"):
        meta_bits.append(f"**人物**: {', '.join(lifelog['people'])}")
    if lifelog.get("locations"):
        meta_bits.append(f"**場所**: {', '.join(lifelog['locations'])}")
    lines.append(" / ".join(meta_bits))
    lines.append("")

    # ライフログ本文
    headline = lifelog.get("headline")
    if headline:
        lines.append(f"## {headline}")
        lines.append("")
    narrative = lifelog.get("narrative")
    if narrative:
        lines.append(narrative)
        lines.append("")

    # キーポイント
    key_points = lifelog.get("key_points") or []
    if key_points:
        lines.append("### キーポイント")
        for k in key_points:
            lines.append(f"- {k}")
        lines.append("")

    # 手書きメモ
    notes = entry.get("notes") or []
    if notes:
        lines.append("### メモ")
        for n in notes:
            created = (n.get("created_at") or "")[:10]
            lines.append(f"- {n.get('text', '')}  _(追記: {created})_")
        lines.append("")

    # タスク
    if tasks:
        lines.append(f"### タスク ({len(tasks)})")
        for t in tasks:
            mark = "x" if t.get("status") == "done" else " "
            pri = t.get("priority", "medium")
            due = t.get("due") or "-"
            cat = t.get("category") or "-"
            lines.append(
                f"- [{mark}] **[{pri}]** {t.get('title', '')}  "
                f"(期限: {due} / {cat})"
            )
        lines.append("")
        if analysis.get("effort_summary"):
            lines.append(f"> {analysis['effort_summary']}")
            lines.append("")

    # 原文（要約 / 文字起こし）
    if raw.get("summary"):
        lines.append("### 要約（Plaud 原文）")
        lines.append(raw["summary"])
        lines.append("")
    if raw.get("transcript"):
        lines.append("### 文字起こし")
        lines.append("```")
        lines.append(raw["transcript"])
        lines.append("```")
        lines.append("")

    _append_footer(lines, entry)
    return "\n".join(lines).rstrip() + "\n"


def report_to_markdown(report: dict) -> str:
    """期間レポートを Markdown に整形する。"""
    narrative = report.get("narrative") or {}
    tasks = report.get("tasks") or {}

    lines: list[str] = []
    lines.append(f"# 振り返り {report.get('period', '')}")
    lines.append("")
    lines.append(
        f"**期間**: {report.get('start', '')} 〜 {report.get('end', '')}  "
        f"/ **エントリ数**: {report.get('entry_count', 0)}"
    )
    lines.append("")

    if narrative.get("summary"):
        lines.append("## サマリー")
        lines.append(narrative["summary"])
        lines.append("")

    highlights = narrative.get("highlights") or []
    if highlights:
        lines.append("## ハイライト")
        for h in highlights:
            lines.append(f"- {h}")
        lines.append("")

    next_focus = narrative.get("next_focus") or []
    if next_focus:
        lines.append("## 次の注力テーマ")
        for n in next_focus:
            lines.append(f"- {n}")
        lines.append("")

    top_tags = report.get("top_tags") or []
    if top_tags:
        lines.append("## タグ集計")
        for tag, count in top_tags:
            lines.append(f"- `{tag}` × {count}")
        lines.append("")

    headlines = report.get("headlines") or []
    if headlines:
        lines.append("## エントリ一覧")
        for h in headlines:
            lines.append(
                f"- {h.get('date', '')} — **{h.get('headline') or h.get('title', '')}** "
                f"(`{h.get('id', '')}`)"
            )
        lines.append("")

    if tasks.get("total"):
        lines.append("## タスクサマリー")
        lines.append(
            f"- 全{tasks.get('total', 0)}件 / open {tasks.get('open', 0)} / "
            f"done {tasks.get('done', 0)}"
        )
        by_pri = tasks.get("by_priority") or {}
        lines.append(
            f"- 優先度（open）: high {by_pri.get('high', 0)} / "
            f"medium {by_pri.get('medium', 0)} / low {by_pri.get('low', 0)}"
        )
        open_list = tasks.get("open_list") or []
        if open_list:
            lines.append("")
            lines.append("### オープンタスク")
            for t in open_list:
                due = t.get("due") or "-"
                lines.append(
                    f"- [ ] **[{t.get('priority', 'medium')}]** "
                    f"{t.get('title', '')}  (期限: {due})"
                )
        lines.append("")

    lines.append("---")
    lines.append(f"_generated: {report.get('generated_at', '')} / source: {narrative.get('source', 'unknown')}_")
    return "\n".join(lines).rstrip() + "\n"


def _append_footer(lines: list, entry: dict) -> None:
    lines.append("---")
    source = (entry.get("lifelog") or {}).get("source", "unknown")
    lines.append(
        f"_id: `{entry.get('id', '')}` / source: {source} / "
        f"ingested: {entry.get('ingested_at', '')}_"
    )
