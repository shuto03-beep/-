"""マルチファクターシグナル生成（学習重み対応）"""
import json
from dataclasses import dataclass, field
from config import (
    DEFAULT_WEIGHTS, BUY_SCORE_THRESHOLD, SELL_SCORE_THRESHOLD,
    STRONG_SIGNAL_THRESHOLD, LEARNING_FILE,
)


@dataclass
class Signal:
    ticker: str
    name: str
    signal_type: str         # "BUY" / "SELL" / "HOLD"
    strength: str            # "STRONG" / "MEDIUM" / "WEAK"
    ta_score: int            # テクニカルスコア(-100~100)
    final_score: int         # 最終スコア（TA + ヒストリカル + AI）
    reasons: list[str] = field(default_factory=list)
    indicators: dict = field(default_factory=dict)
    historical: dict = field(default_factory=dict)
    ai_assessment: dict = field(default_factory=dict)


def load_weights() -> dict:
    """learning.jsonから学習済み重みを読み込む"""
    try:
        with open(LEARNING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("weights", DEFAULT_WEIGHTS)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_WEIGHTS.copy()


def calculate_buy_score(indicators: dict, weights: dict = None) -> tuple[int, list[str]]:
    """買いスコアを計算（0~100）"""
    if weights is None:
        weights = load_weights()

    score = 0
    reasons = []

    # === エントリー位置チェック（天井買い防止）===
    current_price = indicators.get("current_price", 0)
    sr = indicators.get("support_resistance", {})
    recent_high = sr.get("recent_high", current_price)
    recent_low = sr.get("recent_low", current_price)

    if recent_high > recent_low > 0:
        # 現在価格が直近レンジのどこにいるか（0-1、0=底、1=天井）
        position_in_range = (current_price - recent_low) / (recent_high - recent_low)

        # 天井付近・高値圏を厳しく減点（実績反映）
        if position_in_range >= 0.90:
            score -= 15  # -10 → -15に強化
            reasons.append(f"⚠️ 直近高値圏（レンジ{position_in_range*100:.0f}%）")
        elif position_in_range >= 0.75:
            score -= 5  # 新規追加：75%以上は減点
            reasons.append(f"⚠️ 高値圏（レンジ{position_in_range*100:.0f}%）")
        elif position_in_range <= 0.30:
            score += 10  # +8 → +10に強化
            reasons.append(f"✨ 直近安値付近（押し目買いチャンス）")
        elif position_in_range <= 0.60:
            score += 3
            reasons.append("レンジ中位（適正エントリー）")

    # 1. MAクロス
    if indicators.get("golden_cross"):
        score += weights["ma_cross"]
        reasons.append("ゴールデンクロス（SMA5×SMA25）")

    # 2. MAトレンド
    price = indicators.get("current_price", 0)
    sma25 = indicators.get("sma25", 0)
    sma75 = indicators.get("sma75", 0)
    if price and sma25 and sma75 and price > sma25 > sma75:
        score += weights["ma_trend"]
        reasons.append("上昇トレンド（価格>SMA25>SMA75）")

    # 3. MACD
    if indicators.get("macd_cross_buy") or (
        indicators.get("histogram_increasing") and indicators.get("macd_value", 0) > indicators.get("macd_signal", 0)
    ):
        score += weights["macd"]
        reasons.append("MACD買いシグナル")

    # 4. RSI（厳格化：60以上は減点、押し目優遇）
    rsi = indicators.get("rsi", 50)
    if rsi < 30:
        score += weights["rsi"]
        reasons.append(f"RSI売られすぎ（{rsi:.1f}）")
    elif 30 <= rsi <= 50:
        score += weights["rsi"]
        reasons.append(f"RSI回復中（{rsi:.1f}）")
    elif 50 < rsi <= 60:
        score += weights["rsi"] // 3  # やや弱めに
        reasons.append(f"RSI中立圏（{rsi:.1f}）")
    elif 60 < rsi <= 70:
        score -= 5  # 実績から減点
        reasons.append(f"⚠️ RSI買われすぎ気味（{rsi:.1f}）")
    elif rsi > 70:
        score -= 10  # 大幅減点
        reasons.append(f"⚠️ RSI過熱（{rsi:.1f}）")
    if indicators.get("rsi_divergence") == "BULLISH":
        score += 5
        reasons.append("RSI強気ダイバージェンス")

    # 5. ボリンジャーバンド
    bb_pctb = indicators.get("bb_percent_b", 0.5)
    if bb_pctb < 0.2:
        score += weights["bollinger"]
        reasons.append("ボリンジャーバンド下限接触")
    elif 0.4 < bb_pctb < 0.6 and indicators.get("trend") == "UPTREND":
        score += weights["bollinger"] // 2
        reasons.append("ボリンジャーミドル付近（上昇トレンド）")

    # 6. 出来高
    vol_ratio = indicators.get("volume_ratio", 1.0)
    if vol_ratio >= 1.5:
        score += weights["volume"]
        reasons.append(f"出来高急増（{vol_ratio:.1f}倍）")
    elif vol_ratio >= 1.2:
        score += weights["volume"] // 2
        reasons.append(f"出来高増加（{vol_ratio:.1f}倍）")
    elif vol_ratio >= 1.2:
        score += weights["volume"] // 2
        reasons.append(f"出来高増加（{vol_ratio:.1f}倍）")

    # 7. ストキャスティクス
    k = indicators.get("stoch_k", 50)
    d = indicators.get("stoch_d", 50)
    if k > d and k < 30:
        score += weights["stochastic"]
        reasons.append(f"ストキャスティクス買い（%K={k:.0f}）")
    elif k > d and k < 50:
        score += weights["stochastic"] // 2
        reasons.append("ストキャスティクス上昇")

    # 8. 一目均衡表
    cloud = indicators.get("ichimoku_cloud_status", "INSIDE")
    tenkan = indicators.get("tenkan_above_kijun", False)
    if cloud == "ABOVE":
        score += weights["ichimoku"]
        reasons.append("一目均衡表: 雲上抜け")
    elif tenkan:
        score += weights["ichimoku"] // 2
        reasons.append("一目均衡表: 転換線>基準線")

    return min(score, 100), reasons


def calculate_sell_score(indicators: dict, weights: dict = None) -> tuple[int, list[str]]:
    """売りスコアを計算（0~-100）"""
    if weights is None:
        weights = load_weights()

    score = 0
    reasons = []

    if indicators.get("dead_cross"):
        score -= weights["ma_cross"]
        reasons.append("デッドクロス（SMA5×SMA25）")

    price = indicators.get("current_price", 0)
    sma25 = indicators.get("sma25", 0)
    sma75 = indicators.get("sma75", 0)
    if price and sma25 and sma75 and price < sma25 < sma75:
        score -= weights["ma_trend"]
        reasons.append("下降トレンド（価格<SMA25<SMA75）")

    if indicators.get("macd_cross_sell"):
        score -= weights["macd"]
        reasons.append("MACD売りシグナル")

    rsi = indicators.get("rsi", 50)
    if rsi >= 70:
        score -= weights["rsi"]
        reasons.append(f"RSI過買い（{rsi:.1f}）")
    if indicators.get("rsi_divergence") == "BEARISH":
        score -= 5
        reasons.append("RSI弱気ダイバージェンス")

    bb_pctb = indicators.get("bb_percent_b", 0.5)
    if bb_pctb > 0.95:
        score -= weights["bollinger"]
        reasons.append("ボリンジャー上限突破")

    k = indicators.get("stoch_k", 50)
    d = indicators.get("stoch_d", 50)
    if k < d and k > 80:
        score -= weights["stochastic"]
        reasons.append(f"ストキャスティクス売り（%K={k:.0f}）")

    cloud = indicators.get("ichimoku_cloud_status", "INSIDE")
    if cloud == "BELOW":
        score -= weights["ichimoku"]
        reasons.append("一目均衡表: 雲下抜け")

    # 出来高チェック（売りシグナルでも有効化）
    vol_ratio = indicators.get("volume_ratio", 1.0)
    if vol_ratio >= 1.5 and score < 0:
        score -= weights["volume"] // 2
        reasons.append(f"売り出来高増（{vol_ratio:.1f}倍）")

    # レジスタンス突破失敗の検知
    current_price = indicators.get("current_price", 0)
    sr = indicators.get("support_resistance", {})
    recent_high = sr.get("recent_high", current_price)
    if recent_high > 0 and current_price > 0:
        if 0.97 <= current_price / recent_high <= 1.0:
            score -= 5
            reasons.append("直近高値で跳ね返り")

    return max(score, -100), reasons


def compute_final_score(
    ta_score: int,
    historical_data: dict = None,
    ai_assessment: dict = None,
) -> int:
    """TA + ヒストリカル + AI の最終スコアを計算"""
    hist_win_rate = 0.5
    if historical_data and isinstance(historical_data, dict):
        outcomes = historical_data.get("pattern_outcomes", {})
        if outcomes.get("pattern_count", 0) >= 3:
            hist_win_rate = outcomes.get("win_rate", 0.5)

    # ヒストリカル勝率を-100~100スケールに変換
    hist_score = (hist_win_rate - 0.5) * 200  # 50%→0, 70%→40, 80%→60

    if ai_assessment and ai_assessment.get("confidence"):
        ai_conf = ai_assessment["confidence"]
        if ai_assessment.get("recommendation") == "SELL":
            ai_conf = -ai_conf
        elif ai_assessment.get("recommendation") == "HOLD":
            ai_conf = 0
        # AI利用時: TA 50% + ヒストリカル 20% + AI 30%
        final = ta_score * 0.5 + hist_score * 0.2 + ai_conf * 0.3
    else:
        # AIなし: TA 70% + ヒストリカル 30%
        final = ta_score * 0.7 + hist_score * 0.3

    return int(round(final))


def generate_signal(
    ticker: str,
    name: str,
    indicators: dict,
    historical_data: dict = None,
    ai_assessment: dict = None,
) -> Signal:
    """最終的なシグナルを生成"""
    buy_score, buy_reasons = calculate_buy_score(indicators)
    sell_score, sell_reasons = calculate_sell_score(indicators)

    # 買いスコアと売りスコアのネットスコア
    ta_score = buy_score + sell_score  # sell_scoreは負の値

    final_score = compute_final_score(ta_score, historical_data, ai_assessment)

    # 市場サイクル補正（曜日・時間帯・月次・SQ）
    try:
        from market_cycles import get_total_cycle_adjustment
        from datetime import datetime, timezone, timedelta
        jst_now = datetime.now(timezone(timedelta(hours=9)))
        cycle = get_total_cycle_adjustment(jst_now)
        cycle_bias = cycle["total_bias"]
        final_score += cycle_bias
        if cycle["reasons"]:
            reasons_list = buy_reasons if final_score >= 0 else sell_reasons
            for r in cycle["reasons"][:3]:
                reasons_list.append(f"📅 {r}")
    except Exception:
        cycle_bias = 0

    # シグナル判定
    if final_score >= BUY_SCORE_THRESHOLD:
        signal_type = "BUY"
        reasons = buy_reasons
    elif final_score <= SELL_SCORE_THRESHOLD:
        signal_type = "SELL"
        reasons = sell_reasons
    else:
        signal_type = "HOLD"
        reasons = buy_reasons + sell_reasons if abs(final_score) > 20 else []

    # 強度判定
    abs_score = abs(final_score)
    if abs_score >= STRONG_SIGNAL_THRESHOLD:
        strength = "STRONG"
    elif abs_score >= BUY_SCORE_THRESHOLD:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    # ヒストリカル根拠を追加
    if historical_data:
        outcomes = historical_data.get("pattern_outcomes", {})
        if outcomes.get("pattern_count", 0) >= 3:
            reasons.append(
                f"類似パターン{outcomes['pattern_count']}件: "
                f"勝率{outcomes['win_rate']:.0%}, "
                f"平均リターン{outcomes['avg_return']:.1%}"
            )

    return Signal(
        ticker=ticker, name=name, signal_type=signal_type,
        strength=strength, ta_score=ta_score, final_score=final_score,
        reasons=reasons, indicators=indicators,
        historical=historical_data or {},
        ai_assessment=ai_assessment or {},
    )
