import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email over SMTP. Without SMTP_HOST (local dev), log it instead."""
    if not settings.SMTP_HOST:
        logger.warning("SMTP_HOST is not set; email not sent.\nTo: %s\nSubject: %s\n\n%s", to, subject, body)
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USERNAME
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError):
        # Runs as a background task after the response is sent, so log rather than raise.
        logger.exception("Failed to send email to %s", to)
