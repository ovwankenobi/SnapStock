import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, model_validator

from app.schemas.base import CamelModel
from app.schemas.payout import PayoutAccountRead

Role = Literal["seller", "buyer"]
BusinessType = Literal["wholesale", "retail", "both"]


class SellerProfileRead(CamelModel):
    business_name: str
    business_type: BusinessType
    address: str | None = None
    description: str | None = None
    photo_url: str | None = None
    payout_accounts: list[PayoutAccountRead] = []


class UserRead(CamelModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    phone: str | None = None
    preferred_language: str
    created_at: datetime
    qr_login_created_at: datetime | None = None
    seller_profile: SellerProfileRead | None = None


class RegisterRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: Role
    phone: str | None = None
    business_name: str | None = None
    business_type: BusinessType | None = None
    address: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def check_seller_business_fields(self) -> "RegisterRequest":
        if self.role == "seller" and (not self.business_name or not self.business_type):
            raise ValueError("business_name and business_type are required for sellers")
        return self


class ForgotPasswordRequest(CamelModel):
    email: EmailStr


class ResetPasswordRequest(CamelModel):
    token: str
    new_password: str = Field(min_length=8)


class QrLoginKeyCreate(CamelModel):
    current_password: str


class QrLoginKeyRead(CamelModel):
    key: str
    created_at: datetime


class QrLoginRequest(CamelModel):
    key: str


class AuthResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class UserUpdate(CamelModel):
    full_name: str | None = None
    phone: str | None = None
    preferred_language: str | None = None
    business_name: str | None = None
    business_type: BusinessType | None = None
    address: str | None = None
    description: str | None = None
    photo_url: str | None = None
