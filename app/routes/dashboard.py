from datetime import date
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.reservation import Reservation
from app.models.organization import Organization
from app.models.notification import Notification

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def root():
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    context = {}

    if current_user.is_admin:
        pending_orgs = Organization.query.filter_by(is_approved=False).count()
        today_reservations = Reservation.query.filter(
            Reservation.date == today,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).count()
        context.update({
            'pending_orgs': pending_orgs,
            'today_reservations': today_reservations,
            'total_orgs': Organization.query.count(),
        })
    elif current_user.is_org_leader and current_user.organization_id:
        upcoming = Reservation.query.filter(
            Reservation.organization_id == current_user.organization_id,
            Reservation.date >= today,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).order_by(Reservation.date, Reservation.start_time).limit(5).all()
        context['upcoming_reservations'] = upcoming
    elif current_user.role == 'org_member' and current_user.organization_id:
        upcoming = Reservation.query.filter(
            Reservation.organization_id == current_user.organization_id,
            Reservation.date >= today,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).order_by(Reservation.date, Reservation.start_time).limit(5).all()
        context['upcoming_reservations'] = upcoming
    elif current_user.is_school:
        from app.models.school import School
        from app.models.facility import Facility
        school = School.query.first()
        if school:
            today_reservations = Reservation.query.join(Reservation.facility).filter(
                Facility.school_id == school.id,
                Reservation.date == today,
                Reservation.status == Reservation.STATUS_CONFIRMED,
            ).all()
            context['today_reservations_list'] = today_reservations

    return render_template('dashboard/index.html', **context)
