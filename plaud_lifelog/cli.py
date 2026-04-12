"""plaud-lifelog CLI エントリーポイント。"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from . import __version__
from .ai_processor import extract_tasks, generate_lifelog
from .config import AI_ENABLED, AI_MODEL
from .docx_parser import parse_docx
from .exporter import entry_to_markdown, report_to_markdown
from .notifier import format_report, send_text
from .plaud_client import (
    get_recording_date,
    get_recording_detail,
    get_recording_title,
    get_summary,
    get_transcript,
    list_recordings,
)
from .report_generator import build_report
from .stats import compute_stats, generate_trend_analysis
from .storage import (
    append_note,
    build_entry_id,
    delete_entry,
    iter_entries_in_range,
    list_entries,
    list_open_tasks,
    load_entry,
    load_report,
    reindex,
    save_entry,
    save_report,
    search_entries,
    update_task_status,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="plaud_lifelog",
        description="Plaud Web の Word 出力をライフログ + タスク分析に変換します",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Word ファイル/フォルダを取り込む")
    p_ingest.add_argument("path", type=Path, help=".docx ファイル or フォルダのパス")
    p_ingest.add_argument("--dry-run", action="store_true", help="保存せずに結果を表示するだけ")
    p_ingest.add_argument("--force", action="store_true", help="既存IDも上書きして再取り込み")
    p_ingest.add_argument(
        "--recursive", "-r", action="store_true",
        help="フォルダ指定時にサブフォルダも再帰走査する",
    )

    p_list = sub.add_parser("list", help="タイムラインを表示する")
    p_list.add_argument("--limit", type=int, default=20)

    p_tasks = sub.add_parser("tasks", help="オープンタスクを表示する")
    p_tasks.add_argument("--all", action="store_true", help="完了済みも含めて表示")

    p_show = sub.add_parser("show", help="指定エントリの詳細を表示する")
    p_show.add_argument("entry_id", help="エントリID (例: 2026-04-11_asa-kai)")

    p_mark = sub.add_parser("mark", help="タスクの done/open を切り替える")
    p_mark.add_argument("task_id", help="タスクID (例: t_20260411_01)")
    group = p_mark.add_mutually_exclusive_group()
    group.add_argument("--done", dest="status", action="store_const", const="done")
    group.add_argument("--open", dest="status", action="store_const", const="open")
    p_mark.set_defaults(status="done")

    p_report = sub.add_parser("report", help="期間ライフログ振り返りを生成する")
    p_report.add_argument("--days", type=int, default=7, help="直近 N 日（デフォルト 7）")
    p_report.add_argument("--from", dest="date_from", help="開始日 YYYY-MM-DD")
    p_report.add_argument("--to", dest="date_to", help="終了日 YYYY-MM-DD (含む)")
    p_report.add_argument("--month", help="対象月 YYYY-MM（月初〜月末を自動範囲設定）")
    p_report.add_argument("--dry-run", action="store_true", help="保存せずに結果を表示")
    p_report.add_argument(
        "--notify", action="store_true",
        help="Discord webhook (PLAUD_DISCORD_WEBHOOK_URL) に投稿する",
    )

    p_search = sub.add_parser("search", help="全エントリを全文検索する")
    p_search.add_argument("keyword", help="検索キーワード")
    p_search.add_argument("--limit", type=int, default=20)

    p_export = sub.add_parser("export", help="エントリ/レポートを Markdown で出力する")
    g_target = p_export.add_mutually_exclusive_group(required=True)
    g_target.add_argument("--entry", help="エントリID (例: 2026-04-11_asa-kai)")
    g_target.add_argument("--report", dest="report_id", help="レポート period (例: 2026-04-05_to_2026-04-11)")
    g_target.add_argument("--all", action="store_true", help="全エントリを Markdown でフォルダに書き出す")
    p_export.add_argument("-o", "--output", type=Path, help="出力先 (--all の場合はディレクトリ、それ以外はファイル)")

    p_sync = sub.add_parser("sync", help="Plaud Web から新しい録音を自動取得してエントリ作成")
    p_sync.add_argument("--limit", type=int, default=50, help="API から取得する最大件数")
    p_sync.add_argument("--days", type=int, default=0, help="直近 N 日の録音だけ処理（0=全件）")
    p_sync.add_argument("--dry-run", action="store_true", help="取得だけして保存しない")

    p_reindex = sub.add_parser("reindex", help="entries/ を再走査して index.json と tasks.json を再構築")
    p_delete = sub.add_parser("delete", help="指定エントリを削除する")
    p_delete.add_argument("entry_id", help="削除するエントリID")
    p_delete.add_argument("--yes", "-y", action="store_true", help="確認プロンプトをスキップ")

    p_note = sub.add_parser("note", help="エントリに手書きメモを追記する")
    p_note.add_argument("entry_id", help="対象エントリID")
    p_note.add_argument("text", nargs="*", help="メモ本文（--stdin 指定時は不要）")
    p_note.add_argument("--stdin", action="store_true", help="標準入力からメモを読み込む")

    p_stats = sub.add_parser("stats", help="蓄積したライフログ全体の統計を表示する")
    p_stats.add_argument("--json", action="store_true", help="JSON 形式で出力する")
    p_stats.add_argument(
        "--analyze", action="store_true",
        help="Claude で傾向分析コメントを生成する（APIキー未設定時はフォールバック）",
    )

    args = parser.parse_args(argv)

    if args.command == "ingest":
        return cmd_ingest(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "tasks":
        return cmd_tasks(args)
    if args.command == "show":
        return cmd_show(args)
    if args.command == "mark":
        return cmd_mark(args)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "search":
        return cmd_search(args)
    if args.command == "export":
        return cmd_export(args)
    if args.command == "sync":
        return cmd_sync(args)
    if args.command == "reindex":
        return cmd_reindex(args)
    if args.command == "delete":
        return cmd_delete(args)
    if args.command == "note":
        return cmd_note(args)
    if args.command == "stats":
        return cmd_stats(args)

    parser.print_help()
    return 1


# ---------- サブコマンド ----------

def cmd_ingest(args) -> int:
    path: Path = args.path
    if not path.exists():
        print(f"[error] パスが見つかりません: {path}", file=sys.stderr)
        return 2

    if path.is_dir():
        return _ingest_directory(path, args)
    try:
        _ingest_single(path, args, verbose=True)
    except Exception as e:  # noqa: BLE001
        print(f"[error] {e}", file=sys.stderr)
        return 1
    return 0


def _ingest_directory(root: Path, args) -> int:
    pattern = "**/*.docx" if args.recursive else "*.docx"
    files = sorted(
        p for p in root.glob(pattern)
        if p.is_file() and not p.name.startswith("~$")
        and "processed" not in p.parts  # processed/ 配下はスキップ
    )
    if not files:
        print(f"[warn] {root} に .docx が見つかりません")
        return 0

    print(f"[bulk] {len(files)} 件を取り込みます (recursive={args.recursive})")
    processed_count = 0
    skipped = 0
    failed = 0
    ingested_files: list[Path] = []
    for i, f in enumerate(files, start=1):
        print(f"\n--- [{i}/{len(files)}] {f.name} ---")
        try:
            status = _ingest_single(f, args, verbose=False)
        except Exception as e:  # noqa: BLE001
            print(f"  [error] {e}")
            failed += 1
            continue
        if status == "skipped":
            skipped += 1
        else:
            processed_count += 1
            if status == "saved":
                ingested_files.append(f)

    # 成功した元ファイルを processed/ に移動（inbox 運用向け）
    if ingested_files and not args.dry_run:
        processed_dir = root / "processed"
        processed_dir.mkdir(exist_ok=True)
        for f in ingested_files:
            dest = processed_dir / f.name
            if f.exists() and not dest.exists():
                try:
                    f.rename(dest)
                except OSError:
                    pass

    print(
        f"\n[bulk] done: processed={processed_count} skipped={skipped} failed={failed}"
    )
    return 0 if failed == 0 else 1


def _ingest_single(path: Path, args, *, verbose: bool) -> str:
    parsed = parse_docx(path)
    entry_id = build_entry_id(parsed.recorded_at, parsed.title)

    # 既存スキップ（--force 未指定時）
    if not args.force and not args.dry_run:
        try:
            load_entry(entry_id)
            print(f"  [skip] 既存エントリあり: {entry_id} (--force で上書き)")
            return "skipped"
        except FileNotFoundError:
            pass

    if verbose:
        print(f"[1/3] パース: {path}")
    print(f"  title={parsed.title!r}")
    print(f"  recorded_at={parsed.recorded_at.date().isoformat()}")
    print(f"  summary={_truncate(parsed.summary)}")
    print(f"  transcript_chars={len(parsed.transcript)}")

    if verbose:
        print(f"[2/3] AI 処理 (model={AI_MODEL}, enabled={AI_ENABLED})")
    lifelog = generate_lifelog(parsed)
    task_result = extract_tasks(parsed)
    tasks = _attach_task_ids(task_result["tasks"], parsed.recorded_at)

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
        print("  [dry-run] 保存しません。プレビュー:")
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return "dry-run"

    if verbose:
        print("[3/3] 保存")
    saved_path = save_entry(entry)
    print(f"  saved -> {saved_path}")
    print(f"  tasks={len(tasks)}  tags={', '.join(lifelog.get('tags', []))}")
    return "saved"


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


def cmd_mark(args) -> int:
    try:
        task = update_task_status(args.task_id, args.status)
    except (KeyError, FileNotFoundError, ValueError) as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    print(
        f"{task['id']} -> {task['status']}  "
        f"({task.get('priority', 'medium')}) {task.get('title', '')}"
    )
    return 0


def cmd_report(args) -> int:
    try:
        start, end = _resolve_range(args)
    except ValueError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    print(
        f"[1/2] 期間 {start.date().isoformat()} 〜 "
        f"{(end - timedelta(days=1)).date().isoformat()} のエントリを収集"
    )
    entries = iter_entries_in_range(start, end)
    print(f"      -> {len(entries)} 件")

    print(f"[2/2] レポート生成 (model={AI_MODEL}, enabled={AI_ENABLED})")
    report = build_report(entries, start, end)

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.notify:
            result = send_text(format_report(report))
            print(f"[notify] {result}")
        return 0

    path = save_report(report)
    print(f"      -> {path}")
    print()
    print("=== Weekly Lifelog ===")
    print(f"  period : {report['period']}")
    print(f"  entries: {report['entry_count']}")
    if report["top_tags"]:
        tags_str = ", ".join(f"{t}({c})" for t, c in report["top_tags"])
        print(f"  tags   : {tags_str}")
    print()
    print("--- summary ---")
    print(report["narrative"]["summary"])
    if report["narrative"]["highlights"]:
        print()
        print("--- highlights ---")
        for h in report["narrative"]["highlights"]:
            print(f"  * {h}")
    if report["narrative"]["next_focus"]:
        print()
        print("--- next focus ---")
        for f in report["narrative"]["next_focus"]:
            print(f"  * {f}")
    open_count = report["tasks"]["open"]
    if open_count:
        print()
        print(f"--- open tasks ({open_count}) ---")
        for t in report["tasks"]["open_list"][:10]:
            due = t.get("due") or "-"
            print(
                f"  [{t.get('priority', 'medium'):<6}] {t.get('title', '')}  (due={due})"
            )

    if args.notify:
        print()
        print("[notify] Discord webhook に投稿中…")
        result = send_text(format_report(report))
        if result.get("sent"):
            print(f"[notify] 送信成功 ({result['chunks']}/{result['total_chunks']} chunks)")
        else:
            print(f"[notify] 未送信: reason={result.get('reason')} errors={result.get('errors', [])}")
    return 0


def cmd_search(args) -> int:
    hits = search_entries(args.keyword, limit=args.limit)
    if not hits:
        print(f"(キーワード {args.keyword!r} にヒットなし)")
        return 0
    print(f"{'日付':<12} {'ID':<40} {'フィールド':<10} スニペット")
    print("-" * 120)
    for h in hits:
        print(
            f"{h['date']:<12} {h['id']:<40} {h['field']:<10} {h['snippet']}"
        )
    return 0


def cmd_export(args) -> int:
    # 既知エントリID集合（@ref の最長マッチ照合用）
    known_ids = {e["id"] for e in list_entries()}

    if args.all:
        out_dir = args.output or Path("data/plaud/export_md")
        out_dir.mkdir(parents=True, exist_ok=True)
        entries = list_entries()
        if not entries:
            print("(エントリがありません)")
            return 0
        written = 0
        for meta in entries:
            entry_id = meta["id"]
            try:
                entry = load_entry(entry_id)
            except FileNotFoundError:
                continue
            md = entry_to_markdown(entry, known_ids=known_ids)
            (out_dir / f"{entry_id}.md").write_text(md, encoding="utf-8")
            written += 1
        print(f"wrote {written} files -> {out_dir}")
        return 0

    if args.entry:
        try:
            entry = load_entry(args.entry)
        except FileNotFoundError as e:
            print(f"[error] {e}", file=sys.stderr)
            return 2
        md = entry_to_markdown(entry, known_ids=known_ids)
    else:
        try:
            report = load_report(args.report_id)
        except FileNotFoundError as e:
            print(f"[error] {e}", file=sys.stderr)
            return 2
        md = report_to_markdown(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(md, encoding="utf-8")
        print(f"wrote: {args.output}")
    else:
        sys.stdout.write(md)
    return 0


def cmd_sync(args) -> int:
    """Plaud Web から新しい録音を取得し、エントリを自動作成する。"""
    try:
        recordings = list_recordings(limit=args.limit)
    except Exception as e:
        print(f"[error] Plaud Web への接続に失敗: {e}", file=sys.stderr)
        print(
            "  PLAUD_BEARER_TOKEN を設定してください。\n"
            "  取得方法: web.plaud.ai → F12 → Console → "
            "localStorage.getItem('tokenstr')",
            file=sys.stderr,
        )
        return 2

    if not recordings:
        print("[sync] 録音が見つかりません")
        return 0

    print(f"[sync] Plaud Web から {len(recordings)} 件の録音を取得")

    # 日付フィルタ: --days が指定されていれば直近 N 日のみ
    cutoff = None
    if args.days and args.days > 0:
        cutoff = datetime.now() - timedelta(days=args.days)
        print(f"[sync] {cutoff.date()} 以降の録音のみ処理")

    # 既存エントリの ID 集合（重複スキップ用）
    existing_ids = {e["id"] for e in list_entries()}

    created = 0
    skipped = 0
    date_skipped = 0
    for i, rec in enumerate(recordings, start=1):
        # リスト段階で日付フィルタ（API 詳細を取る前に判定）
        recorded_at = get_recording_date(rec)
        title = get_recording_title(rec)
        entry_id = build_entry_id(recorded_at, title)

        if cutoff and recorded_at < cutoff:
            date_skipped += 1
            continue

        if entry_id in existing_ids:
            skipped += 1
            continue

        file_id = rec.get("id") or rec.get("file_id") or ""
        try:
            detail = get_recording_detail(file_id)
        except Exception as e:
            print(f"  [{i}] error: {e}")
            continue

        title = get_recording_title(detail)
        recorded_at = get_recording_date(detail)
        entry_id = build_entry_id(recorded_at, title)

        print(f"  [{i}] {recorded_at.date()} {title}")

        transcript = get_transcript(file_id)
        summary = get_summary(file_id)

        # ParsedDoc 相当のデータを手動構築
        from .models import ParsedDoc

        parsed = ParsedDoc(
            title=title,
            recorded_at=recorded_at,
            transcript=transcript,
            summary=summary,
            raw_text=f"{summary}\n\n{transcript}",
            source_file=f"plaud-web:{file_id}",
        )

        print(f"       transcript={len(transcript)}字  summary={len(summary)}字")
        print(f"       AI 処理中...")

        lifelog = generate_lifelog(parsed)
        task_result = extract_tasks(parsed)
        tasks = [dict(t) for t in task_result.get("tasks", [])]

        for j, t in enumerate(tasks):
            t["id"] = f"t_{recorded_at.strftime('%Y%m%d')}_{j+1:02d}"
            t["status"] = "open"
            t["source_entry_id"] = entry_id

        task_analysis = _summarize_task_analysis(tasks, task_result.get("analysis", {}))

        entry = {
            "id": entry_id,
            "source_file": f"plaud-web:{file_id}",
            "recorded_at": recorded_at.isoformat(),
            "ingested_at": datetime.now().isoformat(timespec="seconds"),
            "title": title,
            "raw": {"transcript": transcript, "summary": summary},
            "lifelog": lifelog,
            "tasks": tasks,
            "task_analysis": task_analysis,
        }

        if args.dry_run:
            print(f"       [dry-run] スキップ")
            created += 1
            continue

        saved_path = save_entry(entry)
        existing_ids.add(entry_id)
        created += 1
        print(
            f"       -> {saved_path}  tasks={len(tasks)}  "
            f"tags={', '.join(lifelog.get('tags', []))}"
        )

    if date_skipped:
        print(f"  (日付フィルタで {date_skipped} 件スキップ)")
    print(f"\n[sync] done: created={created} skipped={skipped} date_filtered={date_skipped}")
    return 0


def cmd_reindex(args) -> int:
    result = reindex()
    print(f"reindex done: entries={result['entries']}, tasks={result['tasks']}")
    return 0


def cmd_delete(args) -> int:
    entry_id = args.entry_id
    if not args.yes:
        print(f"エントリ {entry_id!r} を削除しますか？ [y/N] ", end="", flush=True)
        answer = input().strip().lower()
        if answer not in ("y", "yes"):
            print("キャンセル")
            return 0
    try:
        delete_entry(entry_id)
    except FileNotFoundError as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    print(f"deleted: {entry_id}")
    return 0


def cmd_note(args) -> int:
    if args.stdin:
        text = sys.stdin.read()
    else:
        text = " ".join(args.text).strip()
    if not text.strip():
        print("[error] メモ本文が空です", file=sys.stderr)
        return 2
    try:
        note = append_note(args.entry_id, text)
    except (FileNotFoundError, ValueError) as e:
        print(f"[error] {e}", file=sys.stderr)
        return 2
    print(
        f"{args.entry_id} <- {note['id']} ({note['created_at']})"
    )
    preview = note["text"].replace("\n", " ")
    if len(preview) > 80:
        preview = preview[:80] + "…"
    print(f"  {preview}")
    return 0


def cmd_stats(args) -> int:
    data = compute_stats()
    if args.analyze:
        data["trend_analysis"] = generate_trend_analysis(data)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    print(f"エントリ総数 : {data['entry_count']}")
    span = data.get("span")
    if span:
        print(f"期間         : {span['first']} 〜 {span['last']}")
    tasks = data["tasks"]
    print()
    print(
        f"タスク       : total={tasks['total']}  done={tasks['done']}  "
        f"open={tasks['open']}  完了率={tasks['completion_rate']*100:.1f}%"
    )
    pri = data["priority_breakdown"]
    print(
        f"優先度内訳   : high={pri.get('high', 0)}  "
        f"medium={pri.get('medium', 0)}  low={pri.get('low', 0)}"
    )
    print()

    if data["top_tags"]:
        print("-- タグ TOP --")
        for tag, count in data["top_tags"]:
            print(f"  {tag:<20} {count}")
        print()

    if data["top_categories"]:
        print("-- カテゴリ TOP --")
        for cat, count in data["top_categories"]:
            print(f"  {cat:<20} {count}")
        print()

    if data["moods"]:
        print("-- 気分 --")
        for mood, count in sorted(data["moods"].items(), key=lambda kv: -kv[1]):
            print(f"  {mood:<20} {count}")
        print()

    monthly = data["monthly"]
    if monthly:
        print("-- 月次推移 --")
        print(f"  {'月':<10} {'件数':>5} {'タスク':>6} {'完了':>5} {'完了率':>8}")
        for month, rec in monthly.items():
            rate = (rec["done"] / rec["tasks"] * 100) if rec["tasks"] else 0.0
            print(
                f"  {month:<10} {rec['entries']:>5} "
                f"{rec['tasks']:>6} {rec['done']:>5} {rate:>7.1f}%"
            )
        print()

    if args.analyze:
        trend = data.get("trend_analysis") or {}
        print("-- AI 傾向分析 --")
        print(f"  source: {trend.get('source', 'unknown')}")
        if trend.get("summary"):
            print()
            print(trend["summary"])
        observations = trend.get("observations") or []
        if observations:
            print()
            print("観察:")
            for o in observations:
                print(f"  * {o}")
        suggestions = trend.get("suggestions") or []
        if suggestions:
            print()
            print("提案:")
            for s in suggestions:
                print(f"  * {s}")
    return 0


def _resolve_range(args) -> tuple[datetime, datetime]:
    """--month / --from/--to / --days から [start, end) の範囲を決定する。"""
    month = getattr(args, "month", None)
    if month:
        try:
            y, m = month.split("-")
            year, mon = int(y), int(m)
        except ValueError as e:
            raise ValueError(f"--month は YYYY-MM 形式で指定してください: {month}") from e
        start = datetime(year, mon, 1)
        # 翌月1日
        if mon == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, mon + 1, 1)
        return start, end

    if args.date_from:
        start = datetime.fromisoformat(args.date_from)
    else:
        start = None

    if args.date_to:
        end_inclusive = datetime.fromisoformat(args.date_to)
        end = end_inclusive + timedelta(days=1)
    else:
        end = None

    if start is None and end is None:
        end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=args.days)
    elif start is None:
        start = end - timedelta(days=args.days)
    elif end is None:
        end = start + timedelta(days=args.days)

    if end <= start:
        raise ValueError(
            f"期間の終点が始点以前です: {start.date()} 〜 {end.date()} "
            "(--days は正の値、--from/--to は from <= to を指定してください)"
        )

    return start, end


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
