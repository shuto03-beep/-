from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from app.extensions import db
from app.models.reservation import Reservation
from app.models.organization import Organization
from app.models.facility import Facility
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
    context = {'today': today}

    if current_user.is_admin:
        pending_orgs = Organization.query.filter_by(is_approved=False).count()
        today_reservations = Reservation.query.filter(
            Reservation.date == today,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).count()

        # Monthly reservations count
        first_of_month = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        monthly_reservations = Reservation.query.filter(
            Reservation.date >= first_of_month,
            Reservation.date < next_month,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).count()

        # This week's reservations (next 7 days)
        week_end = today + timedelta(days=7)
        this_week_reservations = Reservation.query.options(
            joinedload(Reservation.facility),
            joinedload(Reservation.organization),
        ).filter(
            Reservation.date >= today,
            Reservation.date < week_end,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).order_by(Reservation.date, Reservation.start_time).all()

        # Facility usage for current month (top 6)
        facility_usage_query = db.session.query(
            Facility.name,
            func.count(Reservation.id).label('count')
        ).join(Reservation, Reservation.facility_id == Facility.id).filter(
            Reservation.date >= first_of_month,
            Reservation.date < next_month,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).group_by(Facility.id, Facility.name).order_by(
            func.count(Reservation.id).desc()
        ).limit(6).all()

        facility_usage = [
            {'name': name, 'count': count}
            for name, count in facility_usage_query
        ]

        context.update({
            'pending_orgs': pending_orgs,
            'today_reservations': today_reservations,
            'total_orgs': Organization.query.count(),
            'monthly_reservations': monthly_reservations,
            'this_week_reservations': this_week_reservations,
            'facility_usage': facility_usage,
        })
    elif current_user.is_org_leader and current_user.organization_id:
        upcoming = Reservation.query.options(
            joinedload(Reservation.facility),
        ).filter(
            Reservation.organization_id == current_user.organization_id,
            Reservation.date >= today,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).order_by(Reservation.date, Reservation.start_time).limit(5).all()
        context['upcoming_reservations'] = upcoming
    elif current_user.role == 'org_member' and current_user.organization_id:
        upcoming = Reservation.query.options(
            joinedload(Reservation.facility),
        ).filter(
            Reservation.organization_id == current_user.organization_id,
            Reservation.date >= today,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        ).order_by(Reservation.date, Reservation.start_time).limit(5).all()
        context['upcoming_reservations'] = upcoming
    elif current_user.is_school:
        from app.models.school import School
        school = School.query.first()
        if school:
            today_reservations = Reservation.query.join(Reservation.facility).filter(
                Facility.school_id == school.id,
                Reservation.date == today,
                Reservation.status == Reservation.STATUS_CONFIRMED,
            ).all()
            context['today_reservations_list'] = today_reservations

    return render_template('dashboard/index.html', **context)
