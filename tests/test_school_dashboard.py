from datetime import date, time, timedelta

import pytest

from app.extensions import db
from app.models.reservation import Reservation
from app.models.school_block import SchoolBlock
from app.models.user import User
from tests.conftest import make_reservation


@pytest.fixture
def school_user(app, school):
    u = User(
        username='schl', email='schl@x.jp', display_name='学校担当',
        role=User.ROLE_SCHOOL,
    )
    u.set_password('x')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def login_school(client, school_user):
    with client.session_transaction() as s:
        s['_user_id'] = str(school_user.id)
        s['_fresh'] = True
    return school_user


def test_school_dashboard_renders(client, login_school, school):
    resp = client.get('/dashboard')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert school.name in html
    assert '今週の予約数' in html
    assert 'ブロック追加' in html


def test_school_dashboard_counts_reservations_today(
    client, login_school, school, facility, approved_org, leader_user,
):
    make_reservation(facility, approved_org, leader_user, at=time(16, 0))
    make_reservation(facility, approved_org, leader_user, at=time(18, 0))
    resp = client.get('/dashboard')
    html = resp.data.decode('utf-8')
    assert '>2<' in html  # count appears as stat value


def test_school_dashboard_shows_this_week_blocks(
    client, login_school, school, school_user,
):
    today = date.today()
    b = SchoolBlock(
        school_id=school.id, date=today, reason='運動会準備',
        start_time=None, end_time=None, blocked_by=school_user.id,
    )
    db.session.add(b)
    db.session.commit()
    resp = client.get('/dashboard')
    html = resp.data.decode('utf-8')
    assert '運動会準備' in html


def test_school_dashboard_shows_upcoming_week_reservations(
    client, login_school, school, facility, approved_org, leader_user,
):
    tomorrow = date.today() + timedelta(days=1)
    r = Reservation(
        facility_id=facility.id, organization_id=approved_org.id, reserved_by=leader_user.id,
        date=tomorrow, start_time=time(17, 0), end_time=time(18, 0),
        status=Reservation.STATUS_CONFIRMED,
    )
    db.session.add(r)
    db.session.commit()
    resp = client.get('/dashboard')
    html = resp.data.decode('utf-8')
    assert facility.name in html
    assert approved_org.name in html
