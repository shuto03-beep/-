"""Notion API でライフログエントリを自動追加する。"""
import json
import os
from typing import Any

import requests

_NOTION_VERSION = "2022-06-28"
_NOTION_API = "https://api.notion.com/v1"


def _get_notion_config() -> tuple[str, str]:
    """Notion API トークンとデータベースIDを取得する。"""
    token = os.environ.get("NOTION_API_TOKEN") or ""
    db_id = os.environ.get("NOTION_DATABASE_ID") or ""
    if not token:
        raise RuntimeError("NOTION_API_TOKEN が未設定です")
    if not db_id:
        raise RuntimeError("NOTION_DATABASE_ID が未設定です")
    return token, db_id


def _notion_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": _NOTION_VERSION,
    }


def push_entry_to_notion(entry: dict) -> dict | None:
    """エントリを Notion データベースに追加する。

    既に同じエントリIDが存在する場合はスキップ（重複防止）。
    """
    try:
        token, db_id = _get_notion_config()
    except RuntimeError:
        return None

    lifelog = entry.get("lifelog") or {}
    tasks = entry.get("tasks") or []
    recorded_at = (entry.get("recorded_at") or "")[:10]

    # Notion ページのプロパティ
    properties: dict[str, Any] = {
        "タイトル": {"title": [{"text": {"content": entry.get("title", "(無題)")}}]},
        "日付": {"date": {"start": recorded_at}} if recorded_at else {},
        "見出し": {"rich_text": [{"text": {"content": str(lifelog.get("headline", ""))[:2000]}}]},
        "ナラティブ": {"rich_text": [{"text": {"content": str(lifelog.get("narrative", ""))[:2000]}}]},
        "人物": {"rich_text": [{"text": {"content": ", ".join(lifelog.get("people") or [])}}]},
        "タスク数": {"number": len(tasks)},
        "エントリID": {"rich_text": [{"text": {"content": entry.get("id", "")}}]},
    }

    # 気分（select）
    mood = lifelog.get("mood") or ""
    if mood:
        properties["気分"] = {"select": {"name": mood}}

    # タグ（multi_select）
    tags = lifelog.get("tags") or []
    if tags:
        properties["タグ"] = {"multi_select": [{"name": t} for t in tags[:10]]}

    # ソース（select）
    source = lifelog.get("source") or "fallback"
    properties["ソース"] = {"select": {"name": source}}

    # ページ本文（キーポイント + タスク + メモ）
    content_parts = []
    key_points = lifelog.get("key_points") or []
    if key_points:
        content_parts.append("## キーポイント")
        for k in key_points:
            content_parts.append(f"- {k}")

    if tasks:
        content_parts.append(f"\n## タスク ({len(tasks)})")
        for t in tasks:
            mark = "x" if t.get("status") == "done" else " "
            pri = t.get("priority", "medium")
            due = t.get("due") or "-"
            content_parts.append(f"- [{mark}] **[{pri}]** {t.get('title', '')} (期限: {due})")

    notes = entry.get("notes") or []
    if notes:
        content_parts.append("\n## メモ")
        for n in notes:
            content_parts.append(f"- {n.get('text', '')}")

    # Notion API でページ作成
    body = {
        "parent": {"database_id": db_id},
        "icon": {"emoji": "📓"},
        "properties": properties,
    }

    # 本文をブロックとして追加（シンプルなパラグラフ）
    if content_parts:
        content = "\n".join(content_parts)
        body["children"] = _text_to_blocks(content)

    try:
        resp = requests.post(
            f"{_NOTION_API}/pages",
            headers=_notion_headers(token),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        return {"id": result.get("id"), "url": result.get("url")}
    except Exception as e:
        print(f"  [notion] 追加失敗: {e}")
        return None


def _text_to_blocks(text: str) -> list[dict]:
    """テキストを Notion のブロック配列に変換する。"""
    blocks = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        if line.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                },
            })
        elif line.startswith("- ["):
            checked = line[3] == "x"
            content = line[6:] if checked else line[5:]
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": content.strip()}}],
                    "checked": checked,
                },
            })
        elif line.startswith("- "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                },
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line}}]
                },
            })
    return blocks
