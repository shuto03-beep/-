"""内的スコアカードの採点・永続化・蒸留。

「他者評価」を変えられない変数として扱い、内的スコアカード（4軸）のみで
自分を採点する。蒸留(distill)機能で過去履歴から「あなたの美学」を抽出する。
"""
from __future__ import annotations

import json
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import SCORECARD_DIR, ensure_dirs
from .models import Scorecard

_AXES = ("systemize", "declutter", "two_handed", "knowledge_share")


def save_scorecard(card: Scorecard) -> Path:
    ensure_dirs()
    path = SCORECARD_DIR / f"{card.date}.json"
    path.write_text(
        json.dumps(card.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_scorecard(target_date: str) -> Scorecard | None:
    path = SCORECARD_DIR / f"{target_date}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return Scorecard(**data)


def load_recent(days: int = 30) -> list[Scorecard]:
    """直近 days 日分のスコアカードを古い順で返す。"""
    if not SCORECARD_DIR.exists():
        return []
    today = date.today()
    cutoff = today - timedelta(days=days)
    cards: list[Scorecard] = []
    for path in sorted(SCORECARD_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            d = data.get("date", "")
            try:
                target = datetime.strptime(d, "%Y-%m-%d").date()
            except ValueError:
                continue
            if target < cutoff:
                continue
            cards.append(Scorecard(**data))
        except (json.JSONDecodeError, TypeError):
            continue
    cards.sort(key=lambda c: c.date)
    return cards


def heuristic_score_from_text(text: str) -> Scorecard:
    """AI 未使用時のフォールバック採点。

    シグナル単語の出現頻度から控えめに採点する。
    実態より高めにならないよう保守的設計。
    """
    today = date.today().isoformat()
    if not text:
        return Scorecard(date=today)

    t = text.lower()
    sys_signals = ("仕組み", "テンプレ", "自動化", "automation", "プロンプト", "ワークフロー")
    decl_signals = ("捨てる", "やらない", "後回し", "委任", "ai化")
    two_signals = ("集中", "ブロック", "deep", "ディープワーク", "両手")
    share_signals = ("家族", "妻", "息子", "娘", "共有", "教えた", "学んだ")

    def count(keys):
        return sum(t.count(k.lower()) for k in keys)

    sys_score = min(10, count(sys_signals) * 2)
    decl_score = min(10, count(decl_signals) * 2)
    two_score = min(10, count(two_signals) * 2)
    share_score = min(10, count(share_signals) * 2)

    return Scorecard(
        date=today,
        systemize=sys_score,
        declutter=decl_score,
        two_handed=two_score,
        knowledge_share=share_score,
        systemize_note="(ヒューリスティック採点) 仕組み系シグナル数",
        declutter_note="(ヒューリスティック採点) 断捨離シグナル数",
        two_handed_note="(ヒューリスティック採点) 集中シグナル数",
        knowledge_share_note="(ヒューリスティック採点) 共有シグナル数",
    )


def aggregate_axes(cards: list[Scorecard]) -> dict[str, dict]:
    """各軸の平均・最大・最小・トレンドを集計。"""
    if not cards:
        return {axis: {"mean": 0, "max": 0, "min": 0, "trend": 0} for axis in _AXES}

    result: dict[str, dict] = {}
    for axis in _AXES:
        values = [getattr(c, axis) for c in cards]
        mean = statistics.fmean(values) if values else 0.0
        # トレンド: 後半平均 - 前半平均（簡易回帰の代わり）
        if len(values) >= 4:
            half = len(values) // 2
            trend = statistics.fmean(values[half:]) - statistics.fmean(values[:half])
        else:
            trend = 0.0
        result[axis] = {
            "mean": round(mean, 2),
            "max": max(values),
            "min": min(values),
            "trend": round(trend, 2),
        }
    return result


def detect_strongest_weakest(agg: dict[str, dict]) -> tuple[str, str]:
    means = [(axis, data["mean"]) for axis, data in agg.items()]
    if not means:
        return _AXES[0], _AXES[0]
    means.sort(key=lambda p: p[1], reverse=True)
    return means[0][0], means[-1][0]


def heuristic_distill(cards: list[Scorecard]) -> dict:
    """AI 未使用時に履歴から美学を蒸留する控えめ版。"""
    if not cards:
        return {
            "aesthetic_principles": ["まだ履歴が足りません"],
            "strongest_axis": _AXES[0],
            "weakest_axis": _AXES[0],
            "leverage_pattern": "",
            "shadow_pattern": "",
            "next_self_experiment": "今日のライフログを coach に通すこと",
        }
    agg = aggregate_axes(cards)
    strong, weak = detect_strongest_weakest(agg)
    label = {
        "systemize": "未来の自分を楽にする仕組み作り",
        "declutter": "他者期待からの戦略的撤退",
        "two_handed": "片手間ではない深い集中",
        "knowledge_share": "家族や周囲との知の共有",
    }
    principles = [
        f"あなたは『{label[strong]}』に強く価値を置いている",
        f"逆に『{label[weak]}』は内的にも軽視されがち（時間配分で挽回可）",
        "他者評価ではなく、この4軸の自分の点数だけを尺度にしてよい",
    ]
    return {
        "aesthetic_principles": principles,
        "strongest_axis": strong,
        "weakest_axis": weak,
        "leverage_pattern": f"{label[strong]}に時間を投じると点数が伸びる傾向",
        "shadow_pattern": f"{label[weak]}は意識しないと放置される",
        "next_self_experiment": f"明日、{label[weak]}に直結する1ブロック(30分)をカレンダー先取りする",
        "aggregate": agg,
        "sample_size": len(cards),
    }
