from datetime import date, time

from app.extensions import db
from app.models.facility import Facility
from app.models.organization import Organization
from app.models.reservation import Reservation
from tests.conftest import make_reservation


def test_reports_status_aggregation(
    client, login_admin, school, facility, approved_org, leader_user,
):
    make_reservation(facility, approved_org, leader_user, at=time(9, 0))
    make_reservation(facility, approved_org, leader_user, at=time(10, 0))
    make_reservation(
        facility, approved_org, leader_user,
        status=Reservation.STATUS_CANCELLED, at=time(11, 0),
    )
    resp = client.get('/admin/reports')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '>2<' in html  # confirmed
    assert '>1<' in html  # cancelled


def test_reports_includes_zero_reservation_facility(
    client, login_admin, school, facility, approved_org,
):
    empty_facility = Facility(school_id=school.id, name='武道場', facility_type='indoor')
    db.session.add(empty_facility)
    db.session.commit()
    resp = client.get('/admin/reports')
    assert resp.status_code == 200
    assert '武道場' in resp.data.decode('utf-8')


def test_reports_excludes_unapproved_organizations(client, login_admin, school, facility):
    unapproved = Organization(name='未承認団体', representative='A', is_approved=False)
    approved = Organization(name='承認済団体', representative='B', is_approved=True)
    db.session.add_all([unapproved, approved])
    db.session.commit()
    resp = client.get('/admin/reports')
    html = resp.data.decode('utf-8')
    assert '承認済団体' in html
    assert '未承認団体' not in html
