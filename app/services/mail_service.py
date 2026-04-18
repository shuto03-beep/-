from flask import current_app
from flask_mail import Message

from app.extensions import mail


def send_notification_email(recipient_email, subject, message, link=None):
    """Send a notification email. Returns True if sent, False if skipped or failed.

    If MAIL_SERVER is not configured, logs and returns False without raising
    so that in-app notification creation is never blocked by mail outages.
    """
    if not recipient_email:
        return False
    if not current_app.config.get('MAIL_SERVER'):
        current_app.logger.info('[MAIL-SKIP] %s: %s', recipient_email, subject)
        return False

    body = message
    if link:
        body = f'{message}\n\nリンク: {link}'

    msg = Message(subject=subject, recipients=[recipient_email], body=body)
    try:
        mail.send(msg)
        return True
    except Exception:
        current_app.logger.exception('Failed to send email to %s', recipient_email)
        return False


def send_notification_emails(user_emails, subject, message, link=None):
    """Send the same notification to many recipients. Errors are logged per-user."""
    sent = 0
    for email in user_emails:
        if send_notification_email(email, subject, message, link):
            sent += 1
    return sent
