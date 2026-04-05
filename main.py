"""日本株スウィングトレード自動売買Bot - メインオーケストレーター（マルチ戦略対応）"""
import time
import traceback
from datetime import datetime, timezone, timedelta

import yfinance as yf

from config import AI_MAX_CALLS_PER_RUN, BUY_SCORE_THRESHOLD, STRATEGIES
from positions import (
    load_state, save_state, check_exit_conditions, update_trailing_stop,
    close_position, open_position, get_all_strategies_summary,
)
from risk_management import (
    can_open_position_strategy, calculate_position_size,
    calculate_stop_loss, calculate_take_profit, check_daily_loss_limit_strategy,
)
from screener import run_screening
from technical_analysis import calculate_all_indicators
from historical_analysis import run_historical_analysis
from ai_advisor import get_ai_assessment
from signals import generate_signal
from learning import should_run_optimization, run_learning_cycle, generate_performance_report
from notifications import (
    send_signal_notification, send_exit_notification,
    send_position_update, send_strategies_summary, send_learning_report,
    send_startup_notification,
)

JST = timezone(timedelta(hours=9))

# 日本の祝日（2026年）※年始に毎年更新が必要
JPX_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-02", "2026-01-03",  # 年末年始
    "2026-01-12",  # 成人の日
    "2026-02-11",  # 建国記念の日
    "2026-02-23",  # 天皇誕生日
    "2026-03-20",  # 春分の日
    "2026-04-29",  # 昭和の日
    "2026-05-03", "2026-05-04", "2026-05-05", "2026-05-06",  # GW
    "2026-07-20",  # 海の日
    "2026-08-11",  # 山の日
    "2026-09-21", "2026-09-22", "2026-09-23",  # 敬老の日・秋分の日
    "2026-10-12",  # スポーツの日
    "2026-11-03",  # 文化の日
    "2026-11-23",  # 勤労感謝の日
    "2026-12-31",  # 大納会
}


def is_market_open(now) -> bool:
    """東証の取引日かどうか判定"""
    if now.weekday() >= 5:  # 土日
        return False
    date_str = now.strftime("%Y-%m-%d")
    if date_str in JPX_HOLIDAYS_2026:
        return False
    return True


def check_existing_positions(state: dict):
    """全戦略の既存ポジション監視"""
    for strategy_key, strategy_config in STRATEGIES.items():
        portfolio = state["strategies"][strategy_key]
        positions = portfolio["positions"]
        if not positions:
            continue

        label = strategy_config["label"]
        print(f"[POSITIONS] {label}: {len(positions)}件のポジションをチェック...")
        current_prices = {}

        for pos in positions[:]:
            ticker = pos["ticker"]
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="5d")
                if hist is None or len(hist) == 0:
                    continue
                current_price = hist["Close"].iloc[-1]
                current_prices[ticker] = current_price

                update_trailing_stop(pos, current_price)

                exit_reason = check_exit_conditions(pos, current_price)
                if exit_reason:
                    trade_record = close_position(state, strategy_key, ticker, current_price, exit_reason)
                    if trade_record:
                        print(f"  → [{label}] {pos['name']} 決済: {exit_reason} (損益: {trade_record['pnl']:+,.0f}円)")
                        send_exit_notification(trade_record, exit_reason, strategy_config)
            except Exception as e:
                print(f"  [ERROR] {pos['name']}: {e}")

        remaining = portfolio["positions"]
        if remaining and current_prices:
            send_position_update(remaining, current_prices, strategy_config)


def run_full_screening_and_signals(state: dict):
    """フルスクリーニング → シグナル生成 → 全戦略にポジション適用"""
    print("[MAIN] フルスクリーニング開始...")

    analyzed = run_screening()
    if not analyzed:
        print("[MAIN] スクリーニング結果なし")
        return 0

    print(f"[MAIN] {len(analyzed)}銘柄を分析完了、シグナル生成中...")

    ai_call_count = 0
    all_signals = []

    for item in analyzed:
        ticker = item["ticker"]
        name = item.get("name", ticker)
        indicators = item.get("indicators")
        if not indicators:
            continue

        try:
            hist_data = run_historical_analysis(ticker, item.get("hist_data"))
        except Exception:
            hist_data = None

        ai_assessment = None
        if ai_call_count < AI_MAX_CALLS_PER_RUN:
            try:
                ai_assessment = get_ai_assessment(ticker, name, indicators, hist_data)
                ai_call_count += 1
            except Exception:
                ai_assessment = None

        signal = generate_signal(ticker, name, indicators, hist_data, ai_assessment)
        all_signals.append(signal)

    # シグナル通知 & 全戦略にポジション適用
    signal_count = 0
    for signal in all_signals:
        if signal.signal_type == "HOLD":
            continue

        if signal.strength in ("STRONG", "MEDIUM"):
            print(f"  📊 {signal.name}: {signal.signal_type} (スコア: {signal.final_score})")
            send_signal_notification(signal)
            signal_count += 1

            # 全戦略に対してポジション開設を試行
            if signal.signal_type == "BUY" and signal.strength == "STRONG":
                _auto_open_all_strategies(state, signal)

    # シグナル履歴保存
    state["signals_history"] = state.get("signals_history", [])[-100:]
    for sig in all_signals:
        if sig.signal_type != "HOLD":
            state["signals_history"].append({
                "ticker": sig.ticker, "name": sig.name,
                "type": sig.signal_type, "score": sig.final_score,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })

    state["last_full_screening"] = datetime.now().isoformat()
    return signal_count


def _auto_open_all_strategies(state: dict, signal):
    """全戦略に対してポジションを自動開設"""
    indicators = signal.indicators
    price = indicators["current_price"]
    atr = indicators.get("atr", 0)
    if atr <= 0:
        return

    sl = calculate_stop_loss(price, atr)
    tp = calculate_take_profit(price, atr)
    ai_conf = signal.ai_assessment.get("confidence", 0) if signal.ai_assessment else 0

    for strategy_key, strategy_config in STRATEGIES.items():
        if not can_open_position_strategy(state, strategy_key):
            continue
        if check_daily_loss_limit_strategy(state, strategy_key):
            continue

        # 既に同じ銘柄を保有していたらスキップ
        portfolio = state["strategies"][strategy_key]
        existing_tickers = [p["ticker"] for p in portfolio["positions"]]
        if signal.ticker in existing_tickers:
            continue

        capital = portfolio["capital"]
        max_ratio = strategy_config.get("max_position_ratio", 0.20)
        shares = calculate_position_size(capital, price, atr, max_position_ratio=max_ratio)
        if shares <= 0 or shares * price > capital:
            continue

        open_position(
            state, strategy_key, signal.ticker, signal.name, price, shares, sl, tp,
            signal_score=signal.final_score,
            signal_reasons=[r[:50] for r in signal.reasons[:5]],
            ai_confidence=ai_conf,
        )
        label = strategy_config["label"]
        print(f"  🟢 [{label}] ポジション開設: {signal.name} {shares}株 @ {price:,.0f}円")


def main():
    """メインエントリポイント"""
    now = datetime.now(JST)
    print(f"{'='*50}")
    print(f"[MAIN] スウィングトレードBot起動 - {now.strftime('%Y-%m-%d %H:%M:%S')} JST")
    print(f"{'='*50}")

    # 環境変数の診断
    from config import DISCORD_WEBHOOK_URL, ANTHROPIC_API_KEY
    if DISCORD_WEBHOOK_URL:
        print(f"[CONFIG] Discord Webhook: 設定済み（{len(DISCORD_WEBHOOK_URL)}文字）")
    else:
        print(f"[CONFIG] Discord Webhook: 未設定！GitHub Secretsを確認してください")
    if ANTHROPIC_API_KEY:
        print(f"[CONFIG] Anthropic API: 設定済み")
    else:
        print(f"[CONFIG] Anthropic API: 未設定（フォールバックモード）")

    print(f"[CONFIG] 戦略数: {len(STRATEGIES)}")
    for key, s in STRATEGIES.items():
        print(f"  {s['emoji']} {s['label']}")

    state = load_state()

    # === 起動通知 ===
    try:
        send_startup_notification(state)
    except Exception as e:
        print(f"[WARN] 起動通知エラー: {e}")

    # === 祝日・休場日チェック ===
    if not is_market_open(now):
        print(f"[MAIN] 本日は休場日です。スクリーニングをスキップします。")
        save_state(state)
        print(f"\n[MAIN] 完了 - state.json保存済み")
        return

    # === Phase 1: 既存ポジション監視 ===
    try:
        check_existing_positions(state)
    except Exception as e:
        print(f"[ERROR] ポジション監視エラー: {e}")
        traceback.print_exc()

    # === Phase 2: フルスクリーニング ===
    signal_count = 0
    try:
        if now.minute < 15:
            signal_count = run_full_screening_and_signals(state)
        else:
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

    # === デイリーサマリー（14:45以降） ===
    try:
        if now.hour == 5 and now.minute >= 45:  # UTC 5:45 = JST 14:45
            send_strategies_summary(state, signal_count)
    except Exception as e:
        print(f"[ERROR] デイリーサマリーエラー: {e}")

    save_state(state)
    print(f"\n[MAIN] 完了 - state.json保存済み")


if __name__ == "__main__":
    main()
