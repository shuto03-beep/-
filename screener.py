"""2パス動的銘柄スクリーニング"""
import time
import yfinance as yf
import pandas as pd
import numpy as np
from config import (
    load_universe, BATCH_SIZE, BATCH_DELAY, SCREENING_MIN_VOLUME,
    TA_SHORT_PERIOD,
)
from technical_analysis import calculate_all_indicators, calculate_sma, calculate_rsi


def fetch_batch_data(tickers: list[str], period: str = "1mo", retries: int = 3) -> dict[str, pd.DataFrame]:
    """複数銘柄のデータをバッチ取得（リトライ付き）"""
    result = {}
    for attempt in range(retries):
        try:
            data = yf.download(
                tickers, period=period, group_by="ticker",
                progress=False, threads=True,
            )
            if data is None or data.empty:
                time.sleep(BATCH_DELAY * (attempt + 1))
                continue

            if len(tickers) == 1:
                # 1銘柄の場合はそのまま
                if len(data) > 0:
                    result[tickers[0]] = data
            else:
                for ticker in tickers:
                    try:
                        ticker_data = data[ticker].dropna(how="all")
                        if len(ticker_data) > 5:
                            result[ticker] = ticker_data
                    except (KeyError, TypeError):
                        continue
            return result
        except Exception as e:
            print(f"  [SCREENER] バッチ取得リトライ {attempt + 1}/{retries}: {e}")
            time.sleep(BATCH_DELAY * (attempt + 1))
    return result


def quick_filter(universe: list[dict]) -> list[dict]:
    """パス1: 500銘柄から候補を30-50に絞り込む"""
    print(f"[SCREENER] パス1: {len(universe)}銘柄をクイックフィルタ...")
    candidates = []
    tickers = [s["ticker"] for s in universe]
    ticker_map = {s["ticker"]: s for s in universe}

    # バッチ単位で取得
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_data = fetch_batch_data(batch, period="1mo")

        for ticker, hist in batch_data.items():
            try:
                if len(hist) < 20:
                    continue

                close = hist["Close"]
                volume = hist["Volume"]

                # 流動性フィルタ
                avg_vol = volume.tail(25).mean()
                if avg_vol < SCREENING_MIN_VOLUME:
                    continue

                # 出来高異常検出
                vol_ratio = volume.iloc[-1] / avg_vol if avg_vol > 0 else 0
                has_volume_spike = vol_ratio >= 1.15  # 1.3→1.15に緩和

                # 価格変動フィルタ（5日間で±2%以上）
                price_change_5d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0
                has_price_move = abs(price_change_5d) >= 0.02  # 3%→2%に緩和

                # 前日比変動（±1.5%以上）
                price_change_1d = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] if len(close) >= 2 else 0
                has_daily_move = abs(price_change_1d) >= 0.015

                # SMAクロス検出
                sma5 = calculate_sma(close, 5)
                sma25 = calculate_sma(close, 25) if len(close) >= 25 else pd.Series([None])
                trend_change = False
                if len(sma5) >= 3 and len(sma25) >= 3:
                    for j in range(-3, 0):
                        if (not pd.isna(sma5.iloc[j]) and not pd.isna(sma25.iloc[j])
                                and not pd.isna(sma5.iloc[j - 1]) and not pd.isna(sma25.iloc[j - 1])):
                            if sma5.iloc[j] > sma25.iloc[j] and sma5.iloc[j - 1] <= sma25.iloc[j - 1]:
                                trend_change = True
                            if sma5.iloc[j] < sma25.iloc[j] and sma5.iloc[j - 1] >= sma25.iloc[j - 1]:
                                trend_change = True

                # RSIフィルタ
                rsi = calculate_rsi(close)
                rsi_val = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
                rsi_extreme = rsi_val < 38 or rsi_val > 62  # 35/65→38/62に緩和

                # いずれかの条件を満たす場合候補
                if has_volume_spike or has_price_move or has_daily_move or trend_change or rsi_extreme:
                    info = ticker_map.get(ticker, {"ticker": ticker, "name": ticker})
                    info["quick_score"] = (
                        (10 if has_volume_spike else 0)
                        + (10 if has_price_move else 0)
                        + (8 if has_daily_move else 0)
                        + (15 if trend_change else 0)
                        + (10 if rsi_extreme else 0)
                    )
                    info["vol_ratio"] = vol_ratio
                    info["price_change_5d"] = price_change_5d
                    info["rsi_quick"] = rsi_val
                    candidates.append(info)
            except Exception as e:
                continue

        if i + BATCH_SIZE < len(tickers):
            time.sleep(BATCH_DELAY)

    # スコア順にソート
    candidates.sort(key=lambda x: x.get("quick_score", 0), reverse=True)
    selected = candidates[:50]
    print(f"  → {len(selected)}銘柄が候補に残りました（全候補: {len(candidates)}）")
    if selected:
        for c in selected[:5]:
            print(f"    📌 {c.get('name', c['ticker'])}: スコア{c.get('quick_score', 0)} "
                  f"(出来高{c.get('vol_ratio', 0):.1f}x, 5日変動{c.get('price_change_5d', 0):+.1%}, RSI{c.get('rsi_quick', 0):.0f})")
    return selected


def full_analysis(candidates: list[dict]) -> list[dict]:
    """パス2: 候補銘柄にフルTA分析を実施"""
    print(f"[SCREENER] パス2: {len(candidates)}銘柄にフルTA分析...")
    analyzed = []
    tickers = [c["ticker"] for c in candidates]
    ticker_map = {c["ticker"]: c for c in candidates}

    # 3ヶ月分のデータを取得
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_data = fetch_batch_data(batch, period=TA_SHORT_PERIOD)

        for ticker, hist in batch_data.items():
            try:
                indicators = calculate_all_indicators(hist)
                if indicators is None:
                    continue
                info = ticker_map.get(ticker, {"ticker": ticker, "name": ticker})
                info["indicators"] = indicators
                info["hist_data"] = hist
                analyzed.append(info)
            except Exception:
                continue

        if i + BATCH_SIZE < len(tickers):
            time.sleep(BATCH_DELAY)

    print(f"  → {len(analyzed)}銘柄の分析完了")
    return analyzed


def run_screening() -> list[dict]:
    """スクリーニングのメインエントリポイント"""
    universe = load_universe()
    if not universe:
        print("[SCREENER] ユニバースが空です")
        return []

    # パス1: クイックフィルタ
    candidates = quick_filter(universe)
    if not candidates:
        print("[SCREENER] 候補なし")
        return []

    # パス2: フルTA分析
    analyzed = full_analysis(candidates)
    return analyzed
