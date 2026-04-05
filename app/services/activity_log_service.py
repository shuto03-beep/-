import json
from app.extensions import db
from app.models.activity_log import ActivityLog


def log_activity(user_id, action, target_type=None, target_id=None, details=None):
    """操作ログを記録する"""
    if isinstance(details, dict):
        details = json.dumps(details, ensure_ascii=False)
    log = ActivityLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        details=details,
    )
    db.session.add(log)
    db.session.commit()
    return log
