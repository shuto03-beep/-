from datetime import date, datetime, timedelta

from flask import Blueprint, abort, render_template, request
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.coach import Coach
from app.models.reservation import Reservation

coach_portal_bp = Blueprint('coach_portal', __name__)


def _current_coach():
    """Return the Coach linked to the logged-in user, or abort."""
    if not current_user.is_authenticated:
        abort(403)
    coach = Coach.query.filter_by(user_id=current_user.id).first()
    if not coach:
        abort(403)
    return coach


def _parse_iso(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


@coach_portal_bp.route('/my/dashboard')
@login_required
def dashboard():
    coach = _current_coach()
    today = date.today()
    week_end = today + timedelta(days=13)

    org_ids = [o.id for o in coach.organizations]

    upcoming = []
    if org_ids:
        upcoming = (
            Reservation.query
            .options(joinedload(Reservation.facility), joinedload(Reservation.organization))
            .filter(
                Reservation.organization_id.in_(org_ids),
                Reservation.date >= today,
                Reservation.date <= week_end,
                Reservation.status == Reservation.STATUS_CONFIRMED,
            )
            .order_by(Reservation.date, Reservation.start_time)
            .all()
        )

    return render_template(
        'coach_portal/dashboard.html',
        coach=coach,
        upcoming=upcoming,
    )


@coach_portal_bp.route('/my/compensation')
@login_required
def compensation():
    coach = _current_coach()
    today = date.today()
    default_from = today.replace(day=1)
    date_from = _parse_iso(request.args.get('from'), default_from)
    date_to = _parse_iso(request.args.get('to'), today)

    org_ids = [o.id for o in coach.organizations]
    rows = []
    if org_ids:
        rows = (
            db.session.query(Reservation.organization_id, Reservation.start_time, Reservation.end_time)
            .filter(
                Reservation.organization_id.in_(org_ids),
                Reservation.date >= date_from,
                Reservation.date <= date_to,
                Reservation.status == Reservation.STATUS_CONFIRMED,
            )
            .all()
        )

    minutes_by_org = {}
    for org_id, s, e in rows:
        m = int((datetime.combine(date.min, e) - datetime.combine(date.min, s)).total_seconds() // 60)
        if m > 0:
            minutes_by_org[org_id] = minutes_by_org.get(org_id, 0) + m

    breakdown = []
    total_amount = 0
    total_minutes = 0
    for org in coach.organizations:
        minutes = minutes_by_org.get(org.id, 0)
        hours = minutes / 60
        amount = int(round(hours * (coach.hourly_rate or 0)))
        total_amount += amount
        total_minutes += minutes
        breakdown.append({
            'org': org, 'minutes': minutes, 'hours': hours, 'amount': amount,
        })

    return render_template(
        'coach_portal/compensation.html',
        coach=coach,
        breakdown=breakdown,
        total_amount=total_amount,
        total_minutes=total_minutes,
        total_hours=round(total_minutes / 60, 2),
        date_from=date_from,
        date_to=date_to,
    )
