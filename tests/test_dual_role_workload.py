from datetime import date, time, timedelta

from app.extensions import db
from app.models.coach import Coach
from tests.conftest import make_reservation


def _monday(d=None):
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def test_dual_role_page_empty_when_no_teachers(client, login_admin):
    resp = client.get('/admin/coaches/dual-role-workload')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '教職員兼職兼業として登録された指導者がいません' in html


def test_dual_role_page_ok_when_within_limit(
    client, login_admin, facility, approved_org, leader_user,
):
    coach = Coach(
        full_name='先生A', compensation_type='paid', hourly_rate=0,
        is_teacher_dual_role=True,
    )
    coach.organizations = [approved_org]
    db.session.add(coach)
    db.session.commit()

    # 1 hour reservation this week - well under 19h45m
    make_reservation(facility, approved_org, leader_user, at=time(17, 0))
    resp = client.get('/admin/coaches/dual-role-workload')
    html = resp.data.decode('utf-8')
    assert '先生A' in html
    assert '上限超過者・警告対象者はありません' in html


def test_dual_role_over_limit_flagged(
    client, login_admin, school, approved_org, admin_user,
):
    from app.models.facility import Facility
    from app.models.reservation import Reservation
    from datetime import datetime

    # Create 21 one-hour confirmed reservations on the current week for this org
    f = Facility(school_id=school.id, name='体育館', facility_type='indoor')
    db.session.add(f)
    db.session.commit()

    coach = Coach(full_name='先生B', compensation_type='paid', is_teacher_dual_role=True)
    coach.organizations = [approved_org]
    db.session.add(coach)
    db.session.commit()

    monday = _monday()
    # Add 21 hours over the week (well over 19h45m=19.75h)
    for day_offset in range(6):
        for h in range(16, 20):
            r = Reservation(
                facility_id=f.id, organization_id=approved_org.id, reserved_by=admin_user.id,
                date=monday + timedelta(days=day_offset),
                start_time=time(h, 0), end_time=time(h + 1, 0),
                status=Reservation.STATUS_CONFIRMED,
            )
            db.session.add(r)
    db.session.commit()

    resp = client.get('/admin/coaches/dual-role-workload')
    html = resp.data.decode('utf-8')
    assert '先生B' in html
    assert '超過' in html
    assert '週上限' in html


def test_dual_role_week_query_parameter(client, login_admin, approved_org):
    coach = Coach(full_name='先生C', compensation_type='paid', is_teacher_dual_role=True)
    coach.organizations = [approved_org]
    db.session.add(coach)
    db.session.commit()

    # Query a past week - no reservations there
    past_monday = _monday() - timedelta(days=28)
    resp = client.get(f'/admin/coaches/dual-role-workload?week={past_monday.isoformat()}')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert past_monday.strftime('%Y-%m-%d') in html
