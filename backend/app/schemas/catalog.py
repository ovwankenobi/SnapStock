import uuid
from datetime import datetime

from pydantic import Field

from app.models.product import UnitType
from app.models.sale import PaymentMethod, SaleStatus, SaleType
from app.models.user import BusinessType
from app.schemas.base import CamelModel
from app.schemas.payout import PayoutAccountRead
from app.schemas.product import StockStatus
from app.schemas.sale import SaleRead


class CatalogProductRead(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    seller_name: str
    name: str
    description: str | None
    photo_url: str | None
    price_cents: int
    unit_type: UnitType
    unit_label: str | None = None
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
    payout_accounts: list[PayoutAccountRead] = []
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
    # Order single pieces of a bundle product instead of whole bundles.
    by_piece: bool = False


class BuyerReceiptItem(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    seller_name: str
    sale_type: SaleType
    total_cents: int
    status: SaleStatus
    payment_method: PaymentMethod
    receipt_code: str
    created_at: datetime
    item_count: int


class BuyerReceiptListResponse(CamelModel):
    items: list[BuyerReceiptItem]
    total: int
    page: int
    page_size: int


class BuyerOrderRead(SaleRead):
    """A buyer's own order, with where to send payment while it is still pending."""

    seller_name: str
    payout_accounts: list[PayoutAccountRead] = []
