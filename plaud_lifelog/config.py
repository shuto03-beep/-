"""plaud-lifelog の設定・パス定義。"""
import os
from pathlib import Path

# === パス設定 ===
PACKAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = PACKAGE_DIR.parent
DATA_DIR = BASE_DIR / "data" / "plaud"
ENTRIES_DIR = DATA_DIR / "entries"
REPORTS_DIR = DATA_DIR / "reports"
TASKS_FILE = DATA_DIR / "tasks.json"
INDEX_FILE = DATA_DIR / "index.json"

# === AI 設定（既存 ai_advisor.py と同じスタイル） ===
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
AI_MODEL = os.environ.get("PLAUD_AI_MODEL", "claude-sonnet-4-5")
AI_TIMEOUT = int(os.environ.get("PLAUD_AI_TIMEOUT", "60"))
AI_ENABLED = bool(ANTHROPIC_API_KEY)


def ensure_dirs() -> None:
    """実行時にデータディレクトリを自動作成する。"""
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
