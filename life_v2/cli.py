"""life_v2 CLI エントリーポイント。

サブコマンド:
  coach       テキストor entry-id → スコアカード + Next Actions（メイン機能）
  triage      Plaud V1 のオープンタスクを高価値/捨てるに振り分け
  morning     朝の儀式: 昨日のスコアカード + 今日の予定 → 90分ブロック設計
  evening     夜の儀式: 今日のテキスト → スコアカード採点 + 明日の最初の一手
  distill     過去のスコアカード履歴から美学を蒸留
  history     スコアカード履歴サマリ表示
  show        保存済み coach output を表示
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .cognitive_partner import (
    coach,
    distill_aesthetic,
    evening_ritual,
    morning_ritual,
    triage,
)
from .config import MAX_NEXT_ACTIONS
from .daily_ritual import format_evening, format_morning, save_ritual
from .models import Scorecard
from .next_action import to_calendar_json, to_human_summary, to_ics
from .notifier import post as notify_post
from .scorecard import (
    aggregate_axes,
    detect_strongest_weakest,
    load_recent,
    load_scorecard,
    save_scorecard,
)
from .storage import (
    collect_recent_plaud_text,
    load_aesthetic,
    load_open_plaud_tasks,
    load_plaud_entry,
    plaud_entry_to_text,
    save_aesthetic,
    save_coach_output,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="life_v2",
        description="Cognitive Continuity Partner: ライフログを即実行可能なNext Actionに変換します",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_coach = sub.add_parser("coach", help="テキスト/エントリ → スコアカード + Next Actions")
    src = p_coach.add_mutually_exclusive_group()
    src.add_argument("--text", help="直接テキストを与える")
    src.add_argument("--entry", help="Plaud V1 の entry_id (例: 2026-04-11_asa-kai)")
    src.add_argument("--from-stdin", action="store_true", help="stdin からテキストを読む")
    src.add_argument("--recent-days", type=int, help="Plaud entries 直近N日分を結合して入力")
    p_coach.add_argument("--save", action="store_true", help="結果を data/life_v2/triage/ に保存")
    p_coach.add_argument("--save-scorecard", action="store_true", help="スコアカードも蓄積")
    p_coach.add_argument("--json", action="store_true", help="JSONで標準出力")
    p_coach.add_argument("--ics", type=Path, help=".ics ファイルとして書き出す")
    p_coach.add_argument(
        "--calendar-json",
        type=Path,
        help="カレンダー登録用 JSON 配列を書き出す",
    )
    p_coach.add_argument("--notify", action="store_true", help="Discord webhook に投稿")

    p_triage = sub.add_parser("triage", help="Plaud V1 のオープンタスクを強制振り分け")
    p_triage.add_argument("--limit", type=int, default=80)
    p_triage.add_argument("--json", action="store_true")

    p_morning = sub.add_parser("morning", help="朝の儀式: 90分ブロック設計")
    p_morning.add_argument("--text", help="今日の予定/メモを直接与える")
    p_morning.add_argument("--from-stdin", action="store_true")
    p_morning.add_argument("--save", action="store_true", help="data/life_v2/rituals/ に保存")
    p_morning.add_argument("--json", action="store_true")
    p_morning.add_argument("--notify", action="store_true", help="Discord webhook に投稿")

    p_evening = sub.add_parser("evening", help="夜の儀式: スコアカード採点")
    p_evening.add_argument("--text", help="今日のライフログを直接与える")
    p_evening.add_argument("--from-stdin", action="store_true")
    p_evening.add_argument("--recent-days", type=int, default=1)
    p_evening.add_argument("--save", action="store_true")
    p_evening.add_argument("--save-scorecard", action="store_true")
    p_evening.add_argument("--json", action="store_true")
    p_evening.add_argument("--notify", action="store_true", help="Discord webhook に投稿")

    p_distill = sub.add_parser("distill", help="過去スコアカードから美学を蒸留")
    p_distill.add_argument("--days", type=int, default=30)
    p_distill.add_argument("--save", action="store_true")
    p_distill.add_argument("--json", action="store_true")

    p_hist = sub.add_parser("history", help="スコアカード履歴サマリ表示")
    p_hist.add_argument("--days", type=int, default=30)
    p_hist.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="保存済み coach output を表示")
    p_show.add_argument("target_date", help="YYYY-MM-DD")

    args = parser.parse_args(argv)

    if args.command == "coach":
        return _cmd_coach(args)
    if args.command == "triage":
        return _cmd_triage(args)
    if args.command == "morning":
        return _cmd_morning(args)
    if args.command == "evening":
        return _cmd_evening(args)
    if args.command == "distill":
        return _cmd_distill(args)
    if args.command == "history":
        return _cmd_history(args)
    if args.command == "show":
        return _cmd_show(args)
    return 2


# ========== コマンド実装 ==========

def _cmd_coach(args) -> int:
    text, source_entry_id = _resolve_text_and_entry(args)
    if not text:
        print("エラー: --text / --entry / --from-stdin / --recent-days のいずれかを指定してください", file=sys.stderr)
        return 2

    output = coach(text, source_entry_id=source_entry_id)

    if args.save:
        path = save_coach_output(output)
        print(f"[保存] {path}")
    if args.save_scorecard:
        save_scorecard(output.scorecard)
        print(f"[保存] スコアカード {output.scorecard.date}")

    if args.calendar_json:
        args.calendar_json.parent.mkdir(parents=True, exist_ok=True)
        args.calendar_json.write_text(
            to_calendar_json(output.next_actions), encoding="utf-8",
        )
        print(f"[書き出し] {args.calendar_json}")
    if args.ics:
        args.ics.parent.mkdir(parents=True, exist_ok=True)
        args.ics.write_text(to_ics(output.next_actions), encoding="utf-8")
        print(f"[書き出し] {args.ics}")

    if args.json:
        print(json.dumps(output.to_dict(), ensure_ascii=False, indent=2))
    else:
        _render_coach(output)
    if args.notify:
        notify_post(
            _coach_to_message(output),
            prefix=f"☀️ Coach for {output.date}",
        )
    return 0


def _cmd_triage(args) -> int:
    open_tasks = load_open_plaud_tasks(limit=args.limit)
    if not open_tasks:
        print("Plaud V1 にオープンタスクがありません。")
        return 0
    high, dropped = triage(open_tasks)

    if args.json:
        print(json.dumps({
            "high_leverage": [t.to_dict() for t in high],
            "dropped": [d.to_dict() for d in dropped],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"📦 Triage 結果 (入力 {len(open_tasks)}件)")
    print(f"  高価値: {len(high)}件 / 戦略的撤退: {len(dropped)}件")
    print()
    print("⚡ 高価値 (Next Actions 候補)")
    for i, t in enumerate(high, 1):
        flags = "".join("L" if t.leverage else "_" + ("M" if t.mission else "_") + ("U" if t.uniqueness else "_"))
        print(f"  {i}. [{flags}] {t.title} ({t.duration_minutes}分 / {t.priority})")
    print()
    print("🗑 戦略的撤退")
    for i, d in enumerate(dropped, 1):
        print(f"  {i}. [{d.disposition}] {d.title}")
        print(f"      → {d.reason}")
    return 0


def _cmd_morning(args) -> int:
    text = _read_text_arg(args)
    if not text:
        text = collect_recent_plaud_text(days=1)
    yesterday = _load_yesterday_card()
    yc_dict = yesterday.to_dict() if yesterday else None
    payload = morning_ritual(yc_dict, text or "(今日の予定情報なし)")

    if args.save:
        path = save_ritual("morning", payload)
        print(f"[保存] {path}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_morning(payload))
    if args.notify:
        notify_post(format_morning(payload), prefix=f"🌅 Morning {date.today().isoformat()}")
    return 0


def _cmd_evening(args) -> int:
    text = _read_text_arg(args)
    if not text:
        text = collect_recent_plaud_text(days=args.recent_days)
    if not text:
        print("エラー: 今日のライフログテキストがありません", file=sys.stderr)
        return 2
    payload = evening_ritual(text)

    if args.save:
        path = save_ritual("evening", payload)
        print(f"[保存] {path}")
    if args.save_scorecard:
        sc = payload.get("scorecard") or {}
        card = Scorecard(
            date=date.today().isoformat(),
            systemize=int(sc.get("systemize", 0)),
            declutter=int(sc.get("declutter", 0)),
            two_handed=int(sc.get("two_handed", 0)),
            knowledge_share=int(sc.get("knowledge_share", 0)),
            systemize_note=str(sc.get("systemize_note", "")),
            declutter_note=str(sc.get("declutter_note", "")),
            two_handed_note=str(sc.get("two_handed_note", "")),
            knowledge_share_note=str(sc.get("knowledge_share_note", "")),
        )
        save_scorecard(card)
        print(f"[保存] スコアカード {card.date}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_evening(payload))
    if args.notify:
        notify_post(format_evening(payload), prefix=f"🌙 Evening {date.today().isoformat()}")
    return 0


def _cmd_distill(args) -> int:
    cards = load_recent(days=args.days)
    payload = distill_aesthetic([c.to_dict() for c in cards])
    if args.save:
        save_aesthetic(payload)
        print(f"[保存] aesthetic.json (sample={len(cards)})")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(f"🧭 内的美学の蒸留 (過去{args.days}日 / 採用={len(cards)}件)")
    for p in payload.get("aesthetic_principles", []):
        print(f"  ・{p}")
    strong = payload.get("strongest_axis")
    weak = payload.get("weakest_axis")
    if strong:
        print(f"  最強軸: {strong} — {payload.get('leverage_pattern','')}")
    if weak:
        print(f"  影の軸: {weak} — {payload.get('shadow_pattern','')}")
    nse = payload.get("next_self_experiment")
    if nse:
        print(f"  🧪 明日の自己実験: {nse}")
    return 0


def _cmd_history(args) -> int:
    cards = load_recent(days=args.days)
    if not cards:
        print("スコアカード履歴がありません。")
        return 0
    agg = aggregate_axes(cards)
    if args.json:
        print(json.dumps({
            "sample_size": len(cards),
            "aggregate": agg,
            "cards": [c.to_dict() for c in cards],
        }, ensure_ascii=False, indent=2))
        return 0

    print(f"📊 スコアカード履歴 (直近{args.days}日 / {len(cards)}件)")
    label = {"systemize": "仕組み化", "declutter": "断捨離",
             "two_handed": "両手", "knowledge_share": "知の共有"}
    for axis, data in agg.items():
        trend = data["trend"]
        arrow = "↗" if trend > 0.5 else ("↘" if trend < -0.5 else "→")
        print(f"  {label[axis]:>6}: 平均{data['mean']:.1f}/10  最大{data['max']}  最小{data['min']}  {arrow}{trend:+.1f}")
    strong, weak = detect_strongest_weakest(agg)
    print(f"\n  最強軸: {label[strong]} / 影の軸: {label[weak]}")
    return 0


def _cmd_show(args) -> int:
    from .config import TRIAGE_DIR
    path = TRIAGE_DIR / f"{args.target_date}_coach.json"
    if not path.exists():
        print(f"見つかりません: {path}", file=sys.stderr)
        return 1
    print(path.read_text(encoding="utf-8"))
    return 0


# ========== ヘルパ ==========

def _resolve_text_and_entry(args) -> tuple[str, str | None]:
    if getattr(args, "text", None):
        return args.text, None
    if getattr(args, "from_stdin", False):
        return sys.stdin.read(), None
    if getattr(args, "entry", None):
        entry = load_plaud_entry(args.entry)
        if not entry:
            print(f"entry が見つかりません: {args.entry}", file=sys.stderr)
            return "", None
        return plaud_entry_to_text(entry), args.entry
    if getattr(args, "recent_days", None):
        return collect_recent_plaud_text(days=args.recent_days), None
    return "", None


def _read_text_arg(args) -> str:
    if getattr(args, "text", None):
        return args.text
    if getattr(args, "from_stdin", False):
        return sys.stdin.read()
    return ""


def _load_yesterday_card() -> Scorecard | None:
    from datetime import timedelta
    target = (date.today() - timedelta(days=1)).isoformat()
    return load_scorecard(target)


def _coach_to_message(output) -> str:
    """Discord 投稿用に coach 結果を簡潔に整形する。"""
    lines = []
    if output.headline:
        lines.append(f"**{output.headline}**")
    if output.aesthetic_signal:
        lines.append(f"_{output.aesthetic_signal}_")
    sc = output.scorecard
    lines.append(
        f"スコア: 仕組み {sc.systemize}/10 ・ 断捨離 {sc.declutter}/10 ・ "
        f"両手 {sc.two_handed}/10 ・ 共有 {sc.knowledge_share}/10 (合計 {sc.total}/40)"
    )
    if output.dropped:
        lines.append("")
        lines.append("🗑 戦略的撤退:")
        for d in output.dropped[:5]:
            lines.append(f"・[{d.disposition}] {d.title}")
    lines.append("")
    lines.append("⚡ Next Actions:")
    for i, t in enumerate(output.next_actions, 1):
        flags = []
        if t.leverage:
            flags.append("L")
        if t.mission:
            flags.append("M")
        if t.uniqueness:
            flags.append("U")
        flag_str = "/".join(flags) or "-"
        lines.append(f"{i}. [{flag_str}] {t.title} ({t.duration_minutes}分・{t.priority})")
    if output.one_minute_action:
        lines.append("")
        lines.append(f"🔘 1分以内の最初の一手: {output.one_minute_action}")
    return "\n".join(lines)


def _render_coach(output) -> None:
    print()
    print(f"📅 {output.date}  {output.headline}")
    if output.aesthetic_signal:
        print(f"   {output.aesthetic_signal}")
    print()
    print("📊 内的スコアカード評価")
    sc = output.scorecard
    for axis, label, note in (
        ("systemize", "仕組み化", sc.systemize_note),
        ("declutter", "断捨離", sc.declutter_note),
        ("two_handed", "両手タスク", sc.two_handed_note),
        ("knowledge_share", "知の共有", sc.knowledge_share_note),
    ):
        score = getattr(sc, axis)
        print(f"  - {label}: {score}/10 - {note or '(短評なし)'}")
    print(f"  合計: {sc.total}/40")
    print()
    print("🗑️ 捨てるべきタスク（戦略的撤退）")
    if not output.dropped:
        print("  (該当なし)")
    for d in output.dropped:
        print(f"  - [{d.disposition}] {d.title} : {d.reason}")
    print()
    print(to_human_summary(output.next_actions, one_minute_action=output.one_minute_action))
    print()
    print("```json")
    print(to_calendar_json(output.next_actions))
    print("```")


if __name__ == "__main__":
    sys.exit(main())
