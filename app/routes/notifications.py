from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.notification import Notification
from app.services.notification_service import mark_as_read

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/notifications')
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()
    return render_template('notifications/list.html', notifications=notifications)


@notifications_bp.route('/notifications/<int:id>/read', methods=['POST'])
@login_required
def read_notification(id):
    notification = mark_as_read(id, current_user.id)
    if notification and notification.link:
        return redirect(notification.link)
    return redirect(url_for('notifications.list_notifications'))
