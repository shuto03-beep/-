from datetime import date, timedelta

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.facility import Facility
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.reservation import Reservation
from app.models.school import School
from app.models.school_block import SchoolBlock
from app.services.notification_service import get_unread_count

dashboard_bp = Blueprint('dashboard', __name__)


def _week_bounds(today):
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


@dashboard_bp.route('/')
@login_required
def root():
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/dashboard')
@login_required
def index():
    today = date.today()
    context = {
        'unread_count': get_unread_count(current_user.id),
    }

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
        school = School.query.first()
        if school:
            week_start, week_end = _week_bounds(today)

            today_list = (
                Reservation.query
                .options(joinedload(Reservation.facility), joinedload(Reservation.organization))
                .join(Reservation.facility)
                .filter(
                    Facility.school_id == school.id,
                    Reservation.date == today,
                    Reservation.status == Reservation.STATUS_CONFIRMED,
                )
                .order_by(Reservation.start_time)
                .all()
            )

            week_count = (
                db.session.query(func.count(Reservation.id))
                .join(Reservation.facility)
                .filter(
                    Facility.school_id == school.id,
                    Reservation.date >= week_start,
                    Reservation.date <= week_end,
                    Reservation.status == Reservation.STATUS_CONFIRMED,
                )
                .scalar() or 0
            )

            week_blocks = (
                SchoolBlock.query
                .filter(
                    SchoolBlock.school_id == school.id,
                    SchoolBlock.date >= week_start,
                    SchoolBlock.date <= week_end,
                )
                .order_by(SchoolBlock.date, SchoolBlock.start_time)
                .all()
            )

            upcoming_week_reservations = (
                Reservation.query
                .options(joinedload(Reservation.facility), joinedload(Reservation.organization))
                .join(Reservation.facility)
                .filter(
                    Facility.school_id == school.id,
                    Reservation.date >= today,
                    Reservation.date <= today + timedelta(days=6),
                    Reservation.status == Reservation.STATUS_CONFIRMED,
                )
                .order_by(Reservation.date, Reservation.start_time)
                .all()
            )

            context.update({
                'school': school,
                'week_start': week_start,
                'week_end': week_end,
                'today_reservations_list': today_list,
                'week_count': week_count,
                'week_blocks': week_blocks,
                'week_block_count': len(week_blocks),
                'upcoming_week_reservations': upcoming_week_reservations,
            })

    return render_template('dashboard/index.html', **context)
