import uuid
from datetime import datetime

from pydantic import Field

from app.models.product import UnitType
from app.models.sale import PaymentMethod, SaleType
from app.models.user import BusinessType
from app.schemas.base import CamelModel
from app.schemas.product import StockStatus


class CatalogProductRead(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    seller_name: str
    name: str
    description: str | None
    photo_url: str | None
    price_cents: int
    unit_type: UnitType
    pieces_per_unit: int
    category: str | None
    stock_status: StockStatus


class CatalogProductListResponse(CamelModel):
    items: list[CatalogProductRead]
    total: int
    page: int
    page_size: int


class CatalogSellerRead(CamelModel):
    id: uuid.UUID
    business_name: str
    business_type: BusinessType
    address: str | None
    description: str | None
    photo_url: str | None
    products: list[CatalogProductRead]


class ImageSearchResultItem(CamelModel):
    product: CatalogProductRead
    # Always null in stage 1 (keyword matching has no meaningful confidence score).
    # Populated once stage 2 (real vision search) replaces the matching logic.
    confidence: float | None = None


class ImageSearchResponse(CamelModel):
    query: str
    results: list[ImageSearchResultItem]


class BuyRequest(CamelModel):
    quantity: int = Field(gt=0)
    payment_method: PaymentMethod


class BuyerReceiptItem(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    seller_name: str
    sale_type: SaleType
    total_cents: int
    payment_method: PaymentMethod
    receipt_code: str
    created_at: datetime
    item_count: int


class BuyerReceiptListResponse(CamelModel):
    items: list[BuyerReceiptItem]
    total: int
    page: int
    page_size: int
