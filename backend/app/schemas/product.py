import enum
import uuid
from datetime import datetime

from pydantic import Field, computed_field, field_validator, model_validator

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


def _clean_unit_label(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ProductCreate(CamelModel):
    name: str = Field(min_length=1)
    description: str | None = None
    price_cents: int = Field(gt=0)
    cost_cents: int | None = Field(default=None, ge=0)
    unit_type: UnitType
    unit_label: str | None = Field(default=None, max_length=16)
    pieces_per_unit: int = Field(default=1, ge=1)
    stock_pieces: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    category: str | None = None

    normalize_unit_label = field_validator("unit_label")(_clean_unit_label)

    @model_validator(mode="after")
    def check_unit_label(self) -> "ProductCreate":
        if self.unit_type == UnitType.MEASURE:
            if self.unit_label is None:
                raise ValueError("unit_label is required for measure products")
        else:
            self.unit_label = None
        return self


class ProductUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    price_cents: int | None = Field(default=None, gt=0)
    cost_cents: int | None = Field(default=None, ge=0)
    unit_type: UnitType | None = None
    unit_label: str | None = Field(default=None, max_length=16)
    pieces_per_unit: int | None = Field(default=None, ge=1)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    category: str | None = None

    normalize_unit_label = field_validator("unit_label")(_clean_unit_label)


class ProductRead(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    name: str
    description: str | None
    photo_url: str | None
    price_cents: int
    cost_cents: int | None = None
    unit_type: UnitType
    unit_label: str | None
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


class ProductImageSearchResultItem(CamelModel):
    product: ProductRead
    # Always null in stage 1, same as the catalog image search.
    confidence: float | None = None


class ProductImageSearchResponse(CamelModel):
    query: str
    results: list[ProductImageSearchResultItem]


class QuickSellRequest(CamelModel):
    quantity: int = Field(gt=0)
    payment_method: PaymentMethod
    # The price agreed during the sale; omitted = the product's current price.
    unit_price_cents: int | None = Field(default=None, ge=0)


class QuickSellResult(CamelModel):
    product: ProductRead
    sale_id: uuid.UUID
    receipt_code: str
    total_cents: int


class RestockRequest(CamelModel):
    quantity: int = Field(gt=0)
    note: str | None = None
    # New cost per selling unit for this delivery; omitted = keep the current cost.
    unit_cost_cents: int | None = Field(default=None, ge=0)


class BulkRestockItem(CamelModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_cost_cents: int | None = Field(default=None, ge=0)


class BulkRestockRequest(CamelModel):
    items: list[BulkRestockItem] = Field(min_length=1)
    note: str | None = None
