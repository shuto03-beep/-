"""10年ヒストリカルパターン分析"""
import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from config import CACHE_DIR, TA_LONG_PERIOD


def fetch_historical_data(ticker: str, years: int = 10) -> pd.DataFrame | None:
    """10年分の日足データを取得（キャッシュ対応）"""
    cache_file = CACHE_DIR / f"{ticker.replace('.', '_')}_hist.csv"

    # キャッシュが1日以内なら再利用
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime < timedelta(days=1):
            try:
                df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                if len(df) > 100:
                    return df
            except Exception:
                pass

    # yfinanceから取得
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=TA_LONG_PERIOD)
        if hist is not None and len(hist) > 100:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            hist.to_csv(cache_file)
            return hist
    except Exception as e:
        print(f"  [HIST] {ticker} データ取得失敗: {e}")

    return None


def normalize_pattern(prices: np.ndarray) -> np.ndarray:
    """価格パターンを正規化（0-1スケール）"""
    min_val = prices.min()
    max_val = prices.max()
    if max_val - min_val < 1e-10:
        return np.zeros_like(prices)
    return (prices - min_val) / (max_val - min_val)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """コサイン類似度"""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return dot / (norm_a * norm_b)


def find_similar_patterns(
    hist: pd.DataFrame, lookback: int = 20, forward: int = 10, top_n: int = 10
) -> list[dict]:
    """直近パターンに類似した過去パターンを検出し、その後の値動きを返す"""
    if hist is None or len(hist) < lookback + forward + 50:
        return []

    close = hist["Close"].values
    current_pattern = normalize_pattern(close[-lookback:])

    results = []
    # 直近50日は除外（重複防止）、lookback+forward分のマージン確保
    search_end = len(close) - lookback - 50
    for i in range(lookback, search_end):
        candidate = normalize_pattern(close[i - lookback:i])
        sim = cosine_similarity(current_pattern, candidate)

        if sim > 0.90:  # 類似度90%以上のみ
            # パターン後のリターン計算
            future_start = i
            future_end = min(i + forward, len(close))
            if future_end <= future_start:
                continue
            entry_price = close[i]
            future_prices = close[future_start:future_end]
            max_return = (future_prices.max() - entry_price) / entry_price
            min_return = (future_prices.min() - entry_price) / entry_price
            final_return = (future_prices[-1] - entry_price) / entry_price

            results.append({
                "index": i,
                "similarity": sim,
                "final_return": final_return,
                "max_return": max_return,
                "min_return": min_return,
                "date": str(hist.index[i].date()) if hasattr(hist.index[i], "date") else str(hist.index[i]),
            })

    # 類似度順にソートして上位を返す
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_n]


def analyze_pattern_outcomes(similar_patterns: list[dict]) -> dict:
    """類似パターン後の勝率・平均リターン等を計算"""
    if not similar_patterns:
        return {
            "pattern_count": 0, "win_rate": 0.5,
            "avg_return": 0, "max_drawdown": 0, "avg_max_return": 0,
        }

    wins = sum(1 for p in similar_patterns if p["final_return"] > 0)
    returns = [p["final_return"] for p in similar_patterns]
    max_returns = [p["max_return"] for p in similar_patterns]
    min_returns = [p["min_return"] for p in similar_patterns]

    return {
        "pattern_count": len(similar_patterns),
        "win_rate": wins / len(similar_patterns),
        "avg_return": np.mean(returns),
        "max_drawdown": np.min(min_returns),
        "avg_max_return": np.mean(max_returns),
    }


def detect_market_regime(hist: pd.DataFrame) -> str:
    """市場環境をSMA200 + ATR変動で判定"""
    if hist is None or len(hist) < 200:
        return "UNKNOWN"

    close = hist["Close"]
    sma200 = close.rolling(200).mean().iloc[-1]
    current = close.iloc[-1]

    # ATRで直近のボラティリティ判定
    high = hist["High"]
    low = hist["Low"]
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_recent = tr.tail(14).mean()
    atr_long = tr.tail(60).mean()

    high_vol = atr_recent > atr_long * 1.5

    if high_vol:
        return "HIGH_VOLATILITY"
    elif current > sma200:
        return "BULL"
    elif current < sma200:
        return "BEAR"
    return "SIDEWAYS"


def get_seasonal_tendency(hist: pd.DataFrame, target_month: int, target_day: int) -> dict:
    """過去10年の同時期の傾向（アノマリー分析）"""
    if hist is None or len(hist) < 252:
        return {"avg_return_5d": 0, "avg_return_10d": 0, "positive_rate": 0.5, "samples": 0}

    close = hist["Close"]
    returns_5d = []
    returns_10d = []

    for year in range(hist.index[0].year, hist.index[-1].year):
        # 対象月の近辺のデータを探す
        mask = (hist.index.year == year) & (hist.index.month == target_month)
        month_data = hist[mask]
        if len(month_data) < 5:
            continue
        # 月の最初の営業日付近でのリターン
        start_idx = hist.index.get_loc(month_data.index[0])
        if start_idx + 10 < len(close):
            ret_5d = (close.iloc[start_idx + 5] - close.iloc[start_idx]) / close.iloc[start_idx]
            ret_10d = (close.iloc[start_idx + 10] - close.iloc[start_idx]) / close.iloc[start_idx]
            returns_5d.append(ret_5d)
            returns_10d.append(ret_10d)

    if not returns_5d:
        return {"avg_return_5d": 0, "avg_return_10d": 0, "positive_rate": 0.5, "samples": 0}

    return {
        "avg_return_5d": np.mean(returns_5d),
        "avg_return_10d": np.mean(returns_10d),
        "positive_rate": sum(1 for r in returns_5d if r > 0) / len(returns_5d),
        "samples": len(returns_5d),
    }


def run_historical_analysis(ticker: str, hist_short: pd.DataFrame) -> dict:
    """ヒストリカル分析のメインエントリポイント"""
    # 10年データ取得
    hist_long = fetch_historical_data(ticker)

    # 類似パターン検出
    similar = find_similar_patterns(hist_long) if hist_long is not None else []
    outcomes = analyze_pattern_outcomes(similar)

    # 市場環境判定
    regime = detect_market_regime(hist_long) if hist_long is not None else "UNKNOWN"

    # 季節性分析
    now = datetime.now()
    seasonal = get_seasonal_tendency(hist_long, now.month, now.day) if hist_long is not None else {}

    return {
        "similar_patterns": similar[:5],  # 上位5件のみ返す
        "pattern_outcomes": outcomes,
        "market_regime": regime,
        "seasonal": seasonal,
    }
