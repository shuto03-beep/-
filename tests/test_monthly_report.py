from datetime import date, time

from app.extensions import db
from app.models.coach import Coach
from tests.conftest import make_reservation


def test_monthly_report_renders_for_current_month(client, login_admin):
    today = date.today()
    resp = client.get('/admin/reports/monthly')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert f'{today.year}年{today.month}月' in html
    assert '月次利用報告書' in html


def test_monthly_report_shows_totals_and_compensation(
    client, login_admin, facility, approved_org, leader_user,
):
    # Two 1h confirmed reservations this month
    make_reservation(facility, approved_org, leader_user, at=time(16, 0))
    make_reservation(facility, approved_org, leader_user, at=time(18, 0))

    # Paid coach at 2000/h affiliated with approved_org
    coach = Coach(full_name='指導者A', compensation_type='paid', hourly_rate=2000)
    coach.organizations = [approved_org]
    db.session.add(coach)
    db.session.commit()

    resp = client.get('/admin/reports/monthly')
    html = resp.data.decode('utf-8')
    assert '指導者A' in html
    # 2h × 2000円 = 4,000円
    assert '4,000円' in html


def test_monthly_report_explicit_year_month(client, login_admin):
    resp = client.get('/admin/reports/monthly?year=2025&month=3')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '2025年3月' in html


def test_monthly_report_invalid_params_fallback_to_current(client, login_admin):
    today = date.today()
    resp = client.get('/admin/reports/monthly?year=abc&month=99')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert f'{today.year}年{today.month}月' in html
