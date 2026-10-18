import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPkMixin


class StockMovementReason(str, enum.Enum):
    SALE = "sale"
    QUICK_SELL = "quick_sell"
    RESTOCK = "restock"
    CORRECTION = "correction"
    INITIAL = "initial"
    VOID = "void"
    REFUND = "refund"
    CANCEL = "cancel"


class StockMovement(UUIDPkMixin, CreatedAtMixin, Base):
    __tablename__ = "stock_movements"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True, nullable=False
    )
    change_pieces: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[StockMovementReason] = mapped_column(
        Enum(StockMovementReason, name="stock_movement_reason"), nullable=False
    )
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sales.id"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
