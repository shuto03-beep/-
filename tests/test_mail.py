from app.extensions import db, mail
from app.models.notification import Notification
from app.models.user import User
from app.services.mail_service import send_notification_email
from app.services.notification_service import (
    create_bulk_notifications,
    create_notification,
    queue_notifications,
    send_queued_emails,
)


def _make_users(n, with_email=True):
    users = []
    for i in range(n):
        u = User(
            username=f'm{i}',
            email=f'm{i}@x.jp' if with_email else None,
            display_name=f'M{i}',
            role=User.ROLE_ORG_MEMBER,
        )
        u.set_password('x')
        users.append(u)
    db.session.add_all(users)
    db.session.commit()
    return users


def test_send_notification_email_success(app):
    with mail.record_messages() as outbox:
        ok = send_notification_email('target@x.jp', 'Hi', 'Body', link='/x')
    assert ok is True
    assert len(outbox) == 1
    msg = outbox[0]
    assert msg.subject == 'Hi'
    assert 'target@x.jp' in msg.recipients
    assert 'リンク: /x' in msg.body


def test_send_notification_email_no_recipient(app):
    assert send_notification_email('', 'Hi', 'Body') is False


def test_send_notification_email_skipped_when_mail_server_unset(app):
    app.config['MAIL_SERVER'] = None
    with mail.record_messages() as outbox:
        ok = send_notification_email('target@x.jp', 'Hi', 'Body')
    assert ok is False
    assert len(outbox) == 0


def test_create_notification_sends_email(app):
    user = _make_users(1)[0]
    with mail.record_messages() as outbox:
        create_notification(user.id, 'Approved', 'Your org is approved')
    assert Notification.query.count() == 1
    assert len(outbox) == 1
    assert user.email in outbox[0].recipients


def test_create_bulk_notifications_sends_email_each(app):
    users = _make_users(3)
    with mail.record_messages() as outbox:
        create_bulk_notifications([u.id for u in users], 'Hi', 'Body')
    assert len(outbox) == 3
    recipients = {r for msg in outbox for r in msg.recipients}
    assert recipients == {u.email for u in users}


def test_bulk_notifications_skips_inactive_users(app):
    users = _make_users(2)
    inactive = User(
        username='inactive', email='inactive@x.jp', display_name='Inactive',
        role=User.ROLE_ORG_MEMBER, is_active=False,
    )
    inactive.set_password('x')
    db.session.add(inactive)
    db.session.commit()
    ids = [u.id for u in users] + [inactive.id]
    with mail.record_messages() as outbox:
        create_bulk_notifications(ids, 'Hi', 'Body')
    assert Notification.query.count() == 3
    assert len(outbox) == 2  # inactive skipped


def test_send_email_disabled_flag(app):
    user = _make_users(1)[0]
    with mail.record_messages() as outbox:
        create_notification(user.id, 'No Email', 'Body', send_email=False)
    assert Notification.query.count() == 1
    assert len(outbox) == 0


def test_send_queued_emails(app):
    users = _make_users(2)
    records = [
        {'user_id': u.id, 'title': f'T{u.id}', 'message': f'M{u.id}', 'link': '/x'}
        for u in users
    ]
    queue_notifications(records)
    db.session.commit()
    with mail.record_messages() as outbox:
        sent = send_queued_emails(records)
    assert sent == 2
    assert len(outbox) == 2
