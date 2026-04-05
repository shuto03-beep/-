"""リスク管理ルール"""
from config import (
    MAX_POSITION_RATIO, MAX_TOTAL_EXPOSURE, MAX_POSITIONS,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, TRAILING_STOP_PCT,
)


def calculate_position_size(
    capital: float, price: float, atr: float, risk_per_trade: float = 0.02
) -> int:
    """ATRベースのポジションサイジング"""
    if price <= 0 or atr <= 0:
        return 0

    # リスク金額 = 資金 × リスク率
    risk_amount = capital * risk_per_trade
    # 1株あたりリスク = ATR × 2（ストップロス幅の近似）
    per_share_risk = atr * 2
    # 株数 = リスク金額 / 1株リスク
    shares = int(risk_amount / per_share_risk)

    # 最大投入額制限
    max_shares_by_capital = int((capital * MAX_POSITION_RATIO) / price)
    shares = min(shares, max_shares_by_capital)

    # 最低1株、100株単位に丸め
    if shares < 100:
        shares = 100
    else:
        shares = (shares // 100) * 100

    # 投入額が資金を超えないか
    if shares * price > capital * MAX_POSITION_RATIO:
        shares = int((capital * MAX_POSITION_RATIO) / price / 100) * 100

    return max(shares, 0)


def can_open_position(state: dict) -> bool:
    """新規ポジション開設可能か"""
    positions = state.get("portfolio", {}).get("positions", [])
    capital = state.get("portfolio", {}).get("capital", 0)

    # ポジション数チェック
    if len(positions) >= MAX_POSITIONS:
        return False

    # 投下率チェック
    total_exposure = sum(p["entry_price"] * p["quantity"] for p in positions)
    if capital > 0 and total_exposure / capital >= MAX_TOTAL_EXPOSURE:
        return False

    return True


def calculate_stop_loss(entry_price: float, atr: float) -> float:
    """ストップロス価格を計算"""
    # ATRベースとパーセンテージの大きい方を採用
    atr_stop = entry_price - atr * 2
    pct_stop = entry_price * (1 + STOP_LOSS_PCT)
    return max(atr_stop, pct_stop)


def calculate_take_profit(entry_price: float, atr: float) -> float:
    """利確価格を計算"""
    atr_target = entry_price + atr * 3
    pct_target = entry_price * (1 + TAKE_PROFIT_PCT)
    return max(atr_target, pct_target)


def calculate_risk_reward_ratio(entry: float, stop_loss: float, take_profit: float) -> float:
    """リスクリワード比を計算"""
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    if risk <= 0:
        return 0
    return reward / risk


def check_daily_loss_limit(state: dict, limit_pct: float = 0.05) -> bool:
    """日次損失限度をチェック。True = 限度超過"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    daily_pnl = state.get("portfolio", {}).get("daily_pnl", {})
    capital = state.get("portfolio", {}).get("capital", 0)
    today_loss = daily_pnl.get(today, 0)
    if capital > 0 and today_loss < -(capital * limit_pct):
        return True
    return False
