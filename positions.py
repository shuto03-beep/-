"""ポジション管理・損益追跡"""
import json
from datetime import datetime
from config import STATE_FILE, TRAILING_STOP_PCT, HOLDING_PERIOD_MAX


def load_state() -> dict:
    """state.jsonからポートフォリオ状態を読み込む"""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "portfolio": {
                "capital": 1_000_000,
                "positions": [],
                "closed_trades": [],
                "daily_pnl": {},
            },
            "last_run": None,
            "last_full_screening": None,
            "signals_history": [],
        }


def save_state(state: dict):
    """state.jsonにポートフォリオ状態を保存"""
    state["last_run"] = datetime.now().isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def open_position(
    state: dict, ticker: str, name: str, price: float, quantity: int,
    stop_loss: float, take_profit: float,
    signal_score: int = 0, signal_reasons: list = None, ai_confidence: int = 0,
) -> dict:
    """新規ポジションを開く"""
    position = {
        "ticker": ticker,
        "name": name,
        "entry_price": price,
        "quantity": quantity,
        "entry_date": datetime.now().strftime("%Y-%m-%d"),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "highest_price": price,
        "signal_score": signal_score,
        "signal_reasons": signal_reasons or [],
        "ai_confidence": ai_confidence,
    }
    state["portfolio"]["positions"].append(position)
    # 資金を減らす
    state["portfolio"]["capital"] -= price * quantity
    return position


def close_position(state: dict, ticker: str, exit_price: float, reason: str) -> dict | None:
    """ポジションを決済する"""
    positions = state["portfolio"]["positions"]
    position = None
    idx = None
    for i, p in enumerate(positions):
        if p["ticker"] == ticker:
            position = p
            idx = i
            break

    if position is None:
        return None

    # 損益計算
    pnl = (exit_price - position["entry_price"]) * position["quantity"]
    pnl_pct = (exit_price - position["entry_price"]) / position["entry_price"]

    trade_record = {
        "ticker": ticker,
        "name": position["name"],
        "entry_price": position["entry_price"],
        "exit_price": exit_price,
        "quantity": position["quantity"],
        "entry_date": position["entry_date"],
        "exit_date": datetime.now().strftime("%Y-%m-%d"),
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "reason": reason,
        "signal_score": position.get("signal_score", 0),
        "signal_reasons": position.get("signal_reasons", []),
        "ai_confidence": position.get("ai_confidence", 0),
    }

    # 取引履歴に追加
    state["portfolio"]["closed_trades"].append(trade_record)
    # 資金を戻す
    state["portfolio"]["capital"] += exit_price * position["quantity"]
    # ポジション削除
    positions.pop(idx)

    # 日次損益記録
    today = datetime.now().strftime("%Y-%m-%d")
    daily = state["portfolio"].setdefault("daily_pnl", {})
    daily[today] = daily.get(today, 0) + pnl

    return trade_record


def check_exit_conditions(position: dict, current_price: float) -> str | None:
    """ポジションの終了条件をチェック。理由を返す or None"""
    entry_price = position["entry_price"]

    # ストップロス
    if current_price <= position["stop_loss"]:
        return "STOP_LOSS"

    # 利確
    if current_price >= position["take_profit"]:
        return "TAKE_PROFIT"

    # トレーリングストップ
    highest = position.get("highest_price", entry_price)
    if current_price < highest * (1 - TRAILING_STOP_PCT) and current_price > entry_price:
        return "TRAILING_STOP"

    # 保有期間超過
    entry_date = datetime.strptime(position["entry_date"], "%Y-%m-%d")
    holding_days = (datetime.now() - entry_date).days
    if holding_days >= HOLDING_PERIOD_MAX:
        return "MAX_HOLDING_PERIOD"

    return None


def update_trailing_stop(position: dict, current_price: float):
    """最高値を更新"""
    if current_price > position.get("highest_price", 0):
        position["highest_price"] = current_price


def get_portfolio_summary(state: dict) -> dict:
    """ポートフォリオのサマリーを返す"""
    portfolio = state.get("portfolio", {})
    positions = portfolio.get("positions", [])
    closed = portfolio.get("closed_trades", [])
    capital = portfolio.get("capital", 0)

    total_invested = sum(p["entry_price"] * p["quantity"] for p in positions)
    total_value = capital + total_invested

    # クローズ済みトレードの成績
    if closed:
        wins = sum(1 for t in closed if t["pnl"] > 0)
        total_pnl = sum(t["pnl"] for t in closed)
        win_rate = wins / len(closed)
    else:
        wins = 0
        total_pnl = 0
        win_rate = 0

    return {
        "cash": capital,
        "total_invested": total_invested,
        "total_value": total_value,
        "position_count": len(positions),
        "total_trades": len(closed),
        "wins": wins,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
    }
