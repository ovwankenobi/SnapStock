import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPkMixin, UpdatedAtMixin


class UnitType(str, enum.Enum):
    PIECE = "piece"
    BUNDLE = "bundle"
    # Sold by a seller-configured measurement (kg, yd, m, ...). Stock, thresholds and
    # quantities are stored in thousandths of that unit; price_cents is per whole unit.
    MEASURE = "measure"


class Product(UUIDPkMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "products"

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    # What one selling unit costs the seller (same unit as price_cents). Null = not recorded yet.
    cost_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_type: Mapped[UnitType] = mapped_column(Enum(UnitType, name="unit_type"), nullable=False)
    unit_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    pieces_per_unit: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False
    )
    stock_pieces: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer, default=10, server_default="10", nullable=False
    )
    category: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
