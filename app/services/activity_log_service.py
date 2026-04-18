from flask_login import current_user

from app.extensions import db
from app.models.activity_log import ActivityLog


def log_activity(action, target_type=None, target_id=None, details=None, user=None):
    """Record an audit-trail entry. Adds to session without committing.

    Caller is responsible for db.session.commit(). Keeps logging in the same
    transaction as the action being logged.
    """
    actor = user if user is not None else (current_user if current_user.is_authenticated else None)
    log = ActivityLog(
        user_id=actor.id if actor else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.session.add(log)
    return log
