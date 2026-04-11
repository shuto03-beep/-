"""Plaud Web がエクスポートした Word (.docx) を解析する。"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import ParsedDoc

# 日付検出正規表現（YYYY-MM-DD / YYYY/MM/DD / YYYY年MM月DD日）
_DATE_RE = re.compile(
    r"(\d{4})\s*[-/年]\s*(\d{1,2})\s*[-/月]\s*(\d{1,2})"
)

# セクション見出し（要約 / 文字起こし / トランスクリプト 等）
_SUMMARY_HEADERS = ("要約", "サマリ", "まとめ", "Summary", "summary")
_TRANSCRIPT_HEADERS = (
    "文字起こし",
    "書き起こし",
    "トランスクリプト",
    "全文",
    "Transcript",
    "transcript",
)


def parse_docx(path: Path) -> ParsedDoc:
    """Word ファイルを ParsedDoc に変換する。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"docx not found: {path}")

    try:
        from docx import Document  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "python-docx が未インストールです: pip install python-docx"
        ) from e

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    raw_text = "\n".join(paragraphs)

    title = _extract_title(paragraphs, path)
    recorded_at = _extract_date(raw_text) or _fallback_mtime(path)
    summary, transcript = _split_sections(paragraphs)

    # セクションが検出できなかったら全文を transcript として扱う
    if not summary and not transcript:
        transcript = raw_text

    return ParsedDoc(
        title=title,
        recorded_at=recorded_at,
        transcript=transcript,
        summary=summary,
        raw_text=raw_text,
        source_file=str(path),
    )


def _extract_title(paragraphs: list[str], path: Path) -> str:
    for p in paragraphs:
        # 行頭の日付（と直後の区切り）を除去してからタイトル候補にする
        stripped = _DATE_RE.sub("", p, count=1).strip(" \u3000-:：")
        if not stripped:
            continue
        if 2 <= len(stripped) <= 80:
            return stripped
    return path.stem


def _extract_date(text: str) -> Optional[datetime]:
    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        y, mo, d = (int(x) for x in m.groups())
        return datetime(y, mo, d)
    except ValueError:
        return None


def _fallback_mtime(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime)


def _is_header(line: str, keywords: tuple[str, ...]) -> bool:
    stripped = line.strip().lstrip("#").strip().rstrip(":：").strip()
    return any(stripped == kw or stripped.startswith(kw) for kw in keywords)


def _split_sections(paragraphs: list[str]) -> tuple[str, str]:
    """要約セクションと文字起こしセクションを分離する。"""
    summary_lines: list[str] = []
    transcript_lines: list[str] = []
    current: Optional[str] = None

    for line in paragraphs:
        if _is_header(line, _SUMMARY_HEADERS):
            current = "summary"
            continue
        if _is_header(line, _TRANSCRIPT_HEADERS):
            current = "transcript"
            continue

        if current == "summary":
            summary_lines.append(line)
        elif current == "transcript":
            transcript_lines.append(line)

    return "\n".join(summary_lines).strip(), "\n".join(transcript_lines).strip()
