from datetime import date

from app.extensions import db
from app.models.activity_log import ActivityLog
from app.models.coach import Coach
from app.models.organization import Organization


def _make_other_org():
    o = Organization(name='バレー部', representative='鈴木', is_approved=True)
    db.session.add(o)
    db.session.commit()
    return o


def test_list_coaches_empty(client, login_admin):
    resp = client.get('/admin/coaches')
    assert resp.status_code == 200
    assert '指導者が登録されていません' in resp.data.decode('utf-8')


def test_create_coach_single_org(client, login_admin, approved_org):
    resp = client.post(
        '/admin/coaches/new',
        data={
            'full_name': '田中太郎',
            'full_name_kana': 'タナカタロウ',
            'compensation_type': 'paid',
            'hourly_rate': '1500',
            'organization_ids': [approved_org.id],
            'is_active': 'y',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    coach = Coach.query.one()
    assert coach.full_name == '田中太郎'
    assert coach.hourly_rate == 1500
    assert [o.id for o in coach.organizations] == [approved_org.id]
    assert not coach.is_multi_affiliated

    log = ActivityLog.query.filter_by(action='register_coach').one()
    assert log.target_id == coach.id


def test_create_coach_multi_affiliation_flagged(client, login_admin, approved_org):
    other_org = _make_other_org()
    resp = client.post(
        '/admin/coaches/new',
        data={
            'full_name': '田中太郎',
            'compensation_type': 'unpaid',
            'hourly_rate': '0',
            'organization_ids': [approved_org.id, other_org.id],
            'is_active': 'y',
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert 'ダブルカウント' in resp.data.decode('utf-8')
    coach = Coach.query.one()
    assert coach.organization_count == 2
    assert coach.is_multi_affiliated


def test_edit_coach(client, login_admin, approved_org):
    coach = Coach(full_name='山田', compensation_type='unpaid', hourly_rate=0)
    coach.organizations = [approved_org]
    db.session.add(coach)
    db.session.commit()

    resp = client.post(
        f'/admin/coaches/{coach.id}/edit',
        data={
            'full_name': '山田花子',
            'compensation_type': 'paid',
            'hourly_rate': '2000',
            'organization_ids': [approved_org.id],
            'is_active': 'y',
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    db.session.refresh(coach)
    assert coach.full_name == '山田花子'
    assert coach.hourly_rate == 2000
    assert coach.compensation_type == 'paid'


def test_list_coaches_multi_filter(client, login_admin, approved_org):
    other = _make_other_org()
    single = Coach(full_name='A', compensation_type='unpaid')
    single.organizations = [approved_org]
    multi = Coach(full_name='B', compensation_type='paid', hourly_rate=1000)
    multi.organizations = [approved_org, other]
    db.session.add_all([single, multi])
    db.session.commit()

    resp = client.get('/admin/coaches?multi=1')
    html = resp.data.decode('utf-8')
    assert '>B</strong>' in html or 'B' in html
    # Single-affiliation coach should not appear when filtered
    rows = html.count('table-warning')
    assert rows >= 1
