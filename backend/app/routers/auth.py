from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import BusinessType, SellerProfile, User, UserRole
from app.schemas.user import AuthResponse, RegisterRequest, UserRead, UserUpdate

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
