from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import BusinessType, SellerProfile, User, UserRole
from app.schemas.user import (
    AuthResponse,
    ForgotPasswordRequest,
    QrLoginKeyCreate,
    QrLoginKeyRead,
    QrLoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserRead,
    UserUpdate,
)
from app.services import email as email_service
from app.services import password_reset, qr_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_REGISTER_RATE_LIMIT)
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole(payload.role),
        phone=payload.phone,
    )
    db.add(user)
    db.flush()

    if payload.role == "seller":
        db.add(
            SellerProfile(
                user_id=user.id,
                business_name=payload.business_name,
                business_type=BusinessType(payload.business_type),
                address=payload.address,
                description=payload.description,
            )
        )

    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return AuthResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
@limiter.limit(settings.AUTH_LOGIN_RATE_LIMIT)
def login(
    request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return AuthResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/qr-login", response_model=AuthResponse)
@limiter.limit(settings.AUTH_QR_LOGIN_RATE_LIMIT)
def login_with_qr(request: Request, payload: QrLoginRequest, db: Session = Depends(get_db)):
    try:
        user = qr_login.authenticate(db, payload.key)
    except qr_login.InvalidQrLoginError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return AuthResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/qr-login-key", response_model=QrLoginKeyRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.AUTH_LOGIN_RATE_LIMIT)
def create_qr_login_key(
    request: Request,
    payload: QrLoginKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # A login QR works like a saved password, so making one asks for the password again: someone
    # holding an unlocked phone can't mint a permanent login. Making a new one replaces the old one.
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password")
    key = qr_login.issue_key(db, current_user)
    return QrLoginKeyRead(key=key, created_at=current_user.qr_login_created_at)


@router.delete("/qr-login-key", status_code=status.HTTP_204_NO_CONTENT)
def revoke_qr_login_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    qr_login.revoke_key(db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.AUTH_FORGOT_PASSWORD_RATE_LIMIT)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Same response whether or not the email is registered, and the email goes out after the
    # response, so neither the body nor the timing reveals which emails have accounts.
    user = password_reset.find_user_for_reset(db, payload.email)
    if user is not None:
        to, subject, body = password_reset.build_reset_email(user)
        background_tasks.add_task(email_service.send_email, to, subject, body)
    return {"detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.AUTH_RESET_PASSWORD_RATE_LIMIT)
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        password_reset.reset_password(db, payload.token, payload.new_password)
    except password_reset.InvalidResetTokenError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.AUTH_CHANGE_PASSWORD_RATE_LIMIT)
def request_password_change(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    # Signed-in users change their password the same way as a forgotten one: a link is emailed
    # to their account address and the new password is set on the reset page.
    to, subject, body = password_reset.build_reset_email(current_user)
    background_tasks.add_task(email_service.send_email, to, subject, body)
    return {"detail": "A link to change your password has been sent to your email."}


@router.get("/me", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updates = payload.model_dump(exclude_unset=True)

    for field in ("full_name", "phone", "preferred_language"):
        if field in updates:
            setattr(current_user, field, updates[field])

    profile_fields = {"business_name", "business_type", "address", "description", "photo_url"}
    profile_updates = {k: v for k, v in updates.items() if k in profile_fields}
    if profile_updates and current_user.seller_profile is not None:
        for field, value in profile_updates.items():
            if field == "business_type" and value is not None:
                value = BusinessType(value)
            setattr(current_user.seller_profile, field, value)

    db.commit()
    db.refresh(current_user)
    return UserRead.model_validate(current_user)
