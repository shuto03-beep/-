from datetime import date, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.facility import Facility, FacilityTimeSlot
from app.models.school import School
from app.forms.admin import OrganizationRegistrationForm, UserEditForm
from app.forms.facility import SchoolForm, FacilityForm, TimeSlotForm
from app.services.notification_service import create_notification
from app.utils.decorators import admin_required

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
    db.session.commit()

    cert_text = 'いなチャレ認定団体として' if certify else ''
    for member in org.members:
        create_notification(
            member.id,
            '団体が承認されました',
            f'「{org.name}」が{cert_text}事務局に承認されました。施設の予約が可能になりました。'
            + (f' 認定団体として{org.advance_days}日先まで優先予約が可能です。' if certify else ''),
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
    db.session.commit()

    if org.is_inachalle_certified:
        status_msg = f'いなチャレ認定団体に設定しました（{org.advance_days}日先まで優先予約可能）'
    else:
        status_msg = f'いなチャレ認定を解除しました（{org.advance_days}日先まで予約可能）'

    for member in org.members:
        create_notification(
            member.id,
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

    for member in org.members:
        create_notification(
            member.id,
            '団体の承認が見送られました',
            f'「{org.name}」の承認が見送られました。事務局にお問い合わせください。',
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
        db.session.commit()

        admins = User.query.filter_by(role=User.ROLE_ADMIN).all()
        for admin in admins:
            create_notification(
                admin.id,
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
    if form.validate_on_submit():
        user.role = form.role.data
        user.is_active = form.is_active.data
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

    monthly_reservations = Reservation.query.filter(
        Reservation.date >= month_start,
        Reservation.status == Reservation.STATUS_CONFIRMED,
    ).count()

    monthly_cancellations = Reservation.query.filter(
        Reservation.date >= month_start,
        Reservation.status == Reservation.STATUS_CANCELLED,
    ).count()

    # 施設別利用状況
    facilities = Facility.query.all()
    facility_stats = []
    for f in facilities:
        count = Reservation.query.filter(
            Reservation.facility_id == f.id,
            Reservation.date >= month_start,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).count()
        facility_stats.append({'facility': f, 'count': count})

    # 団体別利用状況
    orgs = Organization.query.filter_by(is_approved=True).all()
    org_stats = []
    for org in orgs:
        count = Reservation.query.filter(
            Reservation.organization_id == org.id,
            Reservation.date >= month_start,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).count()
        org_stats.append({'org': org, 'count': count})

    return render_template('admin/reports.html',
                           monthly_reservations=monthly_reservations,
                           monthly_cancellations=monthly_cancellations,
                           facility_stats=facility_stats,
                           org_stats=org_stats,
                           month=today.strftime('%Y年%m月'))


# ===================================
# 学校管理
# ===================================

@admin_bp.route('/admin/schools')
@login_required
@admin_required
def schools():
    all_schools = School.query.all()
    return render_template('admin/schools.html', schools=all_schools)


@admin_bp.route('/admin/schools/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_school():
    form = SchoolForm()
    if form.validate_on_submit():
        school = School(
            name=form.name.data,
            code=form.code.data,
            address=form.address.data,
            contact_phone=form.contact_phone.data,
        )
        db.session.add(school)
        db.session.commit()
        flash(f'「{school.name}」を追加しました。', 'success')
        return redirect(url_for('admin.schools'))
    return render_template('admin/school_form.html', form=form, is_edit=False)


@admin_bp.route('/admin/schools/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_school(id):
    school = db.session.get(School, id)
    if not school:
        flash('学校が見つかりません。', 'danger')
        return redirect(url_for('admin.schools'))
    form = SchoolForm(obj=school)
    if form.validate_on_submit():
        school.name = form.name.data
        school.code = form.code.data
        school.address = form.address.data
        school.contact_phone = form.contact_phone.data
        db.session.commit()
        flash(f'「{school.name}」を更新しました。', 'success')
        return redirect(url_for('admin.schools'))
    return render_template('admin/school_form.html', form=form, is_edit=True, school=school)


# ===================================
# 施設管理
# ===================================

@admin_bp.route('/admin/facilities')
@login_required
@admin_required
def facilities():
    all_facilities = Facility.query.join(School).order_by(School.name, Facility.name).all()
    return render_template('admin/facilities.html', facilities=all_facilities)


@admin_bp.route('/admin/facilities/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_facility():
    form = FacilityForm()
    form.school_id.choices = [(s.id, s.name) for s in School.query.all()]
    form.is_active.data = True if request.method == 'GET' else form.is_active.data
    if form.validate_on_submit():
        facility = Facility(
            school_id=form.school_id.data,
            name=form.name.data,
            facility_type=form.facility_type.data,
            capacity=form.capacity.data,
            description=form.description.data,
            usage_rules=form.usage_rules.data,
            equipment=form.equipment.data,
            is_active=form.is_active.data,
        )
        db.session.add(facility)
        db.session.commit()
        flash(f'「{facility.full_name}」を追加しました。', 'success')
        return redirect(url_for('admin.facility_detail', id=facility.id))
    return render_template('admin/facility_form.html', form=form, is_edit=False)


@admin_bp.route('/admin/facilities/<int:id>')
@login_required
@admin_required
def facility_detail(id):
    facility = db.session.get(Facility, id)
    if not facility:
        flash('施設が見つかりません。', 'danger')
        return redirect(url_for('admin.facilities'))

    # 曜日ごとの時間設定を取得
    time_settings = {}
    for day in range(7):
        slots = FacilityTimeSlot.query.filter_by(
            facility_id=id, day_of_week=day
        ).order_by(FacilityTimeSlot.start_time).all()
        time_settings[day] = slots

    time_form = TimeSlotForm()
    day_labels = FacilityTimeSlot.DAY_LABELS

    return render_template('admin/facility_detail.html',
                           facility=facility,
                           time_settings=time_settings,
                           time_form=time_form,
                           day_labels=day_labels)


@admin_bp.route('/admin/facilities/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_facility(id):
    facility = db.session.get(Facility, id)
    if not facility:
        flash('施設が見つかりません。', 'danger')
        return redirect(url_for('admin.facilities'))

    form = FacilityForm(obj=facility)
    form.school_id.choices = [(s.id, s.name) for s in School.query.all()]
    if form.validate_on_submit():
        facility.school_id = form.school_id.data
        facility.name = form.name.data
        facility.facility_type = form.facility_type.data
        facility.capacity = form.capacity.data
        facility.description = form.description.data
        facility.usage_rules = form.usage_rules.data
        facility.equipment = form.equipment.data
        facility.is_active = form.is_active.data
        db.session.commit()
        flash(f'「{facility.full_name}」を更新しました。', 'success')
        return redirect(url_for('admin.facility_detail', id=id))
    return render_template('admin/facility_form.html', form=form, is_edit=True, facility=facility)


@admin_bp.route('/admin/facilities/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_facility(id):
    facility = db.session.get(Facility, id)
    if not facility:
        flash('施設が見つかりません。', 'danger')
        return redirect(url_for('admin.facilities'))
    facility.is_active = not facility.is_active
    db.session.commit()
    status = '有効' if facility.is_active else '無効'
    flash(f'「{facility.full_name}」を{status}にしました。', 'success')
    return redirect(url_for('admin.facilities'))


# ===================================
# 施設 利用可能時間設定
# ===================================

@admin_bp.route('/admin/facilities/<int:id>/timeslots/<int:day>', methods=['POST'])
@login_required
@admin_required
def add_timeslot(id, day):
    facility = db.session.get(Facility, id)
    if not facility or day < 0 or day > 6:
        flash('不正なリクエストです。', 'danger')
        return redirect(url_for('admin.facilities'))

    form = TimeSlotForm()
    if form.validate_on_submit():
        start_h = form.start_hour.data
        end_h = form.end_hour.data
        if start_h >= end_h:
            flash('開始時間は終了時間より前にしてください。', 'danger')
            return redirect(url_for('admin.facility_detail', id=id))

        # 1時間単位で追加
        for h in range(start_h, end_h):
            existing = FacilityTimeSlot.query.filter_by(
                facility_id=id, day_of_week=day,
                start_time=time(h, 0), end_time=time(h + 1, 0),
            ).first()
            if not existing:
                slot = FacilityTimeSlot(
                    facility_id=id,
                    day_of_week=day,
                    start_time=time(h, 0),
                    end_time=time(h + 1, 0),
                    is_available=True,
                )
                db.session.add(slot)

        db.session.commit()
        flash(f'{FacilityTimeSlot.DAY_LABELS[day]}曜日の時間枠を追加しました。', 'success')

    return redirect(url_for('admin.facility_detail', id=id))


@admin_bp.route('/admin/facilities/<int:fid>/timeslots/<int:slot_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_timeslot(fid, slot_id):
    slot = db.session.get(FacilityTimeSlot, slot_id)
    if not slot or slot.facility_id != fid:
        flash('不正なリクエストです。', 'danger')
        return redirect(url_for('admin.facilities'))

    db.session.delete(slot)
    db.session.commit()
    flash('時間枠を削除しました。', 'info')
    return redirect(url_for('admin.facility_detail', id=fid))


@admin_bp.route('/admin/facilities/<int:id>/timeslots/clear/<int:day>', methods=['POST'])
@login_required
@admin_required
def clear_timeslots(id, day):
    FacilityTimeSlot.query.filter_by(facility_id=id, day_of_week=day).delete()
    db.session.commit()
    flash(f'{FacilityTimeSlot.DAY_LABELS[day]}曜日の設定をリセットしました（デフォルトに戻ります）。', 'info')
    return redirect(url_for('admin.facility_detail', id=id))
