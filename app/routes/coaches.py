import csv
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.forms.coach import CoachForm
from app.models.coach import Coach
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.user import User
from app.services.activity_log_service import log_activity
from app.utils.decorators import admin_required
from app.utils.fiscal import (
    FIXED_PAID_RATE,
    fiscal_period_label,
    is_fixed_rate_period,
)

coaches_bp = Blueprint('coaches', __name__)

# 教職員兼職兼業者の週間活動時間上限: 19時間45分 = 1185分
TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES = 19 * 60 + 45


def _week_monday(target_date):
    return target_date - timedelta(days=target_date.weekday())


def _parse_iso(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def _reservation_minutes_by_org(date_from, date_to):
    """Return {organization_id: total_minutes} for confirmed reservations in range."""
    rows = (
        db.session.query(Reservation.organization_id, Reservation.start_time, Reservation.end_time)
        .filter(
            Reservation.date >= date_from,
            Reservation.date <= date_to,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        )
        .all()
    )
    totals = {}
    for org_id, start_t, end_t in rows:
        start = datetime.combine(date.min, start_t)
        end = datetime.combine(date.min, end_t)
        minutes = int((end - start).total_seconds() // 60)
        if minutes <= 0:
            continue
        totals[org_id] = totals.get(org_id, 0) + minutes
    return totals


def _effective_hourly_rate(compensation_type, form_rate):
    """Return the hourly rate to persist based on fiscal period policy.

    During fixed period: paid → 1,482円 / unpaid → 0 (regardless of form input).
    During free period: use the value provided in the form.
    """
    if compensation_type == Coach.COMPENSATION_UNPAID:
        return 0
    if is_fixed_rate_period():
        return FIXED_PAID_RATE
    return int(form_rate or 0)


def _set_org_choices(form):
    form.organization_ids.choices = [
        (o.id, o.name)
        for o in Organization.query.filter_by(is_approved=True).order_by(Organization.name).all()
    ]


def _set_user_choices(form, current_coach=None):
    """Build user picker: users that are eligible to be linked as coach accounts.

    Excludes users already linked to another coach (unless it's the one being edited).
    """
    taken_user_ids = {
        uid for (uid,) in db.session.query(Coach.user_id).filter(Coach.user_id.isnot(None)).all()
    }
    if current_coach and current_coach.user_id:
        taken_user_ids.discard(current_coach.user_id)

    candidates = (
        User.query
        .filter(User.role.in_([User.ROLE_COACH, User.ROLE_RESIDENT]))
        .filter(User.is_active.is_(True))
        .order_by(User.display_name)
        .all()
    )
    choices = [(0, '（未連携）')]
    for u in candidates:
        if u.id in taken_user_ids:
            continue
        choices.append((u.id, f'{u.display_name} ({u.email})'))
    form.user_id.choices = choices


@coaches_bp.route('/admin/coaches')
@login_required
@admin_required
def list_coaches():
    only_multi = request.args.get('multi') == '1'
    query = Coach.query.options(joinedload(Coach.organizations)).order_by(Coach.full_name)
    coaches = query.all()
    if only_multi:
        coaches = [c for c in coaches if c.is_multi_affiliated]
    total = len(coaches)
    multi_count = sum(1 for c in Coach.query.options(joinedload(Coach.organizations)).all() if c.is_multi_affiliated)
    return render_template(
        'admin/coaches.html',
        coaches=coaches, total=total, multi_count=multi_count, only_multi=only_multi,
        is_fixed_rate_period=is_fixed_rate_period(),
        fiscal_label=fiscal_period_label(),
        fixed_paid_rate=FIXED_PAID_RATE,
    )


@coaches_bp.route('/admin/coaches/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_coach():
    form = CoachForm()
    _set_org_choices(form)
    _set_user_choices(form)

    if form.validate_on_submit():
        rate = _effective_hourly_rate(form.compensation_type.data, form.hourly_rate.data)
        coach = Coach(
            full_name=form.full_name.data.strip(),
            full_name_kana=form.full_name_kana.data or None,
            email=form.email.data or None,
            phone=form.phone.data or None,
            birth_date=form.birth_date.data,
            qualification=form.qualification.data or None,
            compensation_type=form.compensation_type.data,
            hourly_rate=rate,
            is_teacher_dual_role=form.is_teacher_dual_role.data,
            is_active=form.is_active.data,
            user_id=form.user_id.data if form.user_id.data else None,
            notes=form.notes.data or None,
        )
        if coach.user_id:
            linked_user = db.session.get(User, coach.user_id)
            if linked_user:
                linked_user.role = User.ROLE_COACH
        selected_orgs = Organization.query.filter(Organization.id.in_(form.organization_ids.data)).all()
        coach.organizations = selected_orgs
        db.session.add(coach)
        db.session.flush()
        log_activity(
            'register_coach',
            target_type='coach', target_id=coach.id,
            details=f'name={coach.full_name} orgs={len(selected_orgs)}',
        )
        db.session.commit()

        if coach.is_multi_affiliated:
            flash(
                f'指導者「{coach.full_name}」を登録しました。'
                f'複数団体（{coach.organization_count}団体）に所属しているため、'
                '謝金計算時のダブルカウントに注意してください。',
                'warning',
            )
        else:
            flash(f'指導者「{coach.full_name}」を登録しました。', 'success')
        return redirect(url_for('coaches.list_coaches'))

    return render_template(
        'admin/coach_form.html',
        form=form, coach=None,
        is_fixed_rate_period=is_fixed_rate_period(),
        fiscal_label=fiscal_period_label(),
        fixed_paid_rate=FIXED_PAID_RATE,
    )


@coaches_bp.route('/admin/coaches/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_coach(id):
    coach = db.session.get(Coach, id)
    if not coach:
        flash('指導者が見つかりません。', 'danger')
        return redirect(url_for('coaches.list_coaches'))

    form = CoachForm(obj=coach)
    _set_org_choices(form)
    _set_user_choices(form, current_coach=coach)
    if request.method == 'GET':
        form.organization_ids.data = [o.id for o in coach.organizations]
        form.user_id.data = coach.user_id or 0

    if form.validate_on_submit():
        coach.full_name = form.full_name.data.strip()
        coach.full_name_kana = form.full_name_kana.data or None
        coach.email = form.email.data or None
        coach.phone = form.phone.data or None
        coach.birth_date = form.birth_date.data
        coach.qualification = form.qualification.data or None
        coach.compensation_type = form.compensation_type.data
        coach.hourly_rate = _effective_hourly_rate(
            form.compensation_type.data, form.hourly_rate.data,
        )
        coach.is_teacher_dual_role = form.is_teacher_dual_role.data
        coach.is_active = form.is_active.data
        new_user_id = form.user_id.data or None
        if coach.user_id and coach.user_id != new_user_id:
            # Unlink previous user
            prev = db.session.get(User, coach.user_id)
            if prev and prev.role == User.ROLE_COACH:
                prev.role = User.ROLE_RESIDENT
        coach.user_id = new_user_id
        if coach.user_id:
            linked_user = db.session.get(User, coach.user_id)
            if linked_user:
                linked_user.role = User.ROLE_COACH
        coach.notes = form.notes.data or None
        coach.organizations = Organization.query.filter(
            Organization.id.in_(form.organization_ids.data),
        ).all()
        log_activity(
            'update_coach',
            target_type='coach', target_id=coach.id,
            details=f'name={coach.full_name}',
        )
        db.session.commit()
        flash(f'指導者「{coach.full_name}」を更新しました。', 'success')
        return redirect(url_for('coaches.list_coaches'))

    return render_template(
        'admin/coach_form.html',
        form=form, coach=coach,
        is_fixed_rate_period=is_fixed_rate_period(),
        fiscal_label=fiscal_period_label(),
        fixed_paid_rate=FIXED_PAID_RATE,
    )


@coaches_bp.route('/admin/coaches/compensation.csv')
@login_required
@admin_required
def export_compensation_csv():
    """指導者×団体ごとに、期間内の予約時間から謝金見込を算出してCSV出力。

    注意: 予約は団体単位で登録されるため、現状は「指導者が所属団体の全活動を指導した」と仮定した
    見込み額。実際の稼働は編集して調整する。
    """
    today = date.today()
    default_from = today.replace(day=1)
    date_from = _parse_iso(request.args.get('from'), default_from)
    date_to = _parse_iso(request.args.get('to'), today)

    minutes_by_org = _reservation_minutes_by_org(date_from, date_to)

    coaches = (
        Coach.query
        .options(joinedload(Coach.organizations))
        .filter_by(is_active=True)
        .order_by(Coach.full_name)
        .all()
    )

    header = [
        '指導者ID', '氏名', '報酬区分', '時間単価(円)', '教職員兼職',
        '団体ID', '団体名', '稼働時間(分)', '稼働時間(時)', '謝金見込(円)', '備考',
    ]
    rows = []
    for c in coaches:
        if not c.organizations:
            rows.append([
                c.id, c.full_name, c.compensation_label, c.hourly_rate or 0,
                'はい' if c.is_teacher_dual_role else 'いいえ',
                '', '（所属なし）', 0, 0, 0, '所属団体未設定',
            ])
            continue
        for org in c.organizations:
            minutes = minutes_by_org.get(org.id, 0)
            hours = minutes / 60
            amount = int(round(hours * (c.hourly_rate or 0)))
            note_parts = []
            if c.is_multi_affiliated:
                note_parts.append('複数団体所属（ダブルカウント注意）')
            if c.compensation_type == Coach.COMPENSATION_UNPAID:
                note_parts.append('無償')
            rows.append([
                c.id, c.full_name, c.compensation_label, c.hourly_rate or 0,
                'はい' if c.is_teacher_dual_role else 'いいえ',
                org.id, org.name, minutes, round(hours, 2), amount,
                '; '.join(note_parts),
            ])

    buf = io.StringIO()
    buf.write('\ufeff')
    if is_fixed_rate_period():
        buf.write(f'# {fiscal_period_label()} / 有償={FIXED_PAID_RATE}円 固定\n')
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    filename = f'compensation_{date_from.isoformat()}_{date_to.isoformat()}.csv'
    return Response(
        buf.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@coaches_bp.route('/admin/coaches/dual-role-workload')
@login_required
@admin_required
def dual_role_workload():
    """教職員兼職兼業者の週間活動時間チェック。19h45mを超える者を警告。"""
    today = date.today()
    week_start_raw = request.args.get('week')
    week_start = _parse_iso(week_start_raw, _week_monday(today))
    # 必ず月曜日始まりに正規化
    week_start = _week_monday(week_start)
    week_end = week_start + timedelta(days=6)

    teacher_coaches = (
        Coach.query
        .options(joinedload(Coach.organizations))
        .filter_by(is_teacher_dual_role=True, is_active=True)
        .order_by(Coach.full_name)
        .all()
    )

    minutes_by_org = _reservation_minutes_by_org(week_start, week_end)

    results = []
    for coach in teacher_coaches:
        minutes = sum(minutes_by_org.get(o.id, 0) for o in coach.organizations)
        hours = minutes / 60
        over = minutes > TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES
        # 80%以上で注意喚起
        warning = (not over) and minutes >= 0.8 * TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES
        results.append({
            'coach': coach,
            'minutes': minutes,
            'hours': hours,
            'limit_minutes': TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES,
            'over': over,
            'warning': warning,
            'ratio': minutes / TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES if TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES else 0,
        })

    # Sort: over > warning > normal, within each descending by minutes
    results.sort(key=lambda r: (-int(r['over']), -int(r['warning']), -r['minutes']))

    return render_template(
        'admin/dual_role_workload.html',
        week_start=week_start,
        week_end=week_end,
        results=results,
        limit_minutes=TEACHER_DUAL_ROLE_WEEKLY_LIMIT_MINUTES,
        limit_label='19時間45分',
        prev_week=(week_start - timedelta(days=7)).isoformat(),
        next_week=(week_start + timedelta(days=7)).isoformat(),
        total=len(results),
        over_count=sum(1 for r in results if r['over']),
        warning_count=sum(1 for r in results if r['warning']),
    )
