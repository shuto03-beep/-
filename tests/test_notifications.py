from app.extensions import db
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    create_bulk_notifications,
    create_notification,
    queue_notifications,
)


def _make_users(n):
    users = []
    for i in range(n):
        u = User(
            username=f'u{i}', email=f'u{i}@x.jp', display_name=f'User {i}',
            role=User.ROLE_ORG_MEMBER,
        )
        u.set_password('x')
        users.append(u)
    db.session.add_all(users)
    db.session.commit()
    return users


def test_create_single_notification(app):
    user = _make_users(1)[0]
    create_notification(user.id, 'T', 'M', link='/x')
    got = Notification.query.filter_by(user_id=user.id).one()
    assert got.title == 'T'
    assert got.message == 'M'
    assert got.link == '/x'
    assert got.is_read is False


def test_bulk_notifications_single_commit(app):
    users = _make_users(5)
    n = create_bulk_notifications([u.id for u in users], 'Bulk', 'Msg')
    assert n == 5
    assert Notification.query.count() == 5


def test_bulk_notifications_empty(app):
    assert create_bulk_notifications([], 'T', 'M') == 0
    assert Notification.query.count() == 0


def test_queue_notifications_requires_caller_commit(app):
    users = _make_users(3)
    records = [
        {'user_id': u.id, 'title': f't{i}', 'message': f'm{i}', 'link': '/x'}
        for i, u in enumerate(users)
    ]
    assert queue_notifications(records) == 3
    db.session.commit()
    titles = sorted(n.title for n in Notification.query.all())
    assert titles == ['t0', 't1', 't2']


def test_queue_notifications_empty(app):
    assert queue_notifications([]) == 0
