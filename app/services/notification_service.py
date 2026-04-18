from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.services.mail_service import send_notification_email


def _emails_for(user_ids):
    if not user_ids:
        return []
    return [
        email for (email,) in db.session.query(User.email)
        .filter(User.id.in_(user_ids), User.email.isnot(None), User.is_active.is_(True))
        .all()
        if email
    ]


def create_notification(user_id, title, message, link=None, send_email=True):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
    )
    db.session.add(notification)
    db.session.commit()
    if send_email:
        user = db.session.get(User, user_id)
        if user and user.email and user.is_active:
            send_notification_email(user.email, title, message, link)
    return notification


def create_bulk_notifications(user_ids, title, message, link=None, send_email=True):
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
    if send_email:
        for email in _emails_for(user_ids):
            send_notification_email(email, title, message, link)
    return len(notifications)


def queue_notifications(records):
    """Stage per-user notifications in the current session without committing.

    Use when notifications must share a transaction with other DB changes.
    Caller is responsible for db.session.commit(). Emails are NOT sent here
    because content differs per record and send must happen post-commit;
    call send_queued_emails(records) after commit if email is desired.

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


def send_queued_emails(records):
    """Send emails for records previously queued via queue_notifications.

    Call after db.session.commit(). Silently skips users without email addresses.
    """
    records = list(records)
    if not records:
        return 0
    user_ids = [r['user_id'] for r in records]
    emails_by_id = dict(
        db.session.query(User.id, User.email)
        .filter(User.id.in_(user_ids), User.email.isnot(None), User.is_active.is_(True))
        .all()
    )
    sent = 0
    for r in records:
        email = emails_by_id.get(r['user_id'])
        if not email:
            continue
        if send_notification_email(email, r['title'], r['message'], r.get('link')):
            sent += 1
    return sent


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_as_read(notification_id, user_id):
    notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notification:
        notification.is_read = True
        db.session.commit()
    return notification
