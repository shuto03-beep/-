"""life_v2 の設定・パス定義。

既存 plaud_lifelog のデータ層 (data/plaud/) と並列に
data/life_v2/ を持ち、スコアカード履歴と triage 結果を蓄積する。
"""
import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = PACKAGE_DIR.parent
DATA_DIR = BASE_DIR / "data" / "life_v2"
SCORECARD_DIR = DATA_DIR / "scorecards"
TRIAGE_DIR = DATA_DIR / "triage"
RITUAL_DIR = DATA_DIR / "rituals"
DISTILL_FILE = DATA_DIR / "aesthetic.json"

# Plaud V1 のデータ層（読み取り共有）
PLAUD_DATA_DIR = BASE_DIR / "data" / "plaud"
PLAUD_ENTRIES_DIR = PLAUD_DATA_DIR / "entries"
PLAUD_TASKS_FILE = PLAUD_DATA_DIR / "tasks.json"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
AI_MODEL = os.environ.get("LIFE_V2_AI_MODEL", os.environ.get("PLAUD_AI_MODEL", "claude-sonnet-4-5"))
AI_TIMEOUT = int(os.environ.get("LIFE_V2_AI_TIMEOUT", "60"))
AI_ENABLED = bool(ANTHROPIC_API_KEY)

# 1日のうち高価値タスクに割ける現実的な上限（分）
DAILY_HIGH_LEVERAGE_BUDGET_MIN = int(os.environ.get("LIFE_V2_DAILY_BUDGET", "180"))

# Next Action の最大本数（過剰提示を防ぐ「捨てる」装置の一部）
MAX_NEXT_ACTIONS = int(os.environ.get("LIFE_V2_MAX_ACTIONS", "3"))


def ensure_dirs() -> None:
    SCORECARD_DIR.mkdir(parents=True, exist_ok=True)
    TRIAGE_DIR.mkdir(parents=True, exist_ok=True)
    RITUAL_DIR.mkdir(parents=True, exist_ok=True)
