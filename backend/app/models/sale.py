import enum
import uuid

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
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


class SaleStatus(str, enum.Enum):
    COMPLETED = "completed"
    # Entered by mistake: excluded from every metric.
    VOIDED = "voided"
    # A real sale whose goods came back: counts in gross sales, subtracted as refunds.
    REFUNDED = "refunded"
    # A buyer's order whose payment the seller has not confirmed yet: stock is
    # reserved but the sale is excluded from every metric until confirmed.
    PENDING_PAYMENT = "pending_payment"
    # An order the seller rejected or the buyer cancelled before payment was
    # confirmed: its stock came back and it is excluded from every metric.
    CANCELLED = "cancelled"


def _default_from(column: str):
    return lambda context: context.get_current_parameters()[column]


class Sale(UUIDPkMixin, CreatedAtMixin, Base):
    __tablename__ = "sales"

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    buyer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=True
    )
    sale_type: Mapped[SaleType] = mapped_column(Enum(SaleType, name="sale_type"), nullable=False)
    # subtotal_cents = sum of line totals at the charged prices; total_cents = subtotal - discount.
    subtotal_cents: Mapped[int] = mapped_column(
        Integer, default=_default_from("total_cents"), nullable=False
    )
    discount_cents: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SaleStatus] = mapped_column(
        Enum(SaleStatus, name="sale_status"),
        default=SaleStatus.COMPLETED,
        server_default=SaleStatus.COMPLETED.name,
        index=True,
        nullable=False,
    )
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Storage key of the buyer's payment screenshot (private; see services/uploads.private_url).
    payment_proof_url: Mapped[str | None] = mapped_column(String, nullable=True)
    proof_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    # The product's price when sold; unit_price_cents_snapshot is what the seller actually charged.
    list_price_cents_snapshot: Mapped[int] = mapped_column(
        Integer, default=_default_from("unit_price_cents_snapshot"), nullable=False
    )
    unit_price_cents_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cost at the time of sale, so later cost edits never rewrite past profit. Null = cost unknown.
    unit_cost_cents_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_total_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_type_snapshot: Mapped[UnitType] = mapped_column(
        Enum(UnitType, name="unit_type"), nullable=False
    )
    unit_label_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pieces_deducted: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    sale: Mapped["Sale"] = relationship(back_populates="items")
