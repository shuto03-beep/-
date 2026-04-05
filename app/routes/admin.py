from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.facility import Facility
from app.models.school import School
from app.forms.admin import OrganizationRegistrationForm, UserEditForm
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
