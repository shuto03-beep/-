from datetime import date, time

from app.extensions import db
from app.models.coach import Coach
from app.models.organization import Organization
from tests.conftest import make_reservation


def _other_org():
    o = Organization(name='バレー部', representative='鈴木', is_approved=True)
    db.session.add(o)
    db.session.commit()
    return o


def test_compensation_csv_auth_required(client):
    resp = client.get('/admin/coaches/compensation.csv', follow_redirects=False)
    assert resp.status_code in (302, 401, 403)


def test_compensation_csv_header_only_when_no_coach(client, login_admin):
    resp = client.get('/admin/coaches/compensation.csv')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8-sig')
    assert '指導者ID' in body
    assert body.count('\n') == 1


def test_compensation_csv_amount_calculation(
    client, login_admin, facility, approved_org, leader_user,
):
    coach = Coach(full_name='田中', compensation_type='paid', hourly_rate=2000)
    coach.organizations = [approved_org]
    db.session.add(coach)
    db.session.commit()

    # Two confirmed reservations: 1h + 1h = 2h at 2000/h = 4000 yen
    make_reservation(facility, approved_org, leader_user, at=time(16, 0))
    make_reservation(facility, approved_org, leader_user, at=time(18, 0))

    resp = client.get('/admin/coaches/compensation.csv')
    body = resp.data.decode('utf-8-sig')
    assert '田中' in body
    # expect "4000" appearing as compensation amount
    assert ',4000,' in body or body.rstrip().endswith('4000,')


def test_compensation_csv_flags_multi_affiliation(
    client, login_admin, facility, approved_org, leader_user,
):
    other = _other_org()
    coach = Coach(full_name='鈴木', compensation_type='paid', hourly_rate=1000)
    coach.organizations = [approved_org, other]
    db.session.add(coach)
    db.session.commit()
    make_reservation(facility, approved_org, leader_user)

    resp = client.get('/admin/coaches/compensation.csv')
    body = resp.data.decode('utf-8-sig')
    assert '鈴木' in body
    assert '複数団体所属' in body


def test_compensation_csv_coach_without_org_marked(client, login_admin):
    coach = Coach(full_name='浮遊', compensation_type='unpaid', hourly_rate=0)
    db.session.add(coach)
    db.session.commit()
    resp = client.get('/admin/coaches/compensation.csv')
    body = resp.data.decode('utf-8-sig')
    assert '浮遊' in body
    assert '所属団体未設定' in body
