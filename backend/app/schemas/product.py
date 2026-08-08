import enum
import uuid
from datetime import datetime

from pydantic import Field, computed_field

from app.models.product import UnitType
from app.models.sale import PaymentMethod
from app.schemas.base import CamelModel


class StockStatus(str, enum.Enum):
    OUT = "out"
    LOW = "low"
    IN_STOCK = "in_stock"


def compute_stock_status(stock_pieces: int, low_stock_threshold: int) -> StockStatus:
    if stock_pieces <= 0:
        return StockStatus.OUT
    if stock_pieces <= low_stock_threshold:
        return StockStatus.LOW
    return StockStatus.IN_STOCK


class ProductCreate(CamelModel):
    name: str = Field(min_length=1)
    description: str | None = None
    price_cents: int = Field(gt=0)
    unit_type: UnitType
    pieces_per_unit: int = Field(default=1, ge=1)
    stock_pieces: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    category: str | None = None


class ProductUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    price_cents: int | None = Field(default=None, gt=0)
    unit_type: UnitType | None = None
    pieces_per_unit: int | None = Field(default=None, ge=1)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    category: str | None = None


class ProductRead(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    name: str
    description: str | None
    photo_url: str | None
    price_cents: int
    unit_type: UnitType
    pieces_per_unit: int
    stock_pieces: int
    low_stock_threshold: int
    category: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def stock_status(self) -> StockStatus:
        return compute_stock_status(self.stock_pieces, self.low_stock_threshold)


class ProductListResponse(CamelModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int


class QuickSellRequest(CamelModel):
    quantity: int = Field(gt=0)
    payment_method: PaymentMethod


class QuickSellResult(CamelModel):
    product: ProductRead
    sale_id: uuid.UUID
    receipt_code: str
    total_cents: int


class RestockRequest(CamelModel):
    quantity: int = Field(gt=0)
    note: str | None = None
