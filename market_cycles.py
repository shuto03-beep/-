"""市場サイクル分析 - 曜日・時間帯・月次のパターンに基づくスコア補正

根拠:
- 曜日効果: Jaffe & Westerfield (1985), Kato & Schallheim (1985)
- 日中パターン: TSE市場構造データ、U字型ボラティリティ
- 月次効果: Ariel (1987) Turn-of-month, Bouman & Jacobsen (2002) Halloween効果
- SQ効果: JPXデリバティブ市場データ
"""
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


# === 曜日効果 (Day-of-Week Effect) ===
# 学術研究に基づく曜日別バイアス（スコア補正値）
DAY_OF_WEEK_BIAS = {
    0: -5,   # 月曜: 歴史的にマイナス（-5〜-10bps）
    1: -3,   # 火曜: やや弱い（日本市場特有のタイムラグ効果）
    2: +3,   # 水曜: やや強い
    3: +2,   # 木曜: ニュートラル〜やや強い
    4: +5,   # 金曜: 歴史的にプラス（+3〜+8bps）
}


# === 時間帯別パターン (Intraday Patterns) ===
# TSEの日中出来高・ボラティリティのU字パターンに基づく
INTRADAY_PHASES = {
    # (開始時, 開始分, 終了時, 終了分): (フェーズ名, スコア補正, 推奨アクション)
    "opening":       {"start": (9, 0),  "end": (9, 30),  "label": "寄り付き",       "bias": 0,  "note": "高ボラ・ギャップ反転傾向。新規エントリーは慎重に"},
    "mid_morning":   {"start": (9, 30), "end": (11, 0),  "label": "前場中盤",       "bias": +3, "note": "トレンド形成期。10:00以降のトレンド継続は信頼性高"},
    "pre_lunch":     {"start": (11, 0), "end": (11, 30), "label": "前場引け前",     "bias": -2, "note": "昼休みリスク回避のポジション調整"},
    "lunch":         {"start": (11, 30),"end": (12, 30), "label": "昼休み",         "bias": 0,  "note": "休場中。先物は取引あり"},
    "afternoon_open":{"start": (12, 30),"end": (13, 0),  "label": "後場寄り",       "bias": 0,  "note": "昼休みギャップ。部分反転傾向"},
    "afternoon_mid": {"start": (13, 0), "end": (14, 0),  "label": "後場中盤",       "bias": -2, "note": "最低出来高・最低ボラ。スプレッド拡大注意"},
    "power_hour":    {"start": (14, 0), "end": (15, 0),  "label": "大引けにかけて", "bias": +3, "note": "出来高急増。機関投資家の活動。+1〜3bpsの正のドリフト"},
}


# === 月次・特殊日パターン ===
# 月別の歴史的パフォーマンス（日経225長期平均）
MONTHLY_BIAS = {
    1: +5,   # 1月: 強い（+1.0〜1.5%）、1月効果
    2: +2,   # 2月: やや強い
    3: +3,   # 3月: 決算期末ウィンドウドレッシング
    4: +5,   # 4月: 強い（新年度資金流入）
    5: -3,   # 5月: 弱い（Sell in May）
    6: 0,    # 6月: ニュートラル
    7: +2,   # 7月: やや強い
    8: -3,   # 8月: 弱い（お盆で流動性低下）
    9: -2,   # 9月: やや弱い
    10: +2,  # 10月: やや強い（底打ち傾向）
    11: +4,  # 11月: 強い
    12: +3,  # 12月: 強い（年末ラリー）
}


# === 2026年SQ日（第2金曜日）===
SQ_DATES_2026 = {
    "2026-01-09", "2026-02-13", "2026-03-13",  # メジャーSQ: 3月
    "2026-04-10", "2026-05-08", "2026-06-12",  # メジャーSQ: 6月
    "2026-07-10", "2026-08-14", "2026-09-11",  # メジャーSQ: 9月
    "2026-10-09", "2026-11-13", "2026-12-11",  # メジャーSQ: 12月
}
MAJOR_SQ_MONTHS = {3, 6, 9, 12}  # メジャーSQの月


def get_day_of_week_adjustment(now: datetime) -> tuple[int, str]:
    """曜日に基づくスコア補正値と説明を返す"""
    weekday = now.weekday()
    bias = DAY_OF_WEEK_BIAS.get(weekday, 0)
    day_names = ["月", "火", "水", "木", "金"]
    day_name = day_names[weekday] if weekday < 5 else "休"

    reasons = []
    if weekday == 0:
        reasons.append(f"{day_name}曜効果: 歴史的にマイナス傾向（補正{bias:+d}）")
    elif weekday == 4:
        reasons.append(f"{day_name}曜効果: 歴史的にプラス傾向（補正{bias:+d}）")
    elif bias != 0:
        reasons.append(f"{day_name}曜バイアス（補正{bias:+d}）")

    return bias, "; ".join(reasons) if reasons else ""


def get_intraday_adjustment(now: datetime) -> tuple[int, str]:
    """時間帯に基づくスコア補正値とフェーズ情報を返す"""
    h, m = now.hour, now.minute

    for phase_key, phase in INTRADAY_PHASES.items():
        sh, sm = phase["start"]
        eh, em = phase["end"]
        start_min = sh * 60 + sm
        end_min = eh * 60 + em
        current_min = h * 60 + m

        if start_min <= current_min < end_min:
            return phase["bias"], f"{phase['label']}（{phase['note']}）"

    return 0, ""


def get_monthly_adjustment(now: datetime) -> tuple[int, str]:
    """月次パターンに基づくスコア補正値を返す"""
    month = now.month
    day = now.day
    bias = MONTHLY_BIAS.get(month, 0)
    reasons = []

    # 月別バイアス
    if bias != 0:
        reasons.append(f"{month}月バイアス（補正{bias:+d}）")

    # Turn-of-month効果（月末最終日〜翌月3営業日: +5〜+10bps/日）
    # 簡易判定: 28日以降 or 1〜3日
    if day >= 28 or day <= 3:
        bias += 3
        reasons.append("月替わり効果（+3）")

    # 配当権利確定前（3月・9月の20-28日）
    if month in (3, 9) and 20 <= day <= 28:
        bias += 4
        reasons.append("配当権利確定前の買い需要（+4）")

    # 権利落ち日（3月・9月の29-31日）
    if month in (3, 9) and day >= 29:
        bias -= 5
        reasons.append("権利落ち日の下落圧力（-5）")

    # 新年度売り（4月第1-2週）
    if month == 4 and day <= 14:
        bias -= 3
        reasons.append("新年度リアロケーション売り（-3）")

    # Sell in May（5月）
    if month == 5:
        reasons.append("Sell in May傾向")

    # お盆（8月10-16日）
    if month == 8 and 10 <= day <= 16:
        bias -= 3
        reasons.append("お盆で流動性低下（-3）")

    return bias, "; ".join(reasons) if reasons else ""


def get_sq_adjustment(now: datetime) -> tuple[int, str]:
    """SQ日の影響を返す"""
    date_str = now.strftime("%Y-%m-%d")
    bias = 0
    reasons = []

    if date_str in SQ_DATES_2026:
        is_major = now.month in MAJOR_SQ_MONTHS
        sq_type = "メジャーSQ" if is_major else "ミニSQ"
        bias = -3  # SQ当日はボラ高で方向感不安定
        reasons.append(f"{sq_type}当日: 寄り付き出来高2-5倍。ボラ上昇注意（補正{bias:+d}）")

    # SQ前日（木曜）
    # 簡易判定: SQ日の前日
    from datetime import timedelta as td
    tomorrow = (now + td(days=1)).strftime("%Y-%m-%d")
    if tomorrow in SQ_DATES_2026:
        bias = -2
        reasons.append("SQ前日: ポジション調整で不安定（補正-2）")

    return bias, "; ".join(reasons) if reasons else ""


def get_total_cycle_adjustment(now: datetime = None) -> dict:
    """全サイクル要素を集約して合計スコア補正と詳細を返す"""
    if now is None:
        now = datetime.now(JST)

    dow_bias, dow_reason = get_day_of_week_adjustment(now)
    intra_bias, intra_reason = get_intraday_adjustment(now)
    monthly_bias, monthly_reason = get_monthly_adjustment(now)
    sq_bias, sq_reason = get_sq_adjustment(now)

    total_bias = dow_bias + intra_bias + monthly_bias + sq_bias

    # 補正範囲を-15〜+15に制限（極端な補正を防止）
    total_bias = max(-15, min(15, total_bias))

    reasons = [r for r in [dow_reason, intra_reason, monthly_reason, sq_reason] if r]

    return {
        "total_bias": total_bias,
        "day_of_week_bias": dow_bias,
        "intraday_bias": intra_bias,
        "monthly_bias": monthly_bias,
        "sq_bias": sq_bias,
        "reasons": reasons,
        "phase": intra_reason.split("（")[0] if intra_reason else "",
    }
