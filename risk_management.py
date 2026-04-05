"""リスク管理ルール（マルチ戦略対応）"""
from config import (
    MAX_POSITION_RATIO, MAX_TOTAL_EXPOSURE, MAX_POSITIONS,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, STRATEGIES,
)


def calculate_position_size(
    capital: float, price: float, atr: float,
    max_position_ratio: float = MAX_POSITION_RATIO,
    risk_per_trade: float = 0.02,
) -> int:
    """ATRベースのポジションサイジング（日本株100株単位対応）"""
    if price <= 0 or atr <= 0 or capital <= 0:
        return 0

    # 最大投入額
    max_invest = capital * max_position_ratio

    # 投入額で買える最大株数（100株単位）
    max_shares = int(max_invest / price / 100) * 100

    # リスクベースの株数計算
    risk_amount = capital * risk_per_trade
    per_share_risk = atr * 2
    risk_shares = int(risk_amount / per_share_risk / 100) * 100

    # リスクベースと最大投入額の小さい方を採用
    shares = min(risk_shares, max_shares) if risk_shares > 0 else max_shares

    # 100株未満でも買える場合は100株で試す
    if shares == 0 and price * 100 <= max_invest:
        shares = 100

    # 最終チェック: 購入金額が資金を超えないか
    if shares * price > capital:
        return 0

    return shares


def can_open_position_strategy(state: dict, strategy_key: str) -> bool:
    """指定戦略で新規ポジション開設可能か"""
    strategy = STRATEGIES.get(strategy_key, {})
    portfolio = state.get("strategies", {}).get(strategy_key, {})
    positions = portfolio.get("positions", [])
    capital = portfolio.get("capital", 0)

    max_pos = strategy.get("max_positions", MAX_POSITIONS)
    max_exp = strategy.get("max_total_exposure", MAX_TOTAL_EXPOSURE)

    if len(positions) >= max_pos:
        return False

    total_invested = sum(p["entry_price"] * p["quantity"] for p in positions)
    total_value = capital + total_invested
    if total_value > 0 and total_invested / total_value >= max_exp:
        return False

    return True


def can_open_position(state: dict) -> bool:
    """後方互換用"""
    return True


def calculate_stop_loss(entry_price: float, atr: float) -> float:
    atr_stop = entry_price - atr * 2
    pct_stop = entry_price * (1 + STOP_LOSS_PCT)
    return max(atr_stop, pct_stop)


def calculate_take_profit(entry_price: float, atr: float) -> float:
    atr_target = entry_price + atr * 3
    pct_target = entry_price * (1 + TAKE_PROFIT_PCT)
    return max(atr_target, pct_target)


def calculate_risk_reward_ratio(entry: float, stop_loss: float, take_profit: float) -> float:
    risk = abs(entry - stop_loss)
    reward = abs(take_profit - entry)
    if risk <= 0:
        return 0
    return reward / risk


def check_daily_loss_limit_strategy(state: dict, strategy_key: str, limit_pct: float = 0.05) -> bool:
    """指定戦略の日次損失限度チェック"""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    portfolio = state.get("strategies", {}).get(strategy_key, {})
    daily_pnl = portfolio.get("daily_pnl", {})
    capital = portfolio.get("capital", 0)
    today_loss = daily_pnl.get(today, 0)
    if capital > 0 and today_loss < -(capital * limit_pct):
        return True
    return False


def check_daily_loss_limit(state: dict, limit_pct: float = 0.05) -> bool:
    """後方互換用"""
    return False
