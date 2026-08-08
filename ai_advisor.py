"""Claude API判断補助（フォールバック付き）"""
import json
from config import ANTHROPIC_API_KEY, AI_ENABLED, AI_TIMEOUT, AI_MODEL


def _fmt(value, spec: str) -> str:
    """数値なら指定フォーマット、そうでなければ'N/A'を返す（APIプロンプト構築用）"""
    if isinstance(value, (int, float)):
        return format(value, spec)
    return "N/A"


def get_ai_assessment(ticker: str, name: str, indicators: dict, historical_data: dict = None) -> dict:
    """Claude APIでAI分析を取得。失敗時はフォールバック。"""
    if not AI_ENABLED or not ANTHROPIC_API_KEY:
        return get_fallback_assessment(indicators)

    try:
        return _call_claude_api(ticker, name, indicators, historical_data)
    except Exception as e:
        print(f"  [AI] API呼び出し失敗（{ticker}）: {e}")
        return get_fallback_assessment(indicators)


def _call_claude_api(ticker: str, name: str, indicators: dict, historical_data: dict = None) -> dict:
    """Claude APIを呼び出して分析結果を返す"""
    import anthropic

    prompt = _build_analysis_prompt(ticker, name, indicators, historical_data)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=AI_MODEL,
        max_tokens=500,
        timeout=AI_TIMEOUT,
        messages=[{"role": "user", "content": prompt}],
        system="あなたは日本株のスウィングトレード専門のアナリストです。テクニカルデータに基づき、簡潔に分析してください。必ず以下のJSON形式で回答してください: {\"confidence\": 0-100の数値, \"recommendation\": \"BUY\"/\"SELL\"/\"HOLD\", \"reasoning\": \"分析コメント\", \"risk_assessment\": \"リスク評価\"}",
    )

    # レスポンスからJSON抽出
    text = response.content[0].text.strip()
    # JSON部分を抽出
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        result = json.loads(text[start:end])
        return {
            "confidence": min(100, max(0, int(result.get("confidence", 50)))),
            "recommendation": result.get("recommendation", "HOLD"),
            "reasoning": result.get("reasoning", ""),
            "risk_assessment": result.get("risk_assessment", ""),
            "source": "claude_api",
        }

    return get_fallback_assessment(indicators)


def _build_analysis_prompt(ticker: str, name: str, indicators: dict, historical_data: dict = None) -> str:
    """分析プロンプトを構築"""
    prompt = f"""以下の銘柄のテクニカル分析データを評価し、今後1-3営業日の見通しを判断してください。

## 銘柄情報
- 銘柄: {name} ({ticker})
- 現在価格: {indicators.get('current_price', 'N/A')}円
- トレンド: {indicators.get('trend', 'N/A')}

## テクニカル指標
- RSI(14): {_fmt(indicators.get('rsi'), '.1f')}
- MACD: {'買いクロス' if indicators.get('macd_cross_buy') else '売りクロス' if indicators.get('macd_cross_sell') else 'ニュートラル'}
- ヒストグラム: {'増加中' if indicators.get('histogram_increasing') else '減少中'}
- ボリンジャー%B: {_fmt(indicators.get('bb_percent_b'), '.2f')}
- ストキャスティクス: %K={_fmt(indicators.get('stoch_k'), '.0f')}, %D={_fmt(indicators.get('stoch_d'), '.0f')}
- 一目均衡表: 雲{indicators.get('ichimoku_cloud_status', 'N/A')}, 転換線{'>' if indicators.get('tenkan_above_kijun') else '<'}基準線
- 出来高比率: {_fmt(indicators.get('volume_ratio'), '.1f')}倍
- ATR: {_fmt(indicators.get('atr'), '.1f')}
- ゴールデンクロス: {'あり' if indicators.get('golden_cross') else 'なし'}
- デッドクロス: {'あり' if indicators.get('dead_cross') else 'なし'}
- RSIダイバージェンス: {indicators.get('rsi_divergence', 'NONE')}"""

    if historical_data:
        outcomes = historical_data.get("pattern_outcomes", {})
        if outcomes.get("pattern_count", 0) > 0:
            prompt += f"""

## ヒストリカルパターン分析（過去10年）
- 類似パターン数: {outcomes.get('pattern_count', 0)}件
- パターン後勝率: {outcomes.get('win_rate', 0):.0%}
- 平均リターン: {outcomes.get('avg_return', 0):.1%}
- 最大ドローダウン: {outcomes.get('max_drawdown', 0):.1%}"""

        regime = historical_data.get("market_regime", "UNKNOWN")
        prompt += f"\n- 市場環境: {regime}"

    prompt += """

上記データに基づき、JSON形式で回答してください。"""

    return prompt


def get_fallback_assessment(indicators: dict) -> dict:
    """AI利用不可時のルールベース判断"""
    rsi = indicators.get("rsi", 50)
    trend = indicators.get("trend", "SIDEWAYS")
    vol_ratio = indicators.get("volume_ratio", 1.0)
    cloud = indicators.get("ichimoku_cloud_status", "INSIDE")

    # ルールベースの確信度計算
    confidence = 50
    recommendation = "HOLD"
    reasoning_parts = []

    # RSIベース
    if rsi < 30:
        confidence += 15
        recommendation = "BUY"
        reasoning_parts.append("RSI売られすぎ圏")
    elif rsi > 70:
        confidence += 15
        recommendation = "SELL"
        reasoning_parts.append("RSI買われすぎ圏")

    # トレンドベース
    if trend == "UPTREND" and recommendation != "SELL":
        confidence += 10
        recommendation = "BUY"
        reasoning_parts.append("上昇トレンド")
    elif trend == "DOWNTREND" and recommendation != "BUY":
        confidence += 10
        recommendation = "SELL"
        reasoning_parts.append("下降トレンド")

    # 出来高
    if vol_ratio > 1.5:
        confidence += 5
        reasoning_parts.append("出来高増加")

    # 一目均衡表
    if cloud == "ABOVE" and recommendation != "SELL":
        confidence += 10
        reasoning_parts.append("雲上")
    elif cloud == "BELOW" and recommendation != "BUY":
        confidence += 10
        reasoning_parts.append("雲下")

    return {
        "confidence": min(100, confidence),
        "recommendation": recommendation,
        "reasoning": "フォールバック判断: " + "、".join(reasoning_parts) if reasoning_parts else "判断材料不足",
        "risk_assessment": "",
        "source": "fallback",
    }
