from datetime import date, timedelta

from flask import Blueprint, abort, render_template
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from app.models.notification import Notification
from app.models.reservation import Reservation

parent_portal_bp = Blueprint('parent_portal', __name__)


def _current_child_org():
    if not current_user.is_authenticated:
        abort(403)
    if not current_user.is_parent:
        abort(403)
    if not current_user.child_organization_id:
        return None
    return current_user.child_organization


@parent_portal_bp.route('/family/dashboard')
@login_required
def dashboard():
    org = _current_child_org()
    if not org:
        return render_template('parent_portal/no_child_org.html')

    today = date.today()
    horizon = today + timedelta(days=13)

    upcoming = (
        Reservation.query
        .options(joinedload(Reservation.facility), joinedload(Reservation.organization))
        .filter(
            Reservation.organization_id == org.id,
            Reservation.date >= today,
            Reservation.date <= horizon,
            Reservation.status == Reservation.STATUS_CONFIRMED,
        )
        .order_by(Reservation.date, Reservation.start_time)
        .all()
    )

    recent_notifications = (
        Notification.query
        .filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'parent_portal/dashboard.html',
        org=org,
        upcoming=upcoming,
        recent_notifications=recent_notifications,
    )
