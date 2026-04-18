from app.extensions import db
from app.models.coach import Coach
from app.models.organization import Organization


def test_chutairen_csv_auth_required(client):
    resp = client.get('/admin/reports/export/chutairen-roster.csv', follow_redirects=False)
    assert resp.status_code in (302, 401, 403)


def test_chutairen_csv_header_only_when_no_certified_org(client, login_admin):
    resp = client.get('/admin/reports/export/chutairen-roster.csv')
    assert resp.status_code == 200
    body = resp.data.decode('utf-8-sig')
    assert '団体ID' in body
    assert body.count('\n') == 1


def test_chutairen_csv_certified_org_without_coaches(client, login_admin, approved_org):
    # approved_org fixture has is_inachalle_certified=True
    resp = client.get('/admin/reports/export/chutairen-roster.csv')
    body = resp.data.decode('utf-8-sig')
    assert approved_org.name in body
    assert '（指導者未登録）' in body


def test_chutairen_csv_excludes_non_certified_orgs(client, login_admin, approved_org):
    non_cert = Organization(
        name='一般団体', representative='A',
        is_approved=True, is_inachalle_certified=False,
    )
    db.session.add(non_cert)
    db.session.commit()
    resp = client.get('/admin/reports/export/chutairen-roster.csv')
    body = resp.data.decode('utf-8-sig')
    assert approved_org.name in body
    assert '一般団体' not in body


def test_chutairen_csv_expands_coach_per_row(client, login_admin, approved_org):
    c1 = Coach(full_name='田中', compensation_type='unpaid', is_teacher_dual_role=True)
    c2 = Coach(full_name='佐藤', compensation_type='paid', hourly_rate=1500)
    c1.organizations = [approved_org]
    c2.organizations = [approved_org]
    db.session.add_all([c1, c2])
    db.session.commit()

    resp = client.get('/admin/reports/export/chutairen-roster.csv')
    body = resp.data.decode('utf-8-sig')
    # header + 2 coach rows
    assert body.strip().count('\n') == 2
    assert '田中' in body and '佐藤' in body


def test_chutairen_csv_skips_inactive_coaches(client, login_admin, approved_org):
    active = Coach(full_name='現役', compensation_type='paid')
    inactive = Coach(full_name='退任', compensation_type='paid', is_active=False)
    active.organizations = [approved_org]
    inactive.organizations = [approved_org]
    db.session.add_all([active, inactive])
    db.session.commit()

    resp = client.get('/admin/reports/export/chutairen-roster.csv')
    body = resp.data.decode('utf-8-sig')
    assert '現役' in body
    assert '退任' not in body
