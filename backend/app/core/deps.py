import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise credentials_error from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error

    try:
        user = db.get(User, uuid.UUID(user_id))
    except ValueError as exc:
        raise credentials_error from exc

    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_seller(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.SELLER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sellers only")
    return user


def require_buyer(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.BUYER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Buyers only")
    return user
