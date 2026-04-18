from datetime import date, time

from app.extensions import db
from app.models.activity_log import ActivityLog
from app.services.activity_log_service import log_activity
from tests.conftest import make_reservation


def test_log_activity_rolled_back_when_transaction_fails(app, admin_user):
    # Simulate logged-in actor via user argument (no flask-login context)
    log_activity('test_action', target_type='thing', target_id=1, details='x', user=admin_user)
    db.session.rollback()
    assert ActivityLog.query.count() == 0


def test_log_activity_persists_on_commit(app, admin_user):
    log_activity('test_action', target_type='thing', target_id=1, details='x', user=admin_user)
    db.session.commit()
    got = ActivityLog.query.one()
    assert got.action == 'test_action'
    assert got.user_id == admin_user.id
    assert got.details == 'x'


def test_approve_organization_records_log(client, login_admin, approved_org):
    # Flip to unapproved first so approve route runs normally
    approved_org.is_approved = False
    approved_org.is_inachalle_certified = False
    db.session.commit()

    resp = client.post(
        f'/admin/organizations/{approved_org.id}/approve',
        data={'certify_inachalle': '1'},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    logs = ActivityLog.query.filter_by(action='approve_organization').all()
    assert len(logs) == 1
    assert logs[0].target_id == approved_org.id


def test_cancel_reservation_records_log(app, admin_user, facility, approved_org, leader_user):
    r = make_reservation(facility, approved_org, leader_user)
    from app.services.reservation_service import cancel_reservation
    cancel_reservation(r.id, leader_user.id, 'やむなく中止')
    log = ActivityLog.query.filter_by(action='cancel_reservation').one()
    assert log.target_id == r.id
    assert 'やむなく中止' in log.details


def test_activity_logs_admin_view(client, login_admin, admin_user):
    log_activity('approve_organization', target_type='organization', target_id=1, user=admin_user)
    db.session.commit()
    resp = client.get('/admin/activity-logs')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert '団体承認' in html
    assert '該当 1 件' in html


def test_activity_logs_filter_by_action(client, login_admin, admin_user):
    log_activity('approve_organization', target_type='organization', target_id=1, user=admin_user)
    log_activity('reject_organization', target_type='organization', target_id=2, user=admin_user)
    db.session.commit()
    resp = client.get('/admin/activity-logs?action=approve_organization')
    html = resp.data.decode('utf-8')
    assert '該当 1 件' in html
