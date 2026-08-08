import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.models.product import UnitType
from app.models.sale import PaymentMethod, SaleType
from app.schemas.base import CamelModel


class SaleItemCreate(CamelModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)


class SaleCreate(CamelModel):
    sale_type: SaleType
    buyer_id: uuid.UUID | None = None
    payment_method: PaymentMethod
    items: list[SaleItemCreate] = Field(default_factory=list)
    note: str | None = None
    # Only used for a walk-in aggregate sale with no line items (a lump-sum amount).
    total_cents: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_consistency(self) -> "SaleCreate":
        if self.sale_type == SaleType.ITEMIZED:
            if self.buyer_id is None:
                raise ValueError("buyer_id is required for itemized sales")
            if not self.items:
                raise ValueError("items are required for itemized sales")
        if self.sale_type == SaleType.WALK_IN and self.buyer_id is not None:
            raise ValueError("walk_in sales cannot have a buyer_id")
        if not self.items and self.total_cents is None:
            raise ValueError("either items or total_cents must be provided")
        if self.items and self.total_cents is not None:
            raise ValueError("provide either items or total_cents, not both")
        return self


class SaleItemRead(CamelModel):
    id: uuid.UUID
    product_id: uuid.UUID | None
    product_name_snapshot: str
    unit_price_cents_snapshot: int
    quantity: int
    unit_type_snapshot: UnitType
    pieces_deducted: int
    line_total_cents: int


class SaleRead(CamelModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    buyer_id: uuid.UUID | None
    buyer_name: str | None = None
    sale_type: SaleType
    total_cents: int
    payment_method: PaymentMethod
    receipt_code: str
    note: str | None
    created_at: datetime
    items: list[SaleItemRead] = Field(default_factory=list)


class SaleListItem(CamelModel):
    id: uuid.UUID
    buyer_id: uuid.UUID | None
    buyer_name: str | None = None
    sale_type: SaleType
    total_cents: int
    payment_method: PaymentMethod
    receipt_code: str
    note: str | None
    created_at: datetime
    item_count: int


class SaleListResponse(CamelModel):
    items: list[SaleListItem]
    total: int
    page: int
    page_size: int


class BuyerSearchResult(CamelModel):
    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None


class PublicReceiptItem(CamelModel):
    name: str
    quantity: int
    unit_type: UnitType
    unit_price_cents: int
    line_total_cents: int


class PublicReceipt(CamelModel):
    business_name: str
    receipt_code: str
    sale_type: SaleType
    items: list[PublicReceiptItem]
    total_cents: int
    payment_method: PaymentMethod
    created_at: datetime
