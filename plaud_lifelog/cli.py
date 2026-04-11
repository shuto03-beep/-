"""plaud-lifelog CLI エントリーポイント。"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from .ai_processor import extract_tasks, generate_lifelog
from .config import AI_ENABLED, AI_MODEL
from .docx_parser import parse_docx
from .storage import build_entry_id, list_entries, list_open_tasks, load_entry, save_entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plaud_lifelog",
        description="Plaud Web の Word 出力をライフログ + タスク分析に変換します",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Word ファイルを取り込む")
    p_ingest.add_argument("path", type=Path, help=".docx ファイルのパス")
    p_ingest.add_argument("--dry-run", action="store_true", help="保存せずに結果を表示するだけ")

    p_list = sub.add_parser("list", help="タイムラインを表示する")
    p_list.add_argument("--limit", type=int, default=20)

    p_tasks = sub.add_parser("tasks", help="オープンタスクを表示する")
    p_tasks.add_argument("--all", action="store_true", help="完了済みも含めて表示")

    p_show = sub.add_parser("show", help="指定エントリの詳細を表示する")
    p_show.add_argument("entry_id", help="エントリID (例: 2026-04-11_asa-kai)")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        return cmd_ingest(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "tasks":
        return cmd_tasks(args)
    if args.command == "show":
        return cmd_show(args)

    parser.print_help()
    return 1


# ---------- サブコマンド ----------

def cmd_ingest(args) -> int:
    path: Path = args.path
    if not path.exists():
        print(f"[error] ファイルが見つかりません: {path}", file=sys.stderr)
        return 2

    print(f"[1/3] パース: {path}")
    parsed = parse_docx(path)
    print(f"      title={parsed.title!r}")
    print(f"      recorded_at={parsed.recorded_at.date().isoformat()}")
    print(f"      summary={_truncate(parsed.summary)}")
    print(f"      transcript_chars={len(parsed.transcript)}")

    print(f"[2/3] AI 処理 (model={AI_MODEL}, enabled={AI_ENABLED})")
    lifelog = generate_lifelog(parsed)
    task_result = extract_tasks(parsed)
    tasks = _attach_task_ids(task_result["tasks"], parsed.recorded_at)

    entry_id = build_entry_id(parsed.recorded_at, parsed.title)
    for i, t in enumerate(tasks):
        t["id"] = f"t_{parsed.recorded_at.strftime('%Y%m%d')}_{i+1:02d}"
        t["status"] = "open"
        t["source_entry_id"] = entry_id

    task_analysis = _summarize_task_analysis(tasks, task_result.get("analysis", {}))

    entry = {
        "id": entry_id,
        "source_file": str(path),
        "recorded_at": parsed.recorded_at.isoformat(),
        "ingested_at": datetime.now().isoformat(timespec="seconds"),
        "title": parsed.title,
        "raw": {
            "transcript": parsed.transcript,
            "summary": parsed.summary,
        },
        "lifelog": lifelog,
        "tasks": tasks,
        "task_analysis": task_analysis,
    }

    if args.dry_run:
        print("[3/3] --dry-run のため保存しません。結果プレビュー:")
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0

    print("[3/3] 保存")
    saved_path = save_entry(entry)
    print(f"      -> {saved_path}")
    print()
    print("=== Lifelog ===")
    print(f"  headline : {lifelog.get('headline', '')}")
    print(f"  narrative: {lifelog.get('narrative', '')}")
    print(f"  tags     : {', '.join(lifelog.get('tags', []))}")
    print(f"  mood     : {lifelog.get('mood', '')}")
    print()
    print(f"=== Tasks ({len(tasks)}) ===")
    for t in tasks:
        due = t.get("due") or "-"
        print(f"  [{t['priority']:<6}] {t['title']}  (due={due}, cat={t.get('category') or '-'})")
    print()
    print(f"effort_summary: {task_analysis.get('effort_summary', '')}")
    return 0


def cmd_list(args) -> int:
    entries = list_entries(limit=args.limit)
    if not entries:
        print("(エントリがまだありません)")
        return 0
    print(f"{'日付':<12} {'ID':<40} {'タスク':>4}  見出し")
    print("-" * 90)
    for e in entries:
        date = (e.get("recorded_at") or "")[:10]
        print(
            f"{date:<12} {e['id']:<40} {e.get('task_count', 0):>4}  "
            f"{e.get('headline') or e.get('title', '')}"
        )
    return 0


def cmd_tasks(args) -> int:
    tasks = list_open_tasks(include_done=args.all)
    if not tasks:
        print("(オープンタスクはありません)")
        return 0
    print(f"{'優先度':<8} {'期限':<12} {'カテゴリ':<10} タスク")
    print("-" * 80)
    for t in tasks:
        print(
            f"{t.get('priority', 'medium'):<8} "
            f"{(t.get('due') or '-'):<12} "
            f"{(t.get('category') or '-'):<10} "
            f"{t.get('title', '')}"
        )
    return 0


def cmd_show(args) -> int:
    try:
        entry = load_entry(args.entry_id)
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


# ---------- 補助関数 ----------

def _truncate(s: str, n: int = 80) -> str:
    s = s.replace("\n", " ")
    return s[:n] + ("…" if len(s) > n else "")


def _attach_task_ids(tasks: list[dict], recorded_at: datetime) -> list[dict]:
    return [dict(t) for t in tasks]


def _summarize_task_analysis(tasks: list[dict], analysis: dict) -> dict:
    by_priority = {"high": 0, "medium": 0, "low": 0}
    for t in tasks:
        p = t.get("priority", "medium")
        by_priority[p] = by_priority.get(p, 0) + 1
    return {
        "total": len(tasks),
        "by_priority": by_priority,
        "effort_summary": analysis.get("effort_summary", ""),
        "blockers": analysis.get("blockers", []),
    }


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
