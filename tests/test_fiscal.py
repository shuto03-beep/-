from datetime import date

from app.utils.fiscal import (
    FIXED_PAID_RATE,
    FREE_PERIOD_START,
    current_fiscal_year,
    current_reiwa_fiscal_year,
    fiscal_period_label,
    is_fixed_rate_period,
)


def test_fixed_paid_rate_constant():
    assert FIXED_PAID_RATE == 1482


def test_free_period_start_is_2029_april():
    assert FREE_PERIOD_START == date(2029, 4, 1)


def test_is_fixed_rate_period_before_2029_april():
    assert is_fixed_rate_period(date(2026, 4, 1)) is True
    assert is_fixed_rate_period(date(2028, 12, 31)) is True
    assert is_fixed_rate_period(date(2029, 3, 31)) is True


def test_is_fixed_rate_period_from_2029_april():
    assert is_fixed_rate_period(date(2029, 4, 1)) is False
    assert is_fixed_rate_period(date(2030, 1, 1)) is False


def test_current_fiscal_year_spring_is_same_year():
    assert current_fiscal_year(date(2026, 4, 1)) == 2026
    assert current_fiscal_year(date(2026, 12, 31)) == 2026


def test_current_fiscal_year_january_is_previous_year():
    assert current_fiscal_year(date(2027, 3, 31)) == 2026
    assert current_fiscal_year(date(2027, 1, 15)) == 2026


def test_current_reiwa_fiscal_year():
    # 2026年度 = 令和8年度
    assert current_reiwa_fiscal_year(date(2026, 5, 1)) == 8
    # 2029年度 = 令和11年度
    assert current_reiwa_fiscal_year(date(2029, 5, 1)) == 11


def test_fiscal_period_label_fixed():
    label = fiscal_period_label(date(2026, 5, 1))
    assert '令和8年度' in label
    assert '固定' in label


def test_fiscal_period_label_free():
    label = fiscal_period_label(date(2029, 5, 1))
    assert '令和11年度' in label
    assert '自由' in label
