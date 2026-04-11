"""Discord webhook 通知（レポート・日次ダイジェスト用）。

既存の /notifications.py と同じパターン（requests.post + 1990 文字分割 +
webhook 未設定時のフォールバック）を採用する。
"""
import os
from typing import Any


_CHUNK_SIZE = 1990
_TIMEOUT = 10


def send_text(message: str, webhook_url: str | None = None) -> dict[str, Any]:
    """任意のテキストを Discord に送る。

    - `webhook_url` が None の場合は `PLAUD_DISCORD_WEBHOOK_URL` 環境変数を参照
    - どちらも未設定ならコンソールに出力して `{"sent": False, "reason": "no_webhook"}` を返す
    - 1990 文字ごとにチャンク分割して順に POST
    """
    url = webhook_url or os.environ.get("PLAUD_DISCORD_WEBHOOK_URL")
    if not url:
        print("[notifier] Webhook 未設定。コンソール出力:")
        print(message)
        return {"sent": False, "reason": "no_webhook", "chunks": 0}

    try:
        import requests  # type: ignore
    except ImportError:
        print("[notifier] requests 未インストール。pip install requests")
        return {"sent": False, "reason": "no_requests", "chunks": 0}

    url = url.replace("https://discordapp.com/", "https://discord.com/")
    chunks = [message[i:i + _CHUNK_SIZE] for i in range(0, len(message), _CHUNK_SIZE)] or [""]
    sent = 0
    errors: list[str] = []
    for chunk in chunks:
        try:
            resp = requests.post(url, json={"content": chunk}, timeout=_TIMEOUT)
            resp.raise_for_status()
            sent += 1
        except Exception as e:  # noqa: BLE001
            errors.append(str(e))
            break
    return {
        "sent": sent > 0,
        "reason": "ok" if sent == len(chunks) else ("partial" if sent else "error"),
        "chunks": sent,
        "total_chunks": len(chunks),
        "errors": errors,
    }


def format_report(report: dict) -> str:
    """report dict を Discord 投稿用のプレーンテキストに整形する。"""
    narrative = report.get("narrative") or {}
    tasks = report.get("tasks") or {}
    headlines = report.get("headlines") or []
    top_tags = report.get("top_tags") or []

    lines: list[str] = []
    lines.append(
        f"**📓 plaud-lifelog 振り返り** `{report.get('period', '')}`"
    )
    lines.append(
        f"期間: {report.get('start', '')} 〜 {report.get('end', '')}  /  "
        f"エントリ: {report.get('entry_count', 0)} 件"
    )
    lines.append("")

    summary = narrative.get("summary") or ""
    if summary:
        lines.append("**サマリー**")
        lines.append(summary)
        lines.append("")

    highlights = narrative.get("highlights") or []
    if highlights:
        lines.append("**ハイライト**")
        for h in highlights[:6]:
            lines.append(f"• {h}")
        lines.append("")

    next_focus = narrative.get("next_focus") or []
    if next_focus:
        lines.append("**次の注力テーマ**")
        for n in next_focus[:5]:
            lines.append(f"• {n}")
        lines.append("")

    if top_tags:
        tag_str = "  ".join(f"`{t}×{c}`" for t, c in top_tags[:6])
        lines.append(f"**タグ**: {tag_str}")

    if tasks.get("total"):
        lines.append(
            f"**タスク**: open {tasks.get('open', 0)} / done {tasks.get('done', 0)} "
            f"(全{tasks.get('total', 0)}件)"
        )
        open_list = tasks.get("open_list") or []
        if open_list:
            lines.append("**オープンタスク（優先度順）**")
            for t in open_list[:5]:
                due = t.get("due") or "-"
                lines.append(
                    f"• [{t.get('priority', 'medium')}] "
                    f"{t.get('title', '')} _(期限: {due})_"
                )

    if headlines and not narrative.get("highlights"):
        lines.append("")
        lines.append("**エントリ**")
        for h in headlines[:8]:
            lines.append(
                f"• {h.get('date', '')}  {h.get('headline') or h.get('title', '')}"
            )

    return "\n".join(lines).rstrip()
