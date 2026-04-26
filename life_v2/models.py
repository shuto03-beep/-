"""life_v2 のデータモデル。

「分析・構造化で満足するループ」を断つため、すべてのモデルは
「即実行可能な状態」または「採点済みの履歴」のどちらかに収束する。
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ValuedTask:
    """高価値タスクに昇格した1件。低価値は dropped に入れて捨てる。"""

    title: str
    duration_minutes: int = 30
    priority: str = "Medium"  # High / Medium / Low
    description: str = ""
    leverage: bool = False  # フィルタ1: レバレッジ
    mission: bool = False   # フィルタ2: 使命
    uniqueness: bool = False  # フィルタ3: 独自性
    source_entry_id: Optional[str] = None

    @property
    def filter_count(self) -> int:
        return int(self.leverage) + int(self.mission) + int(self.uniqueness)

    def to_calendar_dict(self) -> dict:
        """Google Calendar / 任意のカレンダーアプリに即投入可能な形式。"""
        rationale_parts = []
        if self.leverage:
            rationale_parts.append("レバレッジ")
        if self.mission:
            rationale_parts.append("使命")
        if self.uniqueness:
            rationale_parts.append("独自性")
        rationale = "・".join(rationale_parts) or "high-leverage"
        desc = self.description or f"フィルタ({rationale})に合致。"
        return {
            "title": self.title,
            "description": desc,
            "duration_minutes": int(self.duration_minutes),
            "priority": self.priority,
        }

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DroppedTask:
    """戦略的撤退の対象。捨てる/AI化/委任の理由を必ず明示。"""

    title: str
    reason: str  # なぜ捨てる/AI化/委任するか
    disposition: str = "drop"  # drop / automate / delegate / defer
    source_entry_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scorecard:
    """4軸 各10点の内的スコアカード。

    軸の意図:
      - systemize: 未来の自分を楽にするシステムを作ったか
      - declutter: 他者期待ベースの低価値タスクを切り捨てられたか
      - two_handed: 片手間ではない深い集中の時間を取れたか
      - knowledge_share: 家族や周囲と知的な発見を共有できたか
    """

    date: str  # YYYY-MM-DD
    systemize: int = 0
    declutter: int = 0
    two_handed: int = 0
    knowledge_share: int = 0
    systemize_note: str = ""
    declutter_note: str = ""
    two_handed_note: str = ""
    knowledge_share_note: str = ""
    total: int = 0
    source_entry_ids: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        for axis in ("systemize", "declutter", "two_handed", "knowledge_share"):
            v = getattr(self, axis)
            v = max(0, min(10, int(v)))
            setattr(self, axis, v)
        self.total = self.systemize + self.declutter + self.two_handed + self.knowledge_share
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CoachOutput:
    """`coach` コマンドの完全な出力。これ1つで実行に移れる。"""

    date: str
    scorecard: Scorecard
    dropped: list[DroppedTask]
    next_actions: list[ValuedTask]
    headline: str = ""
    one_minute_action: str = ""  # 1分以内に着手できる最初の一手
    aesthetic_signal: str = ""   # 内的スコアカードから読み取れる「あなたの美学」

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "headline": self.headline,
            "one_minute_action": self.one_minute_action,
            "aesthetic_signal": self.aesthetic_signal,
            "scorecard": self.scorecard.to_dict(),
            "dropped": [d.to_dict() for d in self.dropped],
            "next_actions": [t.to_dict() for t in self.next_actions],
        }
