import io
import csv
from datetime import datetime, date, time
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user
from app.extensions import db
from app.models.reservation import Reservation
from app.models.facility import Facility
from app.models.school import School
from app.forms.reservation import ReservationForm, EditReservationForm, CancelReservationForm
from app.models.organization import Organization
from app.services.reservation_service import (
    get_available_slots, create_reservation, update_reservation,
    cancel_reservation, ReservationConflictError, SchoolBlockedError, BookingPeriodError,
)
from app.services.notification_service import create_notification
from app.utils.decorators import role_required
from app.utils.helpers import time_slot_label
from app.services.activity_log_service import log_activity

reservations_bp = Blueprint('reservations', __name__)


def _build_reservation_query():
    """検索条件付きの予約クエリを構築する"""
    if current_user.is_admin:
        query = Reservation.query
    elif current_user.organization_id:
        query = Reservation.query.filter_by(organization_id=current_user.organization_id)
    else:
        return None

    status_filter = request.args.get('status', 'confirmed')
    if status_filter == 'confirmed':
        query = query.filter(Reservation.status == Reservation.STATUS_CONFIRMED)
    elif status_filter == 'cancelled':
        query = query.filter(Reservation.status == Reservation.STATUS_CANCELLED)

    facility_id = request.args.get('facility_id', type=int)
    if facility_id:
        query = query.filter(Reservation.facility_id == facility_id)

    org_id = request.args.get('org_id', type=int)
    if org_id and current_user.is_admin:
        query = query.filter(Reservation.organization_id == org_id)

    date_from = request.args.get('date_from')
    if date_from:
        try:
            query = query.filter(Reservation.date >= date.fromisoformat(date_from))
        except ValueError:
            pass

    date_to = request.args.get('date_to')
    if date_to:
        try:
            query = query.filter(Reservation.date <= date.fromisoformat(date_to))
        except ValueError:
            pass

    return query.order_by(Reservation.date.desc(), Reservation.start_time.desc())


@reservations_bp.route('/reservations')
@login_required
def list_reservations():
    query = _build_reservation_query()
    if query is None:
        flash('団体に所属していないため、予約一覧を表示できません。', 'warning')
        return redirect(url_for('dashboard.index'))

    page = request.args.get('page', 1, type=int)
    reservations = query.paginate(page=page, per_page=20)

    facilities = Facility.query.filter_by(is_active=True).order_by(Facility.school_id, Facility.name).all()
    organizations = Organization.query.filter_by(is_approved=True).order_by(Organization.name).all() if current_user.is_admin else []

    return render_template('reservations/list.html',
                           reservations=reservations,
                           status_filter=request.args.get('status', 'confirmed'),
                           facilities=facilities,
                           organizations=organizations,
                           filters={
                               'facility_id': request.args.get('facility_id', '', type=str),
                               'org_id': request.args.get('org_id', '', type=str),
                               'date_from': request.args.get('date_from', ''),
                               'date_to': request.args.get('date_to', ''),
                           })


@reservations_bp.route('/reservations/export.csv')
@login_required
def export_csv():
    query = _build_reservation_query()
    if query is None:
        flash('団体に所属していないため、エクスポートできません。', 'warning')
        return redirect(url_for('dashboard.index'))

    reservations = query.all()

    output = io.StringIO()
    output.write('\ufeff')  # BOM for Excel
    writer = csv.writer(output)
    writer.writerow(['ID', '日付', '時間', '施設', '団体', '予約者', '目的', '参加人数', '状態', '備考'])

    for r in reservations:
        writer.writerow([
            r.id,
            r.date.strftime('%Y/%m/%d'),
            r.time_range,
            r.facility.full_name,
            r.organization.name,
            r.user.display_name,
            r.purpose or '',
            r.expected_participants or '',
            r.status_label,
            r.notes or '',
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=reservations.csv'},
    )


@reservations_bp.route('/reservations/new', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'org_leader')
def new_reservation():
    if not current_user.organization_id and not current_user.is_admin:
        flash('団体に所属していないため、予約できません。', 'warning')
        return redirect(url_for('dashboard.index'))

    form = ReservationForm()
    schools = School.query.all()
    facilities = Facility.query.filter_by(is_active=True).all()

    facility_choices = [(f.id, f'{f.school.name} - {f.name}（{f.type_label}）') for f in facilities]
    form.facility_id.choices = [(0, '施設を選択してください')] + facility_choices
    form.time_slot.choices = [('', '日付を選択後に表示されます')]

    booking_info = None
    if current_user.organization_id:
        org = db.session.get(Organization, current_user.organization_id)
        if org:
            booking_info = {
                'is_certified': org.is_inachalle_certified,
                'advance_days': org.advance_days,
                'max_date': org.latest_bookable_date.isoformat(),
                'label': 'いなチャレ認定団体' if org.is_inachalle_certified else '一般団体',
            }
    organizations = Organization.query.filter_by(is_approved=True).all() if current_user.is_admin else []

    if form.validate_on_submit():
        try:
            parts = form.time_slot.data.split('-')
            start_time = time(int(parts[0]), int(parts[1]))
            end_time = time(int(parts[2]), int(parts[3]))
        except (ValueError, IndexError):
            flash('時間枠の形式が正しくありません。', 'danger')
            return render_template('reservations/new.html', form=form, schools=schools, today_str=date.today().isoformat(), booking_info=booking_info, organizations=organizations)

        org_id = current_user.organization_id
        if current_user.is_admin and not org_id:
            org_id = request.form.get('organization_id', type=int)
            if not org_id:
                flash('団体を選択してください。', 'danger')
                return render_template('reservations/new.html', form=form, schools=schools, today_str=date.today().isoformat(), booking_info=booking_info, organizations=organizations)

        try:
            reservation = create_reservation(
                facility_id=form.facility_id.data,
                organization_id=org_id,
                user_id=current_user.id,
                target_date=form.date.data,
                start_time=start_time,
                end_time=end_time,
                purpose=form.purpose.data,
                expected_participants=form.expected_participants.data,
                notes=form.notes.data,
            )
            log_activity(current_user.id, '予約作成', 'reservation', reservation.id,
                         f'{reservation.facility.full_name} {reservation.date} {reservation.time_range}')
            flash('予約が確定しました！', 'success')
            return redirect(url_for('reservations.detail', id=reservation.id))
        except ReservationConflictError as e:
            flash(str(e), 'danger')
        except SchoolBlockedError as e:
            flash(str(e), 'danger')
        except BookingPeriodError as e:
            flash(str(e), 'danger')

    return render_template('reservations/new.html', form=form, schools=schools,
                           today_str=date.today().isoformat(), booking_info=booking_info,
                           organizations=organizations)


@reservations_bp.route('/reservations/<int:id>')
@login_required
def detail(id):
    reservation = db.session.get(Reservation, id)
    if not reservation:
        flash('予約が見つかりません。', 'danger')
        return redirect(url_for('reservations.list_reservations'))

    if not current_user.is_admin and reservation.organization_id != current_user.organization_id:
        flash('この予約にアクセスする権限がありません。', 'danger')
        return redirect(url_for('reservations.list_reservations'))

    cancel_form = CancelReservationForm()
    return render_template('reservations/detail.html',
                           reservation=reservation,
                           cancel_form=cancel_form)


@reservations_bp.route('/reservations/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'org_leader')
def edit_reservation(id):
    reservation = db.session.get(Reservation, id)
    if not reservation:
        flash('予約が見つかりません。', 'danger')
        return redirect(url_for('reservations.list_reservations'))

    if not reservation.is_active:
        flash('キャンセル済みの予約は変更できません。', 'warning')
        return redirect(url_for('reservations.detail', id=id))

    if not current_user.is_admin and reservation.organization_id != current_user.organization_id:
        flash('この予約を変更する権限がありません。', 'danger')
        return redirect(url_for('reservations.list_reservations'))

    form = EditReservationForm()
    schools = School.query.all()
    facilities = Facility.query.filter_by(is_active=True).all()
    facility_choices = [(f.id, f'{f.school.name} - {f.name}（{f.type_label}）') for f in facilities]
    form.facility_id.choices = [(0, '施設を選択してください')] + facility_choices
    form.time_slot.choices = [('', '日付を選択後に表示されます')]

    if form.validate_on_submit():
        try:
            parts = form.time_slot.data.split('-')
            start_time = time(int(parts[0]), int(parts[1]))
            end_time = time(int(parts[2]), int(parts[3]))
        except (ValueError, IndexError):
            flash('時間枠の形式が正しくありません。', 'danger')
            return render_template('reservations/edit.html', form=form, reservation=reservation, schools=schools, today_str=date.today().isoformat())

        try:
            update_reservation(
                reservation_id=reservation.id,
                user_id=current_user.id,
                facility_id=form.facility_id.data,
                target_date=form.date.data,
                start_time=start_time,
                end_time=end_time,
                purpose=form.purpose.data,
                expected_participants=form.expected_participants.data,
                notes=form.notes.data,
            )
            log_activity(current_user.id, '予約変更', 'reservation', reservation.id,
                         f'{reservation.facility.full_name} {reservation.date} {reservation.time_range}')
            flash('予約内容を変更しました。', 'success')
            return redirect(url_for('reservations.detail', id=reservation.id))
        except ReservationConflictError as e:
            flash(str(e), 'danger')
        except SchoolBlockedError as e:
            flash(str(e), 'danger')
        except BookingPeriodError as e:
            flash(str(e), 'danger')
    elif request.method == 'GET':
        form.facility_id.data = reservation.facility_id
        form.date.data = reservation.date
        form.time_slot.data = f'{reservation.start_time.strftime("%H-%M")}-{reservation.end_time.strftime("%H-%M")}'
        form.purpose.data = reservation.purpose
        form.expected_participants.data = reservation.expected_participants
        form.notes.data = reservation.notes

    booking_info = None
    org = db.session.get(Organization, reservation.organization_id)
    if org:
        booking_info = {
            'is_certified': org.is_inachalle_certified,
            'advance_days': org.advance_days,
            'max_date': org.latest_bookable_date.isoformat(),
            'label': 'いなチャレ認定団体' if org.is_inachalle_certified else '一般団体',
        }

    return render_template('reservations/edit.html', form=form, reservation=reservation,
                           schools=schools, today_str=date.today().isoformat(), booking_info=booking_info)


@reservations_bp.route('/reservations/<int:id>/cancel', methods=['POST'])
@login_required
@role_required('admin', 'org_leader')
def cancel(id):
    reservation = db.session.get(Reservation, id)
    if not reservation:
        flash('予約が見つかりません。', 'danger')
        return redirect(url_for('reservations.list_reservations'))

    if not current_user.is_admin and reservation.organization_id != current_user.organization_id:
        flash('この予約をキャンセルする権限がありません。', 'danger')
        return redirect(url_for('reservations.list_reservations'))

    form = CancelReservationForm()
    if form.validate_on_submit():
        cancel_reservation(reservation.id, current_user.id, form.cancellation_reason.data)
        log_activity(current_user.id, '予約キャンセル', 'reservation', reservation.id,
                     f'{reservation.facility.full_name} {reservation.date} {reservation.time_range} 理由: {form.cancellation_reason.data}')
        flash('予約をキャンセルしました。', 'info')

    return redirect(url_for('reservations.detail', id=id))


@reservations_bp.route('/api/available_slots')
@login_required
def available_slots():
    facility_id = request.args.get('facility_id', type=int)
    date_str = request.args.get('date')

    if not facility_id or not date_str:
        return jsonify([])

    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify([])

    if target_date < date.today():
        return jsonify([])

    # 予約可能期間チェック（管理者は制限なし）
    if not current_user.is_admin and current_user.organization_id:
        org = db.session.get(Organization, current_user.organization_id)
        if org and not org.can_book_date(target_date):
            return jsonify({'error': True, 'message': f'この日付は予約可能期間外です。{org.advance_days}日先まで予約できます。'})

    exclude_id = request.args.get('exclude_reservation', type=int)
    slots = get_available_slots(facility_id, target_date, exclude_reservation_id=exclude_id)
    return jsonify([{
        'value': f'{s.strftime("%H-%M")}-{e.strftime("%H-%M")}',
        'label': time_slot_label(s, e),
    } for s, e in slots])
