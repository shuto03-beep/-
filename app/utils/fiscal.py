"""日本の会計年度ユーティリティ。

いなチャレでは令和10年度末（2029/3/31）まで町補助金で一律1,482円/時を適用し、
令和11年度（2029/4/1〜）以降は団体ごとに自由設定できる方針。
"""
from datetime import date

# 令和11年度開始 = 2029/4/1（この日以降、単価が自由設定可能）
FREE_PERIOD_START = date(2029, 4, 1)

# 町補助金による固定時給（円/時）
FIXED_PAID_RATE = 1482


def current_fiscal_year(today=None):
    """会計年度を西暦年で返す（4月始まり）。

    例: 2026/4/1〜2027/3/31 → 2026
    """
    today = today or date.today()
    if today.month >= 4:
        return today.year
    return today.year - 1


def current_reiwa_fiscal_year(today=None):
    """会計年度を令和で返す。例: 2026年度 → 8"""
    return current_fiscal_year(today) - 2018


def is_fixed_rate_period(today=None):
    """町補助金による固定単価運用期間かどうか。

    令和10年度末（2029/3/31）まで True、令和11年度以降 False。
    """
    today = today or date.today()
    return today < FREE_PERIOD_START


def fiscal_period_label(today=None):
    """管理画面に表示する期間ラベル。"""
    if is_fixed_rate_period(today):
        fy = current_reiwa_fiscal_year(today)
        return f'令和{fy}年度（町補助金による固定単価期間）'
    fy = current_reiwa_fiscal_year(today)
    return f'令和{fy}年度（団体自由設定期間）'
