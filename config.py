"""スウィングトレードBot設定"""
import os
import json
from pathlib import Path

# === パス設定 ===
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
STATE_FILE = DATA_DIR / "state.json"
LEARNING_FILE = DATA_DIR / "learning.json"
UNIVERSE_FILE = DATA_DIR / "universe.json"

# === 資金設定 ===
INITIAL_CAPITAL = 1_000_000
MAX_POSITION_RATIO = 0.25
MAX_TOTAL_EXPOSURE = 0.80
MAX_POSITIONS = 5

# === スウィングトレード設定 ===
HOLDING_PERIOD_MAX = 15
STOP_LOSS_PCT = -0.03
TAKE_PROFIT_PCT = 0.08
TRAILING_STOP_PCT = 0.03

# === シグナル閾値 ===
BUY_SCORE_THRESHOLD = 60
SELL_SCORE_THRESHOLD = -40
STRONG_SIGNAL_THRESHOLD = 75

# === AI設定 ===
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
AI_ENABLED = bool(ANTHROPIC_API_KEY)
AI_TIMEOUT = 10
AI_MAX_CALLS_PER_RUN = 15
AI_MODEL = "claude-sonnet-4-20250514"

# === Discord設定 ===
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

# === スクリーニング設定 ===
SCREENING_MIN_VOLUME = 500_000
FULL_SCREENING_INTERVAL = 60  # 分

# === テクニカル分析設定 ===
TA_SHORT_PERIOD = "3mo"   # 短期分析用データ期間
TA_LONG_PERIOD = "10y"    # ヒストリカル分析用データ期間
BATCH_SIZE = 50           # yfinance一括取得の最大銘柄数
BATCH_DELAY = 2.0         # バッチ間のスリープ秒数

# === スコアリングのデフォルト重み ===
DEFAULT_WEIGHTS = {
    "ma_cross": 15,
    "ma_trend": 10,
    "macd": 15,
    "rsi": 10,
    "bollinger": 10,
    "volume": 10,
    "stochastic": 10,
    "ichimoku": 15,
    "historical": 5,
}


def load_universe() -> list[dict]:
    """data/universe.jsonからスクリーニングユニバースを読み込む"""
    if UNIVERSE_FILE.exists():
        with open(UNIVERSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("stocks", [])
    return []
