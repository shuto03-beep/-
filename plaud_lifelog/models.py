"""plaud-lifelog のデータモデル。"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class ParsedDoc:
    """Plaud Web がエクスポートした Word を解析した結果。"""

    title: str
    recorded_at: datetime
    transcript: str
    summary: str
    raw_text: str
    source_file: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["recorded_at"] = self.recorded_at.isoformat()
        return d


@dataclass
class Task:
    """抽出されたアクションアイテム1件。"""

    id: str
    title: str
    priority: str = "medium"  # high / medium / low
    due: Optional[str] = None
    category: Optional[str] = None
    status: str = "open"  # open / done
    source_entry_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LifelogEntry:
    """タイムラインに保存される 1 エントリ。"""

    id: str
    source_file: str
    recorded_at: str
    ingested_at: str
    title: str
    raw: dict = field(default_factory=dict)
    lifelog: dict = field(default_factory=dict)
    tasks: list = field(default_factory=list)
    task_analysis: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)
