from sqlalchemy.orm import Session

from app.core.security import QR_LOGIN_KEY_PREFIX, generate_qr_login_key, hash_qr_login_key
from app.models.mixins import utcnow
from app.models.user import User


class InvalidQrLoginError(Exception):
    pass


def issue_key(db: Session, user: User) -> str:
    """Creates (or replaces) the user's login QR key and returns it. The raw key is never stored,
    so this is the only time it can be shown."""
    key = generate_qr_login_key()
    user.qr_login_key_hash = hash_qr_login_key(key)
    user.qr_login_created_at = utcnow()
    db.commit()
    db.refresh(user)
    return key


def revoke_key(db: Session, user: User) -> None:
    user.qr_login_key_hash = None
    user.qr_login_created_at = None
    db.commit()


def authenticate(db: Session, key: str) -> User:
    if not key.startswith(QR_LOGIN_KEY_PREFIX):
        raise InvalidQrLoginError("Not a login QR")
    user = db.query(User).filter(User.qr_login_key_hash == hash_qr_login_key(key)).first()
    if user is None or not user.is_active:
        raise InvalidQrLoginError("Invalid or revoked login QR")
    return user
