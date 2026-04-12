"""Plaud Web API クライアント（非公式）。

web.plaud.ai のリバースエンジニアリング API を使って、
録音・文字起こし・AI 要約をプログラムから取得する。

認証には Plaud Web のブラウザから取得した Bearer トークンを使用する。
取得方法:
  1. https://web.plaud.ai にログイン
  2. F12（DevTools）→ Console タブ
  3. localStorage.getItem("tokenstr") を実行
  4. 表示された "bearer eyJ..." をコピー
"""
import json
import os
from datetime import datetime
from typing import Any

import requests

# API ドメイン（リージョンによって異なる）
# US: api-usw2.plaud.ai / EU: api-euc1.plaud.ai / Asia: api-apne1.plaud.ai
_DEFAULT_API_DOMAIN = "https://api.plaud.ai"

# 取得するページサイズ
_PAGE_SIZE = 50


def _get_config() -> tuple[str, str]:
    """トークンと API ドメインを環境変数から取得する。"""
    token = os.environ.get("PLAUD_BEARER_TOKEN") or ""
    if not token:
        raise RuntimeError(
            "PLAUD_BEARER_TOKEN が未設定です。\n"
            "web.plaud.ai → F12 → Console → localStorage.getItem('tokenstr') "
            "で取得してください。"
        )
    # PLAUD_API_DOMAIN が未設定 or 空の場合はデフォルトを使う
    domain = os.environ.get("PLAUD_API_DOMAIN") or ""
    if not domain:
        domain = _DEFAULT_API_DOMAIN
    return token, domain


def _headers(token: str) -> dict[str, str]:
    """API リクエスト用のヘッダーを返す。"""
    auth = token if token.lower().startswith("bearer ") else f"bearer {token}"
    return {
        "Authorization": auth,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get(url: str, token: str, params: dict | None = None) -> dict:
    resp = requests.get(url, headers=_headers(token), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ---------- 公開 API ----------


def list_recordings(limit: int = _PAGE_SIZE) -> list[dict]:
    """最新の録音一覧を取得する。

    戻り値は [{id, name, duration, created_at, status, ...}, ...] のリスト。
    """
    token, domain = _get_config()
    # 非公式 API: /file/simple/web がファイル一覧
    url = f"{domain}/file/simple/web"
    data = _get(url, token, params={"pageSize": limit, "page": 1})
    # レスポンス構造: {data: {list: [...], ...}} or {data: [...]}
    inner = data.get("data") or data
    if isinstance(inner, dict):
        files = inner.get("list") or inner.get("items") or inner.get("records") or []
    elif isinstance(inner, list):
        files = inner
    else:
        files = []
    return files


def get_recording_detail(file_id: str) -> dict:
    """1 件の録音の詳細（メタデータ + 文字起こし + 要約）を取得する。"""
    token, domain = _get_config()
    # 非公式 API: /file/detail/{file_id}
    url = f"{domain}/file/detail/{file_id}"
    data = _get(url, token)
    return data.get("data") or data


def get_transcript(file_id: str) -> str:
    """文字起こしテキストを取得する。"""
    detail = get_recording_detail(file_id)
    # API レスポンスの構造はバージョンによって異なる可能性がある
    trans = detail.get("trans_result") or detail.get("transcript") or ""
    if isinstance(trans, list):
        # [{speaker, text, start, end}, ...] 形式
        return "\n".join(
            f"{seg.get('speaker', '')}: {seg.get('text', '')}"
            if seg.get("speaker")
            else seg.get("text", "")
            for seg in trans
        )
    if isinstance(trans, dict):
        return trans.get("text") or json.dumps(trans, ensure_ascii=False)
    return str(trans)


def get_summary(file_id: str) -> str:
    """AI 要約テキストを取得する。"""
    detail = get_recording_detail(file_id)
    summary = (
        detail.get("ai_summary")
        or detail.get("summary")
        or detail.get("note")
        or ""
    )
    if isinstance(summary, dict):
        return summary.get("text") or summary.get("content") or json.dumps(summary, ensure_ascii=False)
    return str(summary)


def get_recording_title(detail: dict) -> str:
    """録音のタイトルを取得する。"""
    return (
        detail.get("name")
        or detail.get("title")
        or detail.get("file_name")
        or "(無題)"
    )


def get_recording_date(detail: dict) -> datetime:
    """録音の日時を取得する。"""
    for key in ("created_at", "create_time", "record_time", "timestamp"):
        val = detail.get(key)
        if not val:
            continue
        if isinstance(val, (int, float)):
            # Unix timestamp (秒 or ミリ秒)
            ts = val if val < 1e12 else val / 1000
            return datetime.fromtimestamp(ts)
        if isinstance(val, str):
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    return datetime.strptime(val[:19], fmt)
                except ValueError:
                    continue
    return datetime.now()
