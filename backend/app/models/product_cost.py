import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPkMixin


class CostSource(str, enum.Enum):
    MANUAL = "manual"
    RESTOCK = "restock"


class ProductCostHistory(UUIDPkMixin, CreatedAtMixin, Base):
    """Append-only log of a product's unit cost; a row is written whenever the cost changes."""

    __tablename__ = "product_cost_history"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), index=True, nullable=False
    )
    cost_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[CostSource] = mapped_column(Enum(CostSource, name="cost_source"), nullable=False)
