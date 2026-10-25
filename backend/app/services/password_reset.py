import hmac
import uuid
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import (
    create_password_reset_token,
    decode_password_reset_token,
    hash_password,
    password_fingerprint,
)
from app.models.user import User


class InvalidResetTokenError(Exception):
    pass


_EMAIL_TEXT = {
    "en": (
        "Reset your SnapStock password",
        "Hi {name},\n\n"
        "We received a request to reset the password for your SnapStock account.\n"
        "Open this link to choose a new password:\n\n"
        "{link}\n\n"
        "The link expires in {minutes} minutes and can only be used once.\n"
        "If you didn't ask for this, you can ignore this email; your password won't change.\n\n"
        "SnapStock",
    ),
    "tl": (
        "I-reset ang iyong SnapStock password",
        "Hi {name},\n\n"
        "May humiling na i-reset ang password ng iyong SnapStock account.\n"
        "Buksan ang link na ito para pumili ng bagong password:\n\n"
        "{link}\n\n"
        "Mag-e-expire ang link sa loob ng {minutes} minuto at isang beses lang magagamit.\n"
        "Kung hindi ikaw ang humiling nito, balewalain lang ang email na ito; hindi magbabago ang password mo.\n\n"
        "SnapStock",
    ),
}


def find_user_for_reset(db: Session, email: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        return None
    return user


def build_reset_email(user: User) -> tuple[str, str, str]:
    """Returns (to, subject, body) for the user's password reset email."""
    token = create_password_reset_token(str(user.id), user.hashed_password)
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={quote(token)}"
    subject, body = _EMAIL_TEXT.get(user.preferred_language, _EMAIL_TEXT["en"])
    return (
        user.email,
        subject,
        body.format(name=user.full_name, link=link, minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
    )


def reset_password(db: Session, token: str, new_password: str) -> User:
    try:
        user_id, fingerprint = decode_password_reset_token(token)
        user = db.get(User, uuid.UUID(user_id))
    except ValueError as exc:
        raise InvalidResetTokenError("Reset link is invalid or has expired") from exc

    if (
        user is None
        or not user.is_active
        or not hmac.compare_digest(fingerprint, password_fingerprint(user.hashed_password))
    ):
        raise InvalidResetTokenError("Reset link is invalid or has expired")

    user.hashed_password = hash_password(new_password)
    db.commit()
    return user
