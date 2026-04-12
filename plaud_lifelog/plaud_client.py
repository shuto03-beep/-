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
_API_DOMAINS = [
    "https://api-apne1.plaud.ai",  # Asia Pacific (Japan)
    "https://api-euc1.plaud.ai",   # EU
    "https://api-usw2.plaud.ai",   # US West
    "https://api.plaud.ai",        # Generic
]

# 取得するページサイズ
_PAGE_SIZE = 50


_resolved_domain: str | None = None  # 一度見つけたらキャッシュ


def _get_config() -> tuple[str, str]:
    """トークンと API ドメインを環境変数から取得する。"""
    token = os.environ.get("PLAUD_BEARER_TOKEN") or ""
    if not token:
        raise RuntimeError(
            "PLAUD_BEARER_TOKEN が未設定です。\n"
            "web.plaud.ai → F12 → Console → localStorage.getItem('tokenstr') "
            "で取得してください。"
        )
    # 明示指定がある場合はそれを使う
    domain = os.environ.get("PLAUD_API_DOMAIN") or ""
    if domain:
        return token, domain
    # 自動検出: 複数のリージョンを試して最初に成功したものを使う
    global _resolved_domain
    if _resolved_domain:
        return token, _resolved_domain
    _resolved_domain = _auto_detect_domain(token)
    return token, _resolved_domain


def _auto_detect_domain(token: str) -> str:
    """複数の API ドメインを試して正しいリージョンを自動検出する。

    - 200 → 成功。このドメインを使う。
    - 401/403 → エンドポイントは存在するがトークンに問題。
      ドメイン自体は正しい可能性が高いので候補に入れる。
    - 404 → エンドポイントが存在しない。スキップ。
    """
    auth_domains: list[str] = []  # 401/403 を返したドメイン

    for domain in _API_DOMAINS:
        try:
            url = f"{domain}/file/simple/web"
            resp = requests.get(
                url,
                headers=_headers(token),
                params={"pageSize": 1, "page": 1},
                timeout=10,
            )
            print(f"  [plaud] trying {domain} -> {resp.status_code}")
            if resp.status_code == 200:
                print(f"  [plaud] API domain OK: {domain}")
                return domain
            if resp.status_code in (401, 403):
                auth_domains.append(domain)
        except requests.RequestException as e:
            print(f"  [plaud] trying {domain} -> error: {e}")
            continue

    # 401/403 を返したドメインがあればそれを使う（エンドポイントは正しい）
    if auth_domains:
        print(f"  [plaud] using domain (auth issue): {auth_domains[0]}")
        return auth_domains[0]

    print(f"  [plaud] auto-detect failed, trying {_API_DOMAINS[0]}")
    return _API_DOMAINS[0]


def _headers(token: str) -> dict[str, str]:
    """API リクエスト用のヘッダーを返す。"""
    # トークンのクォートを除去（localStorage から取得時に引用符が含まれることがある）
    clean = token.strip().strip("'\"")
    auth = clean if clean.lower().startswith("bearer ") else f"Bearer {clean}"
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

    # デバッグ: レスポンス構造を出力して正しいキーを特定する
    if isinstance(data, dict):
        print(f"  [plaud] response keys: {list(data.keys())}")
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"  [plaud]   {k}: dict with keys {list(v.keys())}")
            elif isinstance(v, list):
                print(f"  [plaud]   {k}: list of {len(v)} items")
                if v:
                    first = v[0]
                    if isinstance(first, dict):
                        print(f"  [plaud]   {k}[0] keys: {list(first.keys())}")
            else:
                print(f"  [plaud]   {k}: {type(v).__name__} = {str(v)[:80]}")

    # レスポンス構造を柔軟にパース
    files = _extract_file_list(data)
    print(f"  [plaud] parsed {len(files)} recordings")
    return files


def _extract_file_list(data: Any) -> list[dict]:
    """API レスポンスから録音リストを柔軟に抽出する。"""
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    # 直接キーを探す（data_file_list が Plaud の実際のキー）
    for key in ("data_file_list", "list", "items", "records", "files", "data"):
        val = data.get(key)
        if isinstance(val, list) and val:
            return val
        if isinstance(val, dict):
            inner = _extract_file_list(val)
            if inner:
                return inner

    return []


def get_recording_detail(file_id: str) -> dict:
    """1 件の録音の詳細（メタデータ + 文字起こし + 要約）を取得する。"""
    token, domain = _get_config()
    url = f"{domain}/file/detail/{file_id}"
    data = _get(url, token)
    inner = data.get("data") or data

    # デバッグ: レスポンスの全キーと値の型・サイズを出力
    if isinstance(inner, dict):
        print(f"  [plaud-detail] ALL keys ({len(inner)}):")
        for key in sorted(inner.keys()):
            val = inner[key]
            if val is None:
                print(f"    {key}: null")
            elif isinstance(val, str):
                print(f"    {key}: str({len(val)}) = {val[:100]!r}")
            elif isinstance(val, (int, float)):
                print(f"    {key}: {type(val).__name__} = {val}")
            elif isinstance(val, list):
                print(f"    {key}: list({len(val)})")
                if val and isinstance(val[0], dict):
                    print(f"      [0] keys: {list(val[0].keys())[:10]}")
                    first_item = val[0]
                    for k2, v2 in list(first_item.items())[:5]:
                        if isinstance(v2, str):
                            print(f"      [0].{k2}: str({len(v2)}) = {v2[:80]!r}")
                        else:
                            print(f"      [0].{k2}: {type(v2).__name__} = {str(v2)[:80]}")
            elif isinstance(val, dict):
                print(f"    {key}: dict keys={list(val.keys())[:10]}")
                for k2, v2 in list(val.items())[:5]:
                    if isinstance(v2, str):
                        print(f"      .{k2}: str({len(v2)}) = {v2[:80]!r}")

    return inner


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
        detail.get("filename")
        or detail.get("name")
        or detail.get("title")
        or detail.get("file_name")
        or "(無題)"
    )


def get_recording_date(detail: dict) -> datetime:
    """録音の日時を取得する。"""
    for key in ("start_time", "created_at", "create_time", "record_time", "timestamp"):
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
