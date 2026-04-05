"""日本株スウィングトレード自動売買Bot - メインオーケストレーター"""
import time
import traceback
from datetime import datetime, timezone, timedelta

import yfinance as yf

from config import AI_MAX_CALLS_PER_RUN, BUY_SCORE_THRESHOLD, SELL_SCORE_THRESHOLD
from positions import load_state, save_state, check_exit_conditions, update_trailing_stop, close_position, get_portfolio_summary, open_position
from risk_management import can_open_position, calculate_position_size, calculate_stop_loss, calculate_take_profit, check_daily_loss_limit
from screener import run_screening
from technical_analysis import calculate_all_indicators
from historical_analysis import run_historical_analysis
from ai_advisor import get_ai_assessment
from signals import generate_signal
from learning import should_run_optimization, run_learning_cycle, generate_performance_report
from notifications import (
    send_signal_notification, send_exit_notification,
    send_position_update, send_daily_summary, send_learning_report,
    send_startup_notification,
)

JST = timezone(timedelta(hours=9))


def check_existing_positions(state: dict):
    """既存ポジションの監視（ストップロス・利確・トレーリングストップ）"""
    positions = state["portfolio"]["positions"]
    if not positions:
        return

    print(f"[POSITIONS] {len(positions)}件のポジションをチェック...")
    current_prices = {}

    for pos in positions[:]:  # コピーして反復（削除対応）
        ticker = pos["ticker"]
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if hist is None or len(hist) == 0:
                continue
            current_price = hist["Close"].iloc[-1]
            current_prices[ticker] = current_price

            # トレーリングストップ更新
            update_trailing_stop(pos, current_price)

            # 終了条件チェック
            exit_reason = check_exit_conditions(pos, current_price)
            if exit_reason:
                trade_record = close_position(state, ticker, current_price, exit_reason)
                if trade_record:
                    print(f"  → {pos['name']} 決済: {exit_reason} (損益: {trade_record['pnl']:+,.0f}円)")
                    send_exit_notification(trade_record, exit_reason)
        except Exception as e:
            print(f"  [ERROR] {pos['name']}: {e}")

    # ポジション状況通知（残っているポジションがあれば）
    remaining = state["portfolio"]["positions"]
    if remaining and current_prices:
        send_position_update(remaining, current_prices)


def run_full_screening_and_signals(state: dict):
    """フルスクリーニング → TA分析 → ヒストリカル → AI判断 → シグナル生成"""
    print("[MAIN] フルスクリーニング開始...")

    # スクリーニング（パス1 + パス2）
    analyzed = run_screening()
    if not analyzed:
        print("[MAIN] スクリーニング結果なし")
        return 0

    print(f"[MAIN] {len(analyzed)}銘柄を分析完了、シグナル生成中...")

    # 上位銘柄にAI判断を適用
    ai_call_count = 0
    all_signals = []

    for item in analyzed:
        ticker = item["ticker"]
        name = item.get("name", ticker)
        indicators = item.get("indicators")
        if not indicators:
            continue

        # ヒストリカル分析
        try:
            hist_data = run_historical_analysis(ticker, item.get("hist_data"))
        except Exception:
            hist_data = None

        # AI判断（上位銘柄のみ、コール数制限あり）
        ai_assessment = None
        if ai_call_count < AI_MAX_CALLS_PER_RUN:
            try:
                ai_assessment = get_ai_assessment(ticker, name, indicators, hist_data)
                ai_call_count += 1
            except Exception:
                ai_assessment = None

        # シグナル生成
        signal = generate_signal(ticker, name, indicators, hist_data, ai_assessment)
        all_signals.append(signal)

    # シグナル通知
    signal_count = 0
    for signal in all_signals:
        if signal.signal_type == "HOLD":
            continue

        if signal.strength in ("STRONG", "MEDIUM"):
            print(f"  📊 {signal.name}: {signal.signal_type} (スコア: {signal.final_score})")
            send_signal_notification(signal)
            signal_count += 1

            # 自動ポジション開設（STRONGシグナルのみ）
            if (signal.signal_type == "BUY" and signal.strength == "STRONG"
                    and can_open_position(state) and not check_daily_loss_limit(state)):
                _auto_open_position(state, signal)

    # シグナル履歴保存
    state["signals_history"] = state.get("signals_history", [])[-100:]  # 最新100件のみ
    for sig in all_signals:
        if sig.signal_type != "HOLD":
            state["signals_history"].append({
                "ticker": sig.ticker, "name": sig.name,
                "type": sig.signal_type, "score": sig.final_score,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

    state["last_full_screening"] = datetime.now().isoformat()
    return signal_count


def _auto_open_position(state: dict, signal):
    """強シグナルに基づきポジションを自動開設"""
    indicators = signal.indicators
    price = indicators["current_price"]
    atr = indicators.get("atr", 0)
    if atr <= 0:
        return

    capital = state["portfolio"]["capital"]
    shares = calculate_position_size(capital, price, atr)
    if shares <= 0:
        return

    sl = calculate_stop_loss(price, atr)
    tp = calculate_take_profit(price, atr)

    ai_conf = signal.ai_assessment.get("confidence", 0) if signal.ai_assessment else 0
    pos = open_position(
        state, signal.ticker, signal.name, price, shares, sl, tp,
        signal_score=signal.final_score,
        signal_reasons=[r[:50] for r in signal.reasons[:5]],
        ai_confidence=ai_conf,
    )
    print(f"  🟢 ポジション開設: {signal.name} {shares}株 @ {price:,.0f}円")


def quick_check_watchlist(state: dict):
    """15分/30分/45分台: 既存ポジション銘柄のクイックチェック"""
    positions = state["portfolio"]["positions"]
    if not positions:
        return
    # check_existing_positionsで処理済み
    pass


def main():
    """メインエントリポイント"""
    now = datetime.now(JST)
    print(f"{'='*50}")
    print(f"[MAIN] スウィングトレードBot起動 - {now.strftime('%Y-%m-%d %H:%M:%S')} JST")
    print(f"{'='*50}")

    state = load_state()

    # === 起動通知（毎回送信） ===
    try:
        send_startup_notification(state)
    except Exception as e:
        print(f"[WARN] 起動通知エラー: {e}")

    try:
        # === Phase 1: 既存ポジション監視（毎回実行） ===
        check_existing_positions(state)
    except Exception as e:
        print(f"[ERROR] ポジション監視エラー: {e}")
        traceback.print_exc()

    # === Phase 2: フルスクリーニング（毎時0分台のみ） ===
    signal_count = 0
    try:
        if now.minute < 15:
            signal_count = run_full_screening_and_signals(state)
        else:
            quick_check_watchlist(state)
            print(f"[MAIN] クイックチェックモード（次回フルスクリーニング: {now.hour + 1}:00）")
    except Exception as e:
        print(f"[ERROR] スクリーニングエラー: {e}")
        traceback.print_exc()

    # === Phase 3: 学習サイクル（週次） ===
    try:
        if should_run_optimization(state):
            analysis = run_learning_cycle(state)
            report = generate_performance_report(state)
            send_learning_report(report)
    except Exception as e:
        print(f"[ERROR] 学習サイクルエラー: {e}")

    # === デイリーサマリー（14:45以降の最終実行時） ===
    try:
        if now.hour == 5 and now.minute >= 45:  # UTC 5:45 = JST 14:45
            summary = get_portfolio_summary(state)
            send_daily_summary(summary, signal_count)
    except Exception as e:
        print(f"[ERROR] デイリーサマリーエラー: {e}")

    save_state(state)
    print(f"\n[MAIN] 完了 - state.json保存済み")


if __name__ == "__main__":
    main()
