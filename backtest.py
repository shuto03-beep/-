"""バックテストエンジン - 過去データで戦略を検証

目的:
- 現在の3戦略（A/B/C）を過去データで仮想運用
- 勝率、収益率、最大ドローダウンを計算
- ライブ運用前に戦略の妥当性を検証
"""
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from config import (
    STRATEGIES, INITIAL_CAPITAL, STOP_LOSS_PCT, TAKE_PROFIT_PCT,
    TRAILING_STOP_PCT, HOLDING_PERIOD_MAX, load_universe,
    BUY_SCORE_THRESHOLD, STRONG_SIGNAL_THRESHOLD,
)
from technical_analysis import calculate_all_indicators
from signals import calculate_buy_score, calculate_sell_score
from risk_management import (
    calculate_position_size, calculate_stop_loss, calculate_take_profit,
)


@dataclass
class BacktestPosition:
    ticker: str
    name: str
    entry_date: str
    entry_price: float
    quantity: int
    stop_loss: float
    take_profit: float
    highest_price: float
    signal_score: int


@dataclass
class BacktestPortfolio:
    name: str
    capital: float = INITIAL_CAPITAL
    positions: list = field(default_factory=list)
    closed_trades: list = field(default_factory=list)
    max_positions: int = 3
    max_position_ratio: float = 0.30
    equity_curve: list = field(default_factory=list)  # [(date, total_value)]


def fetch_historical_data(tickers: list[str], start: str, end: str) -> dict:
    """バッチで過去データを取得"""
    print(f"[BACKTEST] {len(tickers)}銘柄のデータを取得中...")
    result = {}
    batch_size = 50

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        try:
            data = yf.download(
                batch, start=start, end=end,
                group_by="ticker", progress=False, threads=True,
            )
            if data is None or data.empty:
                continue

            if len(batch) == 1:
                result[batch[0]] = data
            else:
                for ticker in batch:
                    try:
                        td = data[ticker].dropna(how="all")
                        if len(td) > 30:
                            result[ticker] = td
                    except (KeyError, TypeError):
                        continue
        except Exception as e:
            print(f"  [WARN] バッチエラー: {e}")
        time.sleep(1)

    print(f"[BACKTEST] {len(result)}銘柄の取得完了")
    return result


def compute_signal_score(hist_slice: pd.DataFrame) -> tuple[int, list[str]]:
    """過去データの一部からシグナルスコアを計算"""
    indicators = calculate_all_indicators(hist_slice)
    if indicators is None:
        return 0, []

    buy_score, buy_reasons = calculate_buy_score(indicators)
    sell_score, sell_reasons = calculate_sell_score(indicators)
    ta_score = buy_score + sell_score
    return ta_score, buy_reasons if ta_score > 0 else sell_reasons


def simulate_day(
    portfolio: BacktestPortfolio,
    current_date: str,
    all_data: dict,
) -> None:
    """1日分のシミュレーション"""
    # 1. 既存ポジションのチェック（決済判定）
    for pos in portfolio.positions[:]:
        hist = all_data.get(pos.ticker)
        if hist is None or current_date not in hist.index.strftime("%Y-%m-%d").tolist():
            continue

        day_data = hist.loc[hist.index.strftime("%Y-%m-%d") == current_date]
        if day_data.empty:
            continue
        current_price = float(day_data["Close"].iloc[0])

        # トレーリングストップ更新
        if current_price > pos.highest_price:
            pos.highest_price = current_price

        # 決済判定
        exit_reason = None
        if current_price <= pos.stop_loss:
            exit_reason = "STOP_LOSS"
        elif current_price >= pos.take_profit:
            exit_reason = "TAKE_PROFIT"
        elif pos.highest_price >= pos.entry_price * 1.03:
            trailing_price = pos.highest_price * (1 - TRAILING_STOP_PCT)
            trailing_price = max(trailing_price, pos.entry_price * 1.005)
            if current_price < trailing_price:
                exit_reason = "TRAILING_STOP"
        else:
            entry_dt = datetime.strptime(pos.entry_date, "%Y-%m-%d")
            curr_dt = datetime.strptime(current_date, "%Y-%m-%d")
            if (curr_dt - entry_dt).days >= HOLDING_PERIOD_MAX:
                exit_reason = "MAX_HOLDING"

        if exit_reason:
            pnl = (current_price - pos.entry_price) * pos.quantity
            portfolio.capital += current_price * pos.quantity
            portfolio.closed_trades.append({
                "ticker": pos.ticker,
                "name": pos.name,
                "entry_date": pos.entry_date,
                "exit_date": current_date,
                "entry_price": pos.entry_price,
                "exit_price": current_price,
                "pnl": pnl,
                "pnl_pct": (current_price - pos.entry_price) / pos.entry_price,
                "reason": exit_reason,
                "signal_score": pos.signal_score,
            })
            portfolio.positions.remove(pos)

    # 2. 新規エントリー判定
    if len(portfolio.positions) < portfolio.max_positions:
        candidates = []

        for ticker, hist in all_data.items():
            if ticker in [p.ticker for p in portfolio.positions]:
                continue

            # current_dateまでのデータを切り出し
            hist_slice = hist[hist.index.strftime("%Y-%m-%d") <= current_date]
            if len(hist_slice) < 75:
                continue

            try:
                indicators = calculate_all_indicators(hist_slice)
                if indicators is None:
                    continue
                buy_score, _ = calculate_buy_score(indicators)
                sell_score, _ = calculate_sell_score(indicators)
                score = buy_score + sell_score

                if score >= 50:  # 新しい閾値
                    candidates.append({
                        "ticker": ticker,
                        "score": score,
                        "indicators": indicators,
                    })
            except Exception:
                continue

        # スコア順にソート、上位からエントリー
        candidates.sort(key=lambda x: x["score"], reverse=True)

        for cand in candidates:
            if len(portfolio.positions) >= portfolio.max_positions:
                break
            if portfolio.capital <= 0:
                break

            indicators = cand["indicators"]
            price = indicators["current_price"]
            atr = indicators.get("atr", 0)
            if atr <= 0 or price <= 0:
                continue

            shares = calculate_position_size(
                portfolio.capital, price, atr,
                max_position_ratio=portfolio.max_position_ratio,
            )
            if shares <= 0 or shares * price > portfolio.capital:
                continue

            sl = calculate_stop_loss(price, atr)
            tp = calculate_take_profit(price, atr)

            portfolio.positions.append(BacktestPosition(
                ticker=cand["ticker"],
                name=cand["ticker"],
                entry_date=current_date,
                entry_price=price,
                quantity=shares,
                stop_loss=sl,
                take_profit=tp,
                highest_price=price,
                signal_score=cand["score"],
            ))
            portfolio.capital -= price * shares

    # 3. 資産曲線を記録
    invested = sum(p.entry_price * p.quantity for p in portfolio.positions)
    total_value = portfolio.capital + invested
    portfolio.equity_curve.append((current_date, total_value))


def run_backtest(days: int = 90, max_stocks: int = 100) -> dict:
    """バックテストを実行"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 100)  # 指標計算用に余裕

    print(f"[BACKTEST] {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')} ({days}日間)")

    # ユニバース（流動性の高い銘柄に限定）
    universe = load_universe()[:max_stocks]
    tickers = [s["ticker"] for s in universe]
    ticker_names = {s["ticker"]: s["name"] for s in universe}

    # データ取得
    all_data = fetch_historical_data(
        tickers,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
    )

    if not all_data:
        print("[BACKTEST] データ取得失敗")
        return {}

    # 3戦略のポートフォリオ初期化
    portfolios = {}
    for key, config in STRATEGIES.items():
        portfolios[key] = BacktestPortfolio(
            name=config["label"],
            max_positions=config["max_positions"],
            max_position_ratio=config["max_position_ratio"],
        )

    # シミュレーション対象日（実際のdays日分）
    trading_dates = []
    sample_ticker = list(all_data.keys())[0]
    all_dates = all_data[sample_ticker].index.strftime("%Y-%m-%d").tolist()
    cutoff_date = (end_date - timedelta(days=days)).strftime("%Y-%m-%d")
    trading_dates = [d for d in all_dates if d >= cutoff_date]

    print(f"[BACKTEST] シミュレーション対象日: {len(trading_dates)}日")

    # 日次シミュレーション
    for i, current_date in enumerate(trading_dates):
        if i % 10 == 0:
            print(f"  処理中: {current_date} ({i+1}/{len(trading_dates)})")

        # 銘柄名をセット
        for portfolio in portfolios.values():
            for pos in portfolio.positions:
                if pos.name == pos.ticker:
                    pos.name = ticker_names.get(pos.ticker, pos.ticker)

        for portfolio in portfolios.values():
            simulate_day(portfolio, current_date, all_data)

    # 最終日に残ポジションをクローズ
    final_date = trading_dates[-1] if trading_dates else end_date.strftime("%Y-%m-%d")
    for portfolio in portfolios.values():
        for pos in portfolio.positions[:]:
            hist = all_data.get(pos.ticker)
            if hist is None:
                continue
            last_price = float(hist["Close"].iloc[-1])
            pnl = (last_price - pos.entry_price) * pos.quantity
            portfolio.capital += last_price * pos.quantity
            portfolio.closed_trades.append({
                "ticker": pos.ticker,
                "name": pos.name,
                "entry_date": pos.entry_date,
                "exit_date": final_date,
                "entry_price": pos.entry_price,
                "exit_price": last_price,
                "pnl": pnl,
                "pnl_pct": (last_price - pos.entry_price) / pos.entry_price,
                "reason": "FINAL_CLOSE",
                "signal_score": pos.signal_score,
            })
            portfolio.positions.remove(pos)

    # 結果集計
    results = {}
    for key, portfolio in portfolios.items():
        closed = portfolio.closed_trades
        wins = [t for t in closed if t["pnl"] > 0]
        losses = [t for t in closed if t["pnl"] < 0]
        total_pnl = sum(t["pnl"] for t in closed)
        total_return = (portfolio.capital - INITIAL_CAPITAL) / INITIAL_CAPITAL

        # 最大ドローダウン
        max_dd = 0
        peak = INITIAL_CAPITAL
        for _, value in portfolio.equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        results[key] = {
            "name": portfolio.name,
            "final_capital": portfolio.capital,
            "total_return_pct": total_return * 100,
            "total_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(closed) if closed else 0,
            "avg_win_pct": sum(t["pnl_pct"] for t in wins) / len(wins) if wins else 0,
            "avg_loss_pct": sum(t["pnl_pct"] for t in losses) / len(losses) if losses else 0,
            "total_pnl": total_pnl,
            "max_drawdown_pct": max_dd * 100,
        }

    return results


def format_report(results: dict, days: int) -> str:
    """結果を人間可読なレポートに変換"""
    report = f"\n{'='*60}\n"
    report += f"📊 バックテスト結果（過去{days}日間）\n"
    report += f"{'='*60}\n"

    for key, r in results.items():
        emoji = STRATEGIES[key]["emoji"]
        report += f"\n{emoji} {r['name']}\n"
        report += f"  💰 最終資産: {r['final_capital']:,.0f}円 "
        report += f"({'📈' if r['total_return_pct'] >= 0 else '📉'}{r['total_return_pct']:+.2f}%)\n"
        report += f"  📊 トレード: {r['total_trades']}件（勝{r['wins']} 負{r['losses']}）\n"
        if r['total_trades'] > 0:
            report += f"  🎯 勝率: {r['win_rate']*100:.0f}%\n"
            report += f"  📈 平均利益: {r['avg_win_pct']*100:+.2f}%\n"
            report += f"  📉 平均損失: {r['avg_loss_pct']*100:+.2f}%\n"
        report += f"  📉 最大DD: {r['max_drawdown_pct']:.2f}%\n"

    # ベスト戦略
    if results:
        best = max(results.items(), key=lambda x: x[1]["total_return_pct"])
        report += f"\n🏆 ベスト戦略: {STRATEGIES[best[0]]['emoji']} {best[1]['name']} "
        report += f"({best[1]['total_return_pct']:+.2f}%)\n"

    report += f"{'='*60}\n"
    return report


if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    max_stocks = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    results = run_backtest(days=days, max_stocks=max_stocks)
    report = format_report(results, days)
    print(report)

    # レポートをファイルに保存
    output_file = Path(__file__).parent / "data" / "backtest_report.txt"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    # JSON形式でも保存
    json_file = Path(__file__).parent / "data" / "backtest_result.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump({
            "run_at": datetime.now().isoformat(),
            "days": days,
            "max_stocks": max_stocks,
            "results": results,
        }, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nレポート保存: {output_file}")
    print(f"JSON保存: {json_file}")
