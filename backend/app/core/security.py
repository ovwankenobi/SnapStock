import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


PASSWORD_RESET_PURPOSE = "password_reset"


def password_fingerprint(hashed_password: str) -> str:
    # Ties a reset token to the current password hash, so the token stops working once the
    # password changes (each reset link is single-use without storing tokens).
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def create_password_reset_token(
    user_id: str, hashed_password: str, expires_minutes: int | None = None
) -> str:
    minutes = settings.PASSWORD_RESET_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {
        "sub": user_id,
        "purpose": PASSWORD_RESET_PURPOSE,
        "pwd": password_fingerprint(hashed_password),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_password_reset_token(token: str) -> tuple[str, str]:
    """Returns (user_id, password_fingerprint). Raises ValueError for anything but a valid reset token."""
    payload = decode_access_token(token)
    if payload.get("purpose") != PASSWORD_RESET_PURPOSE or not payload.get("sub") or not payload.get("pwd"):
        raise ValueError("Not a password reset token")
    return payload["sub"], payload["pwd"]


QR_LOGIN_KEY_PREFIX = "ssqr1_"


def generate_qr_login_key() -> str:
    # The prefix lets the login scanner tell a login QR apart from other QR codes (e.g. receipts).
    return QR_LOGIN_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_qr_login_key(key: str) -> str:
    # The key is 256 random bits, so a fast hash is enough and lets us look it up by index.
    return hashlib.sha256(key.encode()).hexdigest()
