import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPkMixin, UpdatedAtMixin


class UserRole(str, enum.Enum):
    SELLER = "seller"
    BUYER = "buyer"


class BusinessType(str, enum.Enum):
    WHOLESALE = "wholesale"
    RETAIL = "retail"
    BOTH = "both"


class User(UUIDPkMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    preferred_language: Mapped[str] = mapped_column(
        String, default="en", server_default="en", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    seller_profile: Mapped["SellerProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class SellerProfile(UUIDPkMixin, Base):
    __tablename__ = "seller_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
    )
    business_name: Mapped[str] = mapped_column(String, nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        Enum(BusinessType, name="business_type"), nullable=False
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="seller_profile")
