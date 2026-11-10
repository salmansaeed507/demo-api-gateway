import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from .config import settings

logger = logging.getLogger(__name__)


def send_new_user_email(user_id: int, name: str) -> None:
    """Email the owner when a new user registers. Never raises."""
    if not settings.smtp_username or not settings.smtp_password:
        logger.debug("SMTP not configured; skipping new-user email")
        return

    recipient = settings.notify_email_to or settings.smtp_username
    msg = EmailMessage()
    msg["Subject"] = f"[{settings.service_name}] New user registered: {name}"
    msg["From"] = settings.smtp_username
    msg["To"] = recipient
    msg.set_content(
        f"A new user registered.\n\n"
        f"Name: {name}\n"
        f"User ID: {user_id}\n"
        f"Time (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n"
    )

    try:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=15
        ) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Sent new-user email for user_id=%s", user_id)
    except Exception:
        logger.exception("Failed to send new-user email for user_id=%s", user_id)
