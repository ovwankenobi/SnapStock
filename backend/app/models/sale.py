import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPkMixin
from app.models.product import UnitType


class SaleType(str, enum.Enum):
    ITEMIZED = "itemized"
    WALK_IN = "walk_in"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    GCASH = "gcash"
    MAYA = "maya"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class Sale(UUIDPkMixin, CreatedAtMixin, Base):
    __tablename__ = "sales"

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True
    )
    sale_type: Mapped[SaleType] = mapped_column(Enum(SaleType, name="sale_type"), nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    receipt_code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan", passive_deletes=True
    )


class SaleItem(UUIDPkMixin, Base):
    __tablename__ = "sale_items"

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )
    product_name_snapshot: Mapped[str] = mapped_column(String, nullable=False)
    unit_price_cents_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_type_snapshot: Mapped[UnitType] = mapped_column(
        Enum(UnitType, name="unit_type"), nullable=False
    )
    pieces_deducted: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    sale: Mapped["Sale"] = relationship(back_populates="items")
