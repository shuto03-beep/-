from datetime import date, time, timedelta

import pytest

from app.extensions import db
from app.models.coach import Coach
from app.models.user import User
from tests.conftest import make_reservation


@pytest.fixture
def coach_user(app):
    u = User(
        username='coach1', email='coach1@x.jp', display_name='指導者一郎',
        role=User.ROLE_COACH,
    )
    u.set_password('x')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def linked_coach(app, coach_user, approved_org):
    c = Coach(
        full_name='指導者一郎', compensation_type='paid', hourly_rate=1800,
        user_id=coach_user.id,
    )
    c.organizations = [approved_org]
    db.session.add(c)
    db.session.commit()
    return c


@pytest.fixture
def login_coach(client, coach_user):
    with client.session_transaction() as s:
        s['_user_id'] = str(coach_user.id)
        s['_fresh'] = True
    return coach_user


def test_dashboard_requires_linked_coach(client, app):
    # Non-coach user
    u = User(username='x', email='x@y.jp', display_name='X', role=User.ROLE_RESIDENT)
    u.set_password('x')
    db.session.add(u)
    db.session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)
        s['_fresh'] = True
    resp = client.get('/my/dashboard')
    assert resp.status_code == 403


def test_coach_dashboard_shows_profile(client, login_coach, linked_coach):
    resp = client.get('/my/dashboard')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '指導者一郎' in html
    assert '1,800円' in html


def test_coach_dashboard_upcoming_reservations(
    client, login_coach, linked_coach, facility, approved_org, leader_user,
):
    tomorrow = date.today() + timedelta(days=1)
    from app.models.reservation import Reservation
    r = Reservation(
        facility_id=facility.id, organization_id=approved_org.id, reserved_by=leader_user.id,
        date=tomorrow, start_time=time(17, 0), end_time=time(18, 0),
        status=Reservation.STATUS_CONFIRMED,
    )
    db.session.add(r)
    db.session.commit()
    resp = client.get('/my/dashboard')
    html = resp.data.decode('utf-8')
    assert facility.full_name in html
    assert approved_org.name in html


def test_coach_compensation_totals(
    client, login_coach, linked_coach, facility, approved_org, leader_user,
):
    # Two 1-hour reservations for org => 2h * 1800 = 3,600円
    make_reservation(facility, approved_org, leader_user, at=time(16, 0))
    make_reservation(facility, approved_org, leader_user, at=time(18, 0))
    resp = client.get('/my/compensation')
    html = resp.data.decode('utf-8')
    assert '3,600 円' in html


def test_dashboard_redirects_coach_to_portal(client, login_coach, linked_coach):
    resp = client.get('/dashboard', follow_redirects=False)
    assert resp.status_code == 302
    assert '/my/dashboard' in resp.headers['Location']
