from datetime import date, time, timedelta

import pytest

from app.extensions import db
from app.models.notification import Notification
from app.models.reservation import Reservation
from app.models.user import User


@pytest.fixture
def parent_user(app, approved_org):
    u = User(
        username='parent1', email='parent1@x.jp', display_name='保護者太郎',
        role=User.ROLE_PARENT, child_organization_id=approved_org.id,
    )
    u.set_password('x')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def login_parent(client, parent_user):
    with client.session_transaction() as s:
        s['_user_id'] = str(parent_user.id)
        s['_fresh'] = True
    return parent_user


def test_parent_dashboard_forbidden_for_non_parent(client, login_admin):
    resp = client.get('/family/dashboard')
    assert resp.status_code == 403


def test_parent_dashboard_without_child_org(client, app):
    u = User(
        username='p', email='p@x.jp', display_name='親', role=User.ROLE_PARENT,
        child_organization_id=None,
    )
    u.set_password('x')
    db.session.add(u)
    db.session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)
        s['_fresh'] = True
    resp = client.get('/family/dashboard')
    assert resp.status_code == 200
    assert 'お子さまの所属団体が設定されていません' in resp.data.decode('utf-8')


def test_parent_dashboard_shows_child_org_schedule(
    client, login_parent, parent_user, facility, approved_org, leader_user,
):
    tomorrow = date.today() + timedelta(days=1)
    r = Reservation(
        facility_id=facility.id, organization_id=approved_org.id, reserved_by=leader_user.id,
        date=tomorrow, start_time=time(17, 0), end_time=time(18, 0),
        status=Reservation.STATUS_CONFIRMED,
    )
    db.session.add(r)
    db.session.commit()
    resp = client.get('/family/dashboard')
    html = resp.data.decode('utf-8')
    assert approved_org.name in html
    assert facility.full_name in html


def test_parent_dashboard_shows_own_notifications(client, login_parent, parent_user):
    n = Notification(
        user_id=parent_user.id, title='練習中止のお知らせ',
        message='明日は雨天中止です',
    )
    db.session.add(n)
    db.session.commit()
    resp = client.get('/family/dashboard')
    html = resp.data.decode('utf-8')
    assert '練習中止のお知らせ' in html


def test_dashboard_redirects_parent_to_portal(client, login_parent):
    resp = client.get('/dashboard', follow_redirects=False)
    assert resp.status_code == 302
    assert '/family/dashboard' in resp.headers['Location']
