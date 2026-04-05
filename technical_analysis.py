"""テクニカル指標計算エンジン - 9種の指標を計算"""
import numpy as np
import pandas as pd


def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    ema_fast = calculate_ema(close, fast)
    ema_slow = calculate_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def calculate_bollinger(close: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    middle = calculate_sma(close, period)
    std = close.rolling(window=period).std()
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    bandwidth = (upper - lower) / middle
    percent_b = (close - lower) / (upper - lower)
    return {
        "upper": upper, "middle": middle, "lower": lower,
        "bandwidth": bandwidth, "percent_b": percent_b,
    }


def calculate_stochastic(hist: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> dict:
    low_min = hist["Low"].rolling(window=k_period).min()
    high_max = hist["High"].rolling(window=k_period).max()
    k = 100 * (hist["Close"] - low_min) / (high_max - low_min)
    d = k.rolling(window=d_period).mean()
    return {"k": k, "d": d}


def calculate_atr(hist: pd.DataFrame, period: int = 14) -> pd.Series:
    high = hist["High"]
    low = hist["Low"]
    close = hist["Close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_ichimoku(hist: pd.DataFrame) -> dict:
    high = hist["High"]
    low = hist["Low"]
    close = hist["Close"]

    # 転換線（9期間）
    tenkan = (high.rolling(9).max() + low.rolling(9).min()) / 2
    # 基準線（26期間）
    kijun = (high.rolling(26).max() + low.rolling(26).min()) / 2
    # 先行スパン1（26期間先行）
    senkou_a = ((tenkan + kijun) / 2).shift(26)
    # 先行スパン2（52期間、26期間先行）
    senkou_b = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    # 遅行スパン（26期間遅行）
    chikou = close.shift(-26)

    # 雲の状態判定（現在の価格と雲の位置関係）
    current_price = close.iloc[-1] if len(close) > 0 else 0
    current_senkou_a = senkou_a.iloc[-1] if len(senkou_a) > 0 and not pd.isna(senkou_a.iloc[-1]) else 0
    current_senkou_b = senkou_b.iloc[-1] if len(senkou_b) > 0 and not pd.isna(senkou_b.iloc[-1]) else 0
    cloud_top = max(current_senkou_a, current_senkou_b)
    cloud_bottom = min(current_senkou_a, current_senkou_b)

    if current_price > cloud_top:
        cloud_status = "ABOVE"
    elif current_price < cloud_bottom:
        cloud_status = "BELOW"
    else:
        cloud_status = "INSIDE"

    return {
        "tenkan": tenkan, "kijun": kijun,
        "senkou_a": senkou_a, "senkou_b": senkou_b,
        "chikou": chikou, "cloud_status": cloud_status,
    }


def calculate_obv(hist: pd.DataFrame) -> pd.Series:
    obv = pd.Series(0.0, index=hist.index)
    for i in range(1, len(hist)):
        if hist["Close"].iloc[i] > hist["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] + hist["Volume"].iloc[i]
        elif hist["Close"].iloc[i] < hist["Close"].iloc[i - 1]:
            obv.iloc[i] = obv.iloc[i - 1] - hist["Volume"].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i - 1]
    return obv


def find_support_resistance(hist: pd.DataFrame, window: int = 20) -> dict:
    high = hist["High"]
    low = hist["Low"]
    close = hist["Close"]

    # ピボットポイント
    pivot = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1]) / 3
    r1 = 2 * pivot - low.iloc[-1]
    s1 = 2 * pivot - high.iloc[-1]
    r2 = pivot + (high.iloc[-1] - low.iloc[-1])
    s2 = pivot - (high.iloc[-1] - low.iloc[-1])

    # 直近の高値安値
    recent_high = high.tail(window).max()
    recent_low = low.tail(window).min()

    return {
        "pivot": pivot, "r1": r1, "r2": r2, "s1": s1, "s2": s2,
        "recent_high": recent_high, "recent_low": recent_low,
    }


def detect_rsi_divergence(close: pd.Series, rsi: pd.Series, lookback: int = 14) -> str:
    """RSIダイバージェンス検出"""
    if len(close) < lookback * 2:
        return "NONE"
    recent_close = close.tail(lookback)
    prev_close = close.iloc[-lookback * 2:-lookback]
    recent_rsi = rsi.tail(lookback)
    prev_rsi = rsi.iloc[-lookback * 2:-lookback]

    # 強気ダイバージェンス: 価格は安値更新、RSIは安値更新せず
    if recent_close.min() < prev_close.min() and recent_rsi.min() > prev_rsi.min():
        return "BULLISH"
    # 弱気ダイバージェンス: 価格は高値更新、RSIは高値更新せず
    if recent_close.max() > prev_close.max() and recent_rsi.max() < prev_rsi.max():
        return "BEARISH"
    return "NONE"


def calculate_all_indicators(hist: pd.DataFrame) -> dict:
    """全テクニカル指標を計算して辞書で返す"""
    if hist is None or len(hist) < 52:
        return None

    close = hist["Close"]
    current_price = close.iloc[-1]

    # 移動平均線
    sma5 = calculate_sma(close, 5)
    sma25 = calculate_sma(close, 25)
    sma75 = calculate_sma(close, 75)
    ema5 = calculate_ema(close, 5)
    ema25 = calculate_ema(close, 25)

    # クロス検出（直近3日以内）
    golden_cross = False
    dead_cross = False
    if len(sma5) >= 3 and len(sma25) >= 3:
        for i in range(-3, 0):
            if (not pd.isna(sma5.iloc[i]) and not pd.isna(sma25.iloc[i])
                    and not pd.isna(sma5.iloc[i - 1]) and not pd.isna(sma25.iloc[i - 1])):
                if sma5.iloc[i] > sma25.iloc[i] and sma5.iloc[i - 1] <= sma25.iloc[i - 1]:
                    golden_cross = True
                if sma5.iloc[i] < sma25.iloc[i] and sma5.iloc[i - 1] >= sma25.iloc[i - 1]:
                    dead_cross = True

    # MACD
    macd_data = calculate_macd(close)
    macd_cross_buy = False
    macd_cross_sell = False
    if len(macd_data["macd"]) >= 2:
        m = macd_data["macd"]
        s = macd_data["signal"]
        if not pd.isna(m.iloc[-1]) and not pd.isna(s.iloc[-1]):
            if m.iloc[-1] > s.iloc[-1] and m.iloc[-2] <= s.iloc[-2]:
                macd_cross_buy = True
            if m.iloc[-1] < s.iloc[-1] and m.iloc[-2] >= s.iloc[-2]:
                macd_cross_sell = True
    histogram_increasing = False
    if len(macd_data["histogram"]) >= 2:
        h = macd_data["histogram"]
        if not pd.isna(h.iloc[-1]) and not pd.isna(h.iloc[-2]):
            histogram_increasing = h.iloc[-1] > h.iloc[-2]

    # RSI
    rsi = calculate_rsi(close)
    rsi_value = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    rsi_divergence = detect_rsi_divergence(close, rsi)

    # ボリンジャーバンド
    bb = calculate_bollinger(close)
    bb_percent_b = bb["percent_b"].iloc[-1] if not pd.isna(bb["percent_b"].iloc[-1]) else 0.5
    bb_bandwidth = bb["bandwidth"].iloc[-1] if not pd.isna(bb["bandwidth"].iloc[-1]) else 0
    bb_squeeze = bb_bandwidth < 0.04  # スクイーズ検出

    # 出来高分析
    vol = hist["Volume"]
    vol_ma25 = calculate_sma(vol.astype(float), 25)
    vol_ratio = vol.iloc[-1] / vol_ma25.iloc[-1] if vol_ma25.iloc[-1] > 0 else 1.0
    obv = calculate_obv(hist)

    # ストキャスティクス
    stoch = calculate_stochastic(hist)
    stoch_k = stoch["k"].iloc[-1] if not pd.isna(stoch["k"].iloc[-1]) else 50
    stoch_d = stoch["d"].iloc[-1] if not pd.isna(stoch["d"].iloc[-1]) else 50

    # 一目均衡表
    ichimoku = calculate_ichimoku(hist)
    tenkan_above_kijun = False
    if not pd.isna(ichimoku["tenkan"].iloc[-1]) and not pd.isna(ichimoku["kijun"].iloc[-1]):
        tenkan_above_kijun = ichimoku["tenkan"].iloc[-1] > ichimoku["kijun"].iloc[-1]

    # ATR
    atr = calculate_atr(hist)
    atr_value = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else 0

    # サポート/レジスタンス
    sr = find_support_resistance(hist)

    # トレンド判定
    trend = "SIDEWAYS"
    if not pd.isna(sma25.iloc[-1]) and not pd.isna(sma75.iloc[-1]):
        if current_price > sma25.iloc[-1] > sma75.iloc[-1]:
            trend = "UPTREND"
        elif current_price < sma25.iloc[-1] < sma75.iloc[-1]:
            trend = "DOWNTREND"

    return {
        "current_price": current_price,
        "trend": trend,
        # 移動平均
        "sma5": sma5.iloc[-1], "sma25": sma25.iloc[-1], "sma75": sma75.iloc[-1],
        "ema5": ema5.iloc[-1], "ema25": ema25.iloc[-1],
        "golden_cross": golden_cross, "dead_cross": dead_cross,
        # MACD
        "macd_value": macd_data["macd"].iloc[-1],
        "macd_signal": macd_data["signal"].iloc[-1],
        "macd_histogram": macd_data["histogram"].iloc[-1],
        "macd_cross_buy": macd_cross_buy, "macd_cross_sell": macd_cross_sell,
        "histogram_increasing": histogram_increasing,
        # RSI
        "rsi": rsi_value, "rsi_divergence": rsi_divergence,
        # ボリンジャーバンド
        "bb_upper": bb["upper"].iloc[-1], "bb_middle": bb["middle"].iloc[-1],
        "bb_lower": bb["lower"].iloc[-1],
        "bb_percent_b": bb_percent_b, "bb_bandwidth": bb_bandwidth, "bb_squeeze": bb_squeeze,
        # 出来高
        "volume": vol.iloc[-1], "volume_ma25": vol_ma25.iloc[-1],
        "volume_ratio": vol_ratio,
        # ストキャスティクス
        "stoch_k": stoch_k, "stoch_d": stoch_d,
        # 一目均衡表
        "ichimoku_cloud_status": ichimoku["cloud_status"],
        "tenkan_above_kijun": tenkan_above_kijun,
        # ATR
        "atr": atr_value,
        # サポート/レジスタンス
        "support_resistance": sr,
    }
