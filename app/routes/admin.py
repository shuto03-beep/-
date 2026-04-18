import csv
import io
from datetime import date, datetime, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func, case
from sqlalchemy.orm import joinedload
from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.facility import Facility
from app.models.school import School
from app.models.activity_log import ActivityLog
from app.models.coach import Coach
from app.forms.admin import OrganizationRegistrationForm, UserEditForm
from app.services.notification_service import create_bulk_notifications
from app.services.activity_log_service import log_activity
from app.utils.decorators import admin_required
from app.utils.fiscal import FIXED_PAID_RATE, fiscal_period_label, is_fixed_rate_period

admin_bp = Blueprint('admin', __name__)


# === 団体管理 ===

@admin_bp.route('/admin/organizations')
@login_required
@admin_required
def organizations():
    orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    return render_template('admin/organizations.html', organizations=orgs)


@admin_bp.route('/admin/organizations/<int:id>')
@login_required
@admin_required
def organization_detail(id):
    org = db.session.get(Organization, id)
    if not org:
        flash('団体が見つかりません。', 'danger')
        return redirect(url_for('admin.organizations'))
    return render_template('admin/organization_detail.html', org=org)


@admin_bp.route('/admin/organizations/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_organization(id):
    org = db.session.get(Organization, id)
    if not org:
        flash('団体が見つかりません。', 'danger')
        return redirect(url_for('admin.organizations'))

    org.is_approved = True
    # いなチャレ認定として承認するかどうか
    certify = request.form.get('certify_inachalle') == '1'
    org.is_inachalle_certified = certify
    log_activity(
        'approve_organization',
        target_type='organization', target_id=org.id,
        details=f'認定={certify}',
    )
    db.session.commit()

    cert_text = 'いなチャレ認定団体として' if certify else ''
    message = (
        f'「{org.name}」が{cert_text}事務局に承認されました。施設の予約が可能になりました。'
        + (f' 認定団体として{org.advance_days}日先まで優先予約が可能です。' if certify else '')
    )
    create_bulk_notifications(
        [m.id for m in org.members],
        '団体が承認されました',
        message,
    )

    flash(f'「{org.name}」を{cert_text}承認しました。', 'success')
    return redirect(url_for('admin.organizations'))


@admin_bp.route('/admin/organizations/<int:id>/toggle_certification', methods=['POST'])
@login_required
@admin_required
def toggle_certification(id):
    org = db.session.get(Organization, id)
    if not org:
        flash('団体が見つかりません。', 'danger')
        return redirect(url_for('admin.organizations'))

    org.is_inachalle_certified = not org.is_inachalle_certified
    log_activity(
        'toggle_certification',
        target_type='organization', target_id=org.id,
        details=f'認定={org.is_inachalle_certified}',
    )
    db.session.commit()

    if org.is_inachalle_certified:
        status_msg = f'いなチャレ認定団体に設定しました（{org.advance_days}日先まで優先予約可能）'
    else:
        status_msg = f'いなチャレ認定を解除しました（{org.advance_days}日先まで予約可能）'

    create_bulk_notifications(
        [m.id for m in org.members],
        'いなチャレ認定ステータスが変更されました',
        f'「{org.name}」の認定ステータスが変更されました。{status_msg}',
    )

    flash(f'「{org.name}」: {status_msg}', 'success')
    return redirect(url_for('admin.organization_detail', id=id))


@admin_bp.route('/admin/organizations/<int:id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_organization(id):
    org = db.session.get(Organization, id)
    if not org:
        flash('団体が見つかりません。', 'danger')
        return redirect(url_for('admin.organizations'))

    create_bulk_notifications(
        [m.id for m in org.members],
        '団体の承認が見送られました',
        f'「{org.name}」の承認が見送られました。事務局にお問い合わせください。',
    )
    log_activity(
        'reject_organization',
        target_type='organization', target_id=org.id,
        details=f'団体名={org.name}',
    )

    db.session.delete(org)
    db.session.commit()
    flash(f'「{org.name}」の登録を却下しました。', 'info')
    return redirect(url_for('admin.organizations'))


# === 団体登録申請 ===

@admin_bp.route('/organizations/register', methods=['GET', 'POST'])
@login_required
def register_organization():
    form = OrganizationRegistrationForm()
    if form.validate_on_submit():
        org = Organization(
            name=form.name.data,
            representative=form.representative.data,
            contact_email=form.contact_email.data,
            contact_phone=form.contact_phone.data,
            registration_number=form.registration_number.data,
            notes=form.notes.data,
        )
        db.session.add(org)
        db.session.flush()

        current_user.organization_id = org.id
        current_user.role = User.ROLE_ORG_LEADER
        log_activity(
            'register_organization',
            target_type='organization', target_id=org.id,
            details=f'団体名={org.name}',
        )
        db.session.commit()

        admin_ids = [row[0] for row in db.session.query(User.id).filter_by(role=User.ROLE_ADMIN).all()]
        create_bulk_notifications(
            admin_ids,
            '新しい団体登録申請',
            f'「{org.name}」から団体登録の申請がありました。',
            link=url_for('admin.organization_detail', id=org.id),
        )

        flash('団体登録を申請しました。事務局の承認をお待ちください。', 'info')
        return redirect(url_for('dashboard.index'))

    return render_template('admin/register_organization.html', form=form)


# === ユーザー管理 ===

@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/admin/users/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def user_detail(id):
    user = db.session.get(User, id)
    if not user:
        flash('ユーザーが見つかりません。', 'danger')
        return redirect(url_for('admin.users'))

    form = UserEditForm(obj=user)
    form.child_organization_id.choices = [(0, '（未設定）')] + [
        (o.id, o.name)
        for o in Organization.query.filter_by(is_approved=True).order_by(Organization.name).all()
    ]
    if request.method == 'GET':
        form.child_organization_id.data = user.child_organization_id or 0

    if form.validate_on_submit():
        user.role = form.role.data
        user.is_active = form.is_active.data
        user.child_organization_id = form.child_organization_id.data or None
        db.session.commit()
        flash('ユーザー情報を更新しました。', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin/user_detail.html', user=user, form=form)


# === レポート ===

@admin_bp.route('/admin/reports')
@login_required
@admin_required
def reports():
    today = date.today()
    month_start = today.replace(day=1)

    status_counts = dict(
        db.session.query(Reservation.status, func.count(Reservation.id))
        .filter(Reservation.date >= month_start)
        .group_by(Reservation.status)
        .all()
    )
    monthly_reservations = status_counts.get(Reservation.STATUS_CONFIRMED, 0)
    monthly_cancellations = status_counts.get(Reservation.STATUS_CANCELLED, 0)

    confirmed_count = func.count(case((Reservation.status == Reservation.STATUS_CONFIRMED, 1)))

    # 施設別利用状況（全施設を表示、予約0件も含む）
    facility_rows = (
        db.session.query(Facility, confirmed_count)
        .outerjoin(
            Reservation,
            (Reservation.facility_id == Facility.id) & (Reservation.date >= month_start),
        )
        .group_by(Facility.id)
        .all()
    )
    facility_stats = [{'facility': f, 'count': c} for f, c in facility_rows]

    # 団体別利用状況（承認済み団体のみ）
    org_rows = (
        db.session.query(Organization, confirmed_count)
        .outerjoin(
            Reservation,
            (Reservation.organization_id == Organization.id) & (Reservation.date >= month_start),
        )
        .filter(Organization.is_approved.is_(True))
        .group_by(Organization.id)
        .all()
    )
    org_stats = [{'org': o, 'count': c} for o, c in org_rows]

    return render_template('admin/reports.html',
                           monthly_reservations=monthly_reservations,
                           monthly_cancellations=monthly_cancellations,
                           facility_stats=facility_stats,
                           org_stats=org_stats,
                           month=today.strftime('%Y年%m月'),
                           export_from=month_start.isoformat(),
                           export_to=today.isoformat())


# === CSVエクスポート ===

def _parse_iso_date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _csv_response(rows, header, filename):
    buf = io.StringIO()
    buf.write('\ufeff')  # Excelで日本語を正しく扱うためのBOM
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@admin_bp.route('/admin/reports/export/reservations.csv')
@login_required
@admin_required
def export_reservations_csv():
    today = date.today()
    default_from = today.replace(day=1)
    date_from = _parse_iso_date(request.args.get('from'), default_from)
    date_to = _parse_iso_date(request.args.get('to'), today)

    reservations = (
        Reservation.query
        .options(
            joinedload(Reservation.facility).joinedload(Facility.school),
            joinedload(Reservation.organization),
            joinedload(Reservation.user),
        )
        .filter(Reservation.date >= date_from, Reservation.date <= date_to)
        .order_by(Reservation.date, Reservation.start_time)
        .all()
    )

    header = [
        '予約ID', '日付', '開始時刻', '終了時刻',
        '学校', '施設', '施設区分', '団体名', 'いなチャレ認定',
        '予約者', '参加予定人数', '目的', 'ステータス',
        'キャンセル理由', '登録日時',
    ]
    rows = []
    for r in reservations:
        facility = r.facility
        school_name = facility.school.name if facility and facility.school else ''
        facility_name = facility.name if facility else ''
        facility_type = facility.type_label if facility else ''
        org_name = r.organization.name if r.organization else ''
        is_certified = 'はい' if (r.organization and r.organization.is_inachalle_certified) else 'いいえ'
        user_name = r.user.display_name if r.user else ''
        rows.append([
            r.id,
            r.date.isoformat(),
            r.start_time.strftime('%H:%M'),
            r.end_time.strftime('%H:%M'),
            school_name,
            facility_name,
            facility_type,
            org_name,
            is_certified,
            user_name,
            r.expected_participants or '',
            r.purpose or '',
            r.status_label,
            r.cancellation_reason or '',
            r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
        ])

    filename = f'reservations_{date_from.isoformat()}_{date_to.isoformat()}.csv'
    return _csv_response(rows, header, filename)


@admin_bp.route('/admin/reports/export/organizations.csv')
@login_required
@admin_required
def export_organizations_csv():
    orgs = Organization.query.order_by(Organization.created_at.desc()).all()
    header = [
        '団体ID', '団体名', '代表者', '連絡先メール', '連絡先電話',
        '登録番号', 'ステータス', 'いなチャレ認定', '予約可能日数', '備考', '登録日',
    ]
    rows = []
    for org in orgs:
        rows.append([
            org.id,
            org.name,
            org.representative,
            org.contact_email or '',
            org.contact_phone or '',
            org.registration_number or '',
            org.status_label,
            'はい' if org.is_inachalle_certified else 'いいえ',
            org.advance_days,
            (org.notes or '').replace('\n', ' '),
            org.created_at.strftime('%Y-%m-%d') if org.created_at else '',
        ])
    filename = f'organizations_{date.today().isoformat()}.csv'
    return _csv_response(rows, header, filename)


@admin_bp.route('/admin/reports/export/chutairen-roster.csv')
@login_required
@admin_required
def export_chutairen_roster_csv():
    """中体連提出用: いなチャレ認定かつ承認済みの団体と所属指導者の一覧。

    1行 = 1 (団体, 指導者) ペア。指導者がいない団体も1行出力する。
    """
    certified_orgs = (
        Organization.query
        .filter(
            Organization.is_inachalle_certified.is_(True),
            Organization.is_approved.is_(True),
        )
        .order_by(Organization.name)
        .all()
    )

    header = [
        '団体ID', '団体名', '代表者', '登録番号', '連絡先メール', '連絡先電話',
        '指導者氏名', '指導者氏名カナ', '指導者メール', '指導者電話',
        '報酬区分', '資格・指導経歴', '教職員兼職兼業',
    ]
    rows = []
    for org in certified_orgs:
        active_coaches = [c for c in org.coaches if c.is_active]
        if not active_coaches:
            rows.append([
                org.id, org.name, org.representative, org.registration_number or '',
                org.contact_email or '', org.contact_phone or '',
                '（指導者未登録）', '', '', '', '', '', '',
            ])
            continue
        for coach in sorted(active_coaches, key=lambda c: c.full_name):
            rows.append([
                org.id, org.name, org.representative, org.registration_number or '',
                org.contact_email or '', org.contact_phone or '',
                coach.full_name, coach.full_name_kana or '',
                coach.email or '', coach.phone or '',
                coach.compensation_label,
                (coach.qualification or '').replace('\n', ' '),
                'はい' if coach.is_teacher_dual_role else 'いいえ',
            ])
    filename = f'chutairen_roster_{date.today().isoformat()}.csv'
    return _csv_response(rows, header, filename)


# === 活動ログ（監査） ===

ACTIVITY_ACTION_LABELS = {
    'approve_organization': '団体承認',
    'toggle_certification': '認定ステータス変更',
    'reject_organization': '団体却下',
    'register_organization': '団体登録申請',
    'create_school_block': '学校行事ブロック作成',
    'create_reservation': '予約作成',
    'cancel_reservation': '予約キャンセル',
}


@admin_bp.route('/admin/activity-logs')
@login_required
@admin_required
def activity_logs():
    today = date.today()
    default_from = today - timedelta(days=30)
    date_from = _parse_iso_date(request.args.get('from'), default_from)
    date_to = _parse_iso_date(request.args.get('to'), today)
    action = request.args.get('action') or ''
    user_id_raw = request.args.get('user_id') or ''
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 50

    query = (
        ActivityLog.query
        .options(joinedload(ActivityLog.user))
        .filter(ActivityLog.created_at >= datetime.combine(date_from, time.min))
        .filter(ActivityLog.created_at <= datetime.combine(date_to, time.max))
    )
    if action:
        query = query.filter(ActivityLog.action == action)
    if user_id_raw.isdigit():
        query = query.filter(ActivityLog.user_id == int(user_id_raw))

    total = query.count()
    logs = (
        query.order_by(ActivityLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    actions_known = list(ACTIVITY_ACTION_LABELS.items())
    return render_template(
        'admin/activity_logs.html',
        logs=logs,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page,
        date_from=date_from.isoformat(),
        date_to=date_to.isoformat(),
        action=action,
        user_id=user_id_raw,
        action_choices=actions_known,
        action_labels=ACTIVITY_ACTION_LABELS,
    )


# === 月報（印刷用） ===

def _reservation_minutes(status_filter, start, end):
    """Return total minutes of reservations in [start, end] filtered by status."""
    rows = (
        db.session.query(Reservation.start_time, Reservation.end_time)
        .filter(
            Reservation.date >= start,
            Reservation.date <= end,
            Reservation.status == status_filter,
        )
        .all()
    )
    total = 0
    for s, e in rows:
        s_dt = datetime.combine(date.min, s)
        e_dt = datetime.combine(date.min, e)
        m = int((e_dt - s_dt).total_seconds() // 60)
        if m > 0:
            total += m
    return total


@admin_bp.route('/admin/reports/monthly')
@login_required
@admin_required
def monthly_report():
    today = date.today()
    try:
        year = int(request.args.get('year', today.year))
        month = int(request.args.get('month', today.month))
        if not 1 <= month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year, 12, 31)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    confirmed_count = func.count(case((Reservation.status == Reservation.STATUS_CONFIRMED, 1)))

    total_confirmed = (
        db.session.query(func.count(Reservation.id))
        .filter(
            Reservation.date >= month_start,
            Reservation.date <= month_end,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        )
        .scalar() or 0
    )
    total_cancelled = (
        db.session.query(func.count(Reservation.id))
        .filter(
            Reservation.date >= month_start,
            Reservation.date <= month_end,
            Reservation.status == Reservation.STATUS_CANCELLED,
        )
        .scalar() or 0
    )
    total_confirmed_minutes = _reservation_minutes(
        Reservation.STATUS_CONFIRMED, month_start, month_end,
    )

    facility_rows = (
        db.session.query(Facility, confirmed_count)
        .outerjoin(
            Reservation,
            (Reservation.facility_id == Facility.id)
            & (Reservation.date >= month_start)
            & (Reservation.date <= month_end),
        )
        .group_by(Facility.id)
        .order_by(Facility.id)
        .all()
    )

    org_rows = (
        db.session.query(Organization, confirmed_count)
        .outerjoin(
            Reservation,
            (Reservation.organization_id == Organization.id)
            & (Reservation.date >= month_start)
            & (Reservation.date <= month_end),
        )
        .filter(Organization.is_approved.is_(True))
        .group_by(Organization.id)
        .order_by(Organization.name)
        .all()
    )

    # 指導者別謝金見込（有償のみ）
    coaches = (
        Coach.query
        .options(joinedload(Coach.organizations))
        .filter(
            Coach.is_active.is_(True),
            Coach.compensation_type == Coach.COMPENSATION_PAID,
        )
        .order_by(Coach.full_name)
        .all()
    )
    minutes_by_org = {}
    rows = (
        db.session.query(Reservation.organization_id, Reservation.start_time, Reservation.end_time)
        .filter(
            Reservation.date >= month_start,
            Reservation.date <= month_end,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        )
        .all()
    )
    for org_id, s, e in rows:
        minutes = int((datetime.combine(date.min, e) - datetime.combine(date.min, s)).total_seconds() // 60)
        if minutes > 0:
            minutes_by_org[org_id] = minutes_by_org.get(org_id, 0) + minutes

    compensation_rows = []
    total_compensation = 0
    for c in coaches:
        for org in c.organizations:
            mins = minutes_by_org.get(org.id, 0)
            hours = mins / 60
            amount = int(round(hours * (c.hourly_rate or 0)))
            if mins == 0 and amount == 0:
                continue
            total_compensation += amount
            compensation_rows.append({
                'coach': c, 'org': org,
                'minutes': mins, 'hours': hours, 'amount': amount,
            })

    return render_template(
        'admin/monthly_report.html',
        year=year, month=month,
        month_start=month_start, month_end=month_end,
        total_confirmed=total_confirmed,
        total_cancelled=total_cancelled,
        total_confirmed_minutes=total_confirmed_minutes,
        total_confirmed_hours=round(total_confirmed_minutes / 60, 2),
        facility_stats=[{'facility': f, 'count': c} for f, c in facility_rows],
        org_stats=[{'org': o, 'count': c} for o, c in org_rows],
        compensation_rows=compensation_rows,
        total_compensation=total_compensation,
        generated_at=datetime.now(),
        is_fixed_rate_period=is_fixed_rate_period(month_start),
        fiscal_label=fiscal_period_label(month_start),
        fixed_paid_rate=FIXED_PAID_RATE,
    )
