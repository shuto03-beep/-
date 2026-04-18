from datetime import date, time

from app.extensions import db
from app.models.reservation import Reservation
from tests.conftest import make_reservation


def test_reservations_csv_returns_header_only_when_empty(client, login_admin):
    resp = client.get('/admin/reports/export/reservations.csv?from=2020-01-01&to=2020-01-02')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8-sig')
    assert '予約ID' in body
    assert body.count('\n') == 1  # header only


def test_reservations_csv_contains_reservation_data(
    client, login_admin, facility, approved_org, leader_user,
):
    make_reservation(facility, approved_org, leader_user)
    resp = client.get('/admin/reports/export/reservations.csv')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8-sig')
    assert '稲美中学校' in body
    assert '体育館' in body
    assert 'いなチャレ陸上クラブ' in body
    assert 'はい' in body  # inachalle certification


def test_reservations_csv_content_type(client, login_admin):
    resp = client.get('/admin/reports/export/reservations.csv')
    assert 'text/csv' in resp.headers['Content-Type']
    assert 'attachment' in resp.headers['Content-Disposition']


def test_organizations_csv(client, login_admin, approved_org):
    resp = client.get('/admin/reports/export/organizations.csv')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8-sig')
    assert '団体ID' in body
    assert 'いなチャレ陸上クラブ' in body


def test_csv_requires_admin(client):
    resp = client.get('/admin/reports/export/reservations.csv', follow_redirects=False)
    assert resp.status_code in (302, 401, 403)
