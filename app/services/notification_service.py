from app.extensions import db
from app.models.notification import Notification


def create_notification(user_id, title, message, link=None):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def create_bulk_notifications(user_ids, title, message, link=None):
    """Create the same notification for many users in a single commit."""
    user_ids = list(user_ids)
    if not user_ids:
        return 0
    notifications = [
        Notification(user_id=uid, title=title, message=message, link=link)
        for uid in user_ids
    ]
    db.session.add_all(notifications)
    db.session.commit()
    return len(notifications)


def queue_notifications(records):
    """Stage per-user notifications in the current session without committing.

    Use when notifications must share a transaction with other DB changes.
    Caller is responsible for db.session.commit().

    records: iterable of dicts with keys: user_id, title, message, link (optional).
    """
    records = list(records)
    if not records:
        return 0
    notifications = [
        Notification(
            user_id=r['user_id'],
            title=r['title'],
            message=r['message'],
            link=r.get('link'),
        )
        for r in records
    ]
    db.session.add_all(notifications)
    return len(notifications)


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_as_read(notification_id, user_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notification:
        notification.is_read = True
        db.session.commit()
    return notification
