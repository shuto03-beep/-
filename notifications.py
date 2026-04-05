"""Discord通知（リッチフォーマット）"""
import requests
from config import DISCORD_WEBHOOK_URL


def _send_discord(message: str):
    """Discordにメッセージを送信"""
    if not DISCORD_WEBHOOK_URL:
        print(f"[DISCORD] Webhook未設定 → コンソール出力:\n{message}")
        return

    # discordapp.com → discord.com に正規化（リダイレクトでPOSTがGETになる問題を回避）
    url = DISCORD_WEBHOOK_URL.replace("https://discordapp.com/", "https://discord.com/")

    # Discord文字数制限（2000文字）対応
    chunks = [message[i:i + 1990] for i in range(0, len(message), 1990)]
    for chunk in chunks:
        try:
            payload = {"content": chunk}
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            print(f"[DISCORD] 送信成功 (status: {resp.status_code})")
        except Exception as e:
            print(f"[DISCORD] 送信エラー: {e}")


def send_signal_notification(signal):
    """買い/売りシグナル通知"""
    if signal.signal_type == "BUY":
        emoji = "🟢"
        label = "買いシグナル"
    elif signal.signal_type == "SELL":
        emoji = "🔴"
        label = "売りシグナル"
    else:
        return  # HOLDは通知しない

    strength_label = {"STRONG": "強い", "MEDIUM": "中程度の", "WEAK": "弱い"}.get(signal.strength, "")

    indicators = signal.indicators
    price = indicators.get("current_price", 0)
    sr = indicators.get("support_resistance", {})
    atr = indicators.get("atr", 0)

    msg = f"""{emoji} 【{strength_label}{label}】{signal.name} ({signal.ticker})
━━━━━━━━━━━━━━━━━━━
📊 最終スコア: {signal.final_score}/100 | TAスコア: {signal.ta_score} | トレンド: {indicators.get('trend', 'N/A')}"""

    # AI判断
    ai = signal.ai_assessment
    if ai and ai.get("source") == "claude_api":
        msg += f"\n🤖 AI判断: {ai.get('recommendation', 'N/A')}（確信度{ai.get('confidence', 0)}%）"

    msg += f"\n💰 現在値: {price:,.0f}円"

    # テクニカル根拠
    if signal.reasons:
        msg += "\n\n📈 テクニカル根拠:"
        for reason in signal.reasons[:8]:
            msg += f"\n  ✅ {reason}"

    # ヒストリカル分析
    hist = signal.historical
    if hist:
        outcomes = hist.get("pattern_outcomes", {})
        if outcomes.get("pattern_count", 0) >= 3:
            msg += f"\n\n📜 ヒストリカル分析:"
            msg += f"\n  類似パターン: {outcomes['pattern_count']}件（過去10年）"
            msg += f"\n  パターン後勝率: {outcomes['win_rate']:.0%}"
            msg += f"\n  平均リターン: {outcomes['avg_return']:+.1%}"
        regime = hist.get("market_regime", "")
        if regime:
            msg += f"\n  市場環境: {regime}"

    # AI分析コメント
    if ai and ai.get("reasoning") and ai.get("source") == "claude_api":
        reasoning = ai["reasoning"][:200]
        msg += f"\n\n🤖 AI分析:\n  「{reasoning}」"

    # 推奨トレード
    if signal.signal_type == "BUY" and price > 0 and atr > 0:
        from risk_management import calculate_stop_loss, calculate_take_profit, calculate_risk_reward_ratio, calculate_position_size
        sl = calculate_stop_loss(price, atr)
        tp = calculate_take_profit(price, atr)
        rr = calculate_risk_reward_ratio(price, sl, tp)
        shares = calculate_position_size(1_000_000, price, atr)
        sl_pct = (sl - price) / price * 100
        tp_pct = (tp - price) / price * 100

        msg += f"\n\n🎯 推奨トレード:"
        msg += f"\n  エントリー: {price:,.0f}円"
        msg += f"\n  ストップロス: {sl:,.0f}円（{sl_pct:+.1f}%）"
        msg += f"\n  利確目標: {tp:,.0f}円（{tp_pct:+.1f}%）"
        msg += f"\n  R/R比: {rr:.2f}"
        msg += f"\n  推奨株数: {shares}株"

    msg += "\n━━━━━━━━━━━━━━━━━━━"
    _send_discord(msg)


def send_exit_notification(trade_record: dict, reason_label: str):
    """ポジション決済通知"""
    pnl = trade_record["pnl"]
    pnl_pct = trade_record["pnl_pct"]
    emoji = "💰" if pnl > 0 else "💸"

    reason_map = {
        "STOP_LOSS": "ストップロス",
        "TAKE_PROFIT": "利確",
        "TRAILING_STOP": "トレーリングストップ",
        "MAX_HOLDING_PERIOD": "保有期間超過",
    }

    msg = f"""{emoji} 【決済】{trade_record['name']} ({trade_record['ticker']})
━━━━━━━━━━━━━━━━━━━
📌 決済理由: {reason_map.get(reason_label, reason_label)}
💹 エントリー: {trade_record['entry_price']:,.0f}円 → 決済: {trade_record['exit_price']:,.0f}円
{'📈' if pnl > 0 else '📉'} 損益: {pnl:+,.0f}円（{pnl_pct:+.1%}）
📅 保有期間: {trade_record['entry_date']} → {trade_record['exit_date']}
━━━━━━━━━━━━━━━━━━━"""

    _send_discord(msg)


def send_position_update(positions: list, current_prices: dict):
    """ポジション状況更新通知"""
    if not positions:
        return

    msg = "📋 保有ポジション状況\n━━━━━━━━━━━━━━━━━━━"
    for pos in positions:
        ticker = pos["ticker"]
        current = current_prices.get(ticker, pos["entry_price"])
        pnl_pct = (current - pos["entry_price"]) / pos["entry_price"]
        emoji = "📈" if pnl_pct > 0 else "📉"
        msg += f"\n{emoji} {pos['name']}: {current:,.0f}円（{pnl_pct:+.1%}）"

    msg += "\n━━━━━━━━━━━━━━━━━━━"
    _send_discord(msg)


def send_daily_summary(portfolio_summary: dict, signal_count: int):
    """デイリーサマリー通知"""
    s = portfolio_summary
    msg = f"""📊 デイリーサマリー
━━━━━━━━━━━━━━━━━━━
💰 総資産: {s['total_value']:,.0f}円
  現金: {s['cash']:,.0f}円
  投資額: {s['total_invested']:,.0f}円
📈 保有ポジション: {s['position_count']}件
📊 本日シグナル: {signal_count}件

📜 累計成績:
  総トレード: {s['total_trades']}件
  勝率: {s['win_rate']:.0%}
  累計損益: {s['total_pnl']:+,.0f}円
━━━━━━━━━━━━━━━━━━━"""

    _send_discord(msg)


def send_learning_report(report: str):
    """学習レポート通知"""
    _send_discord(report)


def send_startup_notification(state: dict):
    """起動通知（Webhook動作確認兼用）"""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone(timedelta(hours=9)))
    positions = state.get("portfolio", {}).get("positions", [])
    capital = state.get("portfolio", {}).get("capital", 0)
    closed = state.get("portfolio", {}).get("closed_trades", [])

    day_names = ["月", "火", "水", "木", "金", "土", "日"]
    day_name = day_names[now.weekday()]

    is_market_day = now.weekday() < 5
    market_status = "取引日" if is_market_day else "休場日"

    msg = f"""🤖 スウィングトレードBot起動
━━━━━━━━━━━━━━━━━━━
🕐 {now.strftime('%Y-%m-%d')}（{day_name}）{now.strftime('%H:%M')} JST
📅 本日: {market_status}
💰 資金: {capital:,.0f}円
📈 保有ポジション: {len(positions)}件
📊 累計トレード: {len(closed)}件
━━━━━━━━━━━━━━━━━━━"""

    _send_discord(msg)
