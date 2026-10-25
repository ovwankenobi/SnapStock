import random
import string
import uuid
from datetime import datetime

from fastapi import UploadFile
from sqlalchemy.orm import Session, selectinload

from app.core.business_time import RANGE_DAYS, now_utc, resolve_range
from app.models.product import Product
from app.models.sale import PaymentMethod, Sale, SaleStatus, SaleType
from app.models.stock_movement import StockMovementReason
from app.models.user import User, UserRole
from app.services import uploads as uploads_service
from app.services.inventory import apply_stock_change, build_sale_item

# Excludes 0/O and 1/I, which are easy to misread on a printed receipt.
RECEIPT_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
RECEIPT_CODE_LENGTH = 8
MAX_RECEIPT_CODE_ATTEMPTS = 10


class ProductNotFoundError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


class BuyerNotFoundError(Exception):
    pass


class InvalidDiscountError(Exception):
    pass


class SaleStatusError(Exception):
    """The sale is not in a state that allows the requested change (e.g. already voided)."""


class PaymentProofNotAllowedError(Exception):
    """Cash orders are paid in person, so they take no payment screenshot."""


class PaymentProofMissingError(Exception):
    """A digital-payment order cannot be confirmed before the buyer uploads proof."""


def generate_receipt_code(db: Session) -> str:
    for _ in range(MAX_RECEIPT_CODE_ATTEMPTS):
        code = "".join(random.choices(RECEIPT_CODE_ALPHABET, k=RECEIPT_CODE_LENGTH))
        if db.query(Sale.id).filter(Sale.receipt_code == code).first() is None:
            return code
    raise RuntimeError("Could not generate a unique receipt code")


def create_sale(
    db: Session,
    seller_id: uuid.UUID,
    sale_type: SaleType,
    buyer_id: uuid.UUID | None,
    payment_method: PaymentMethod,
    items: list[tuple[uuid.UUID, int, int | None]],
    note: str | None,
    total_cents_override: int | None,
    discount_cents: int = 0,
    status: SaleStatus = SaleStatus.COMPLETED,
) -> Sale:
    """Create a sale. Each item is (product_id, quantity, charged unit price or None for the list price).

    A `pending_payment` sale (a buyer's order) deducts stock the same way, which
    reserves it until the seller confirms payment or the order is cancelled.
    """
    if buyer_id is not None:
        buyer = db.get(User, buyer_id)
        if buyer is None or buyer.role != UserRole.BUYER:
            raise BuyerNotFoundError("Buyer not found")

    # Aggregate by product first so stock is validated for every line before
    # anything is deducted, even if the same product appears on multiple lines.
    aggregated: dict[uuid.UUID, int] = {}
    for product_id, quantity, _ in items:
        aggregated[product_id] = aggregated.get(product_id, 0) + quantity

    products: dict[uuid.UUID, Product] = {}
    for product_id, quantity in aggregated.items():
        product = db.get(Product, product_id)
        if product is None or product.seller_id != seller_id or not product.is_active:
            raise ProductNotFoundError(f"Product {product_id} not found")
        pieces_needed = quantity * product.pieces_per_unit
        if product.stock_pieces < pieces_needed:
            raise InsufficientStockError(f"Not enough stock for {product.name}")
        products[product_id] = product

    sale_items = [
        build_sale_item(None, products[product_id], quantity, unit_price_cents)
        for product_id, quantity, unit_price_cents in items
    ]
    subtotal_cents = sum(item.line_total_cents for item in sale_items) if items else total_cents_override
    if discount_cents and not items:
        raise InvalidDiscountError("A discount needs line items")
    if discount_cents > subtotal_cents:
        raise InvalidDiscountError("Discount cannot be more than the subtotal")

    sale = Sale(
        seller_id=seller_id,
        buyer_id=buyer_id,
        sale_type=sale_type,
        subtotal_cents=subtotal_cents,
        discount_cents=discount_cents,
        total_cents=subtotal_cents - discount_cents,
        payment_method=payment_method,
        receipt_code=generate_receipt_code(db),
        note=note,
        status=status,
    )
    db.add(sale)
    db.flush()

    for item in sale_items:
        item.sale_id = sale.id
        db.add(item)
        apply_stock_change(
            db,
            products[item.product_id],
            change_pieces=-item.pieces_deducted,
            reason=StockMovementReason.SALE,
            sale_id=sale.id,
        )

    db.commit()
    db.refresh(sale)
    return sale


def _lock_sale(db: Session, sale_id: uuid.UUID, *owner_filters) -> Sale | None:
    # Row-lock the sale so two taps (e.g. on "Void" or "Confirm") cannot both apply.
    return (
        db.query(Sale)
        .options(selectinload(Sale.items))
        .filter(Sale.id == sale_id, *owner_filters)
        .with_for_update(of=Sale)
        .first()
    )


def _reverse_sale(
    db: Session,
    sale: Sale | None,
    new_status: SaleStatus,
    reason: str | None,
    allowed_from: SaleStatus = SaleStatus.COMPLETED,
) -> Sale | None:
    if sale is None:
        return None
    if sale.status != allowed_from:
        raise SaleStatusError(f"Sale is already {sale.status.value}")

    movement_reason = {
        SaleStatus.VOIDED: StockMovementReason.VOID,
        SaleStatus.REFUNDED: StockMovementReason.REFUND,
        SaleStatus.CANCELLED: StockMovementReason.CANCEL,
    }[new_status]
    for item in sale.items:
        if item.product_id is None:
            continue
        product = db.get(Product, item.product_id)
        apply_stock_change(
            db, product, change_pieces=item.pieces_deducted, reason=movement_reason, sale_id=sale.id, note=reason
        )

    sale.status = new_status
    sale.status_changed_at = now_utc()
    sale.status_reason = reason
    db.commit()
    db.refresh(sale)
    return sale


def void_sale(db: Session, sale_id: uuid.UUID, seller_id: uuid.UUID, reason: str | None) -> Sale | None:
    """Cancel a sale entered by mistake: its stock comes back and it drops out of every metric."""
    sale = _lock_sale(db, sale_id, Sale.seller_id == seller_id)
    return _reverse_sale(db, sale, SaleStatus.VOIDED, reason)


def refund_sale(db: Session, sale_id: uuid.UUID, seller_id: uuid.UUID, reason: str | None) -> Sale | None:
    """Return a whole sale: its stock comes back and its total is reported as a refund."""
    sale = _lock_sale(db, sale_id, Sale.seller_id == seller_id)
    return _reverse_sale(db, sale, SaleStatus.REFUNDED, reason)


def reject_order(db: Session, sale_id: uuid.UUID, seller_id: uuid.UUID, reason: str | None) -> Sale | None:
    """The seller turns down a buyer's unpaid order: the reserved stock comes back."""
    sale = _lock_sale(db, sale_id, Sale.seller_id == seller_id)
    return _reverse_sale(db, sale, SaleStatus.CANCELLED, reason, allowed_from=SaleStatus.PENDING_PAYMENT)


def cancel_order_by_buyer(db: Session, sale_id: uuid.UUID, buyer_id: uuid.UUID) -> Sale | None:
    """The buyer withdraws their own unpaid order: the reserved stock comes back."""
    sale = _lock_sale(db, sale_id, Sale.buyer_id == buyer_id)
    return _reverse_sale(
        db, sale, SaleStatus.CANCELLED, "Cancelled by buyer", allowed_from=SaleStatus.PENDING_PAYMENT
    )


def submit_payment_proof(db: Session, sale_id: uuid.UUID, buyer_id: uuid.UUID, file: UploadFile) -> Sale | None:
    """Attach (or replace) the buyer's payment screenshot on their pending digital-payment order."""
    sale = _lock_sale(db, sale_id, Sale.buyer_id == buyer_id)
    if sale is None:
        return None
    if sale.status != SaleStatus.PENDING_PAYMENT:
        raise SaleStatusError(f"Order is already {sale.status.value}")
    if sale.payment_method == PaymentMethod.CASH:
        raise PaymentProofNotAllowedError("Cash orders are paid to the seller in person")

    sale.payment_proof_url = uploads_service.save_image(file, prefix=f"proof_{sale.id}", private=True)
    sale.proof_submitted_at = now_utc()
    db.commit()
    db.refresh(sale)
    return sale


def confirm_payment(db: Session, sale_id: uuid.UUID, seller_id: uuid.UUID) -> Sale | None:
    """The seller confirms a buyer's order was paid: it becomes a completed sale that counts everywhere."""
    sale = _lock_sale(db, sale_id, Sale.seller_id == seller_id)
    if sale is None:
        return None
    if sale.status != SaleStatus.PENDING_PAYMENT:
        raise SaleStatusError(f"Order is already {sale.status.value}")
    if sale.payment_method != PaymentMethod.CASH and sale.payment_proof_url is None:
        raise PaymentProofMissingError("The buyer has not uploaded proof of payment yet")

    sale.status = SaleStatus.COMPLETED
    sale.status_changed_at = now_utc()
    db.commit()
    db.refresh(sale)
    return sale


def get_buyer_sale(db: Session, sale_id: uuid.UUID, buyer_id: uuid.UUID) -> Sale | None:
    return (
        db.query(Sale)
        .options(selectinload(Sale.items))
        .filter(Sale.id == sale_id, Sale.buyer_id == buyer_id)
        .first()
    )


def _range_bounds(
    range_key: str | None, start: datetime | None, end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    if range_key == "custom":
        return start, end
    if range_key in RANGE_DAYS:
        # Local business days, so "today" starts at local midnight rather than UTC midnight.
        return resolve_range(range_key).start_utc, None
    return None, None


def list_sales(
    db: Session,
    seller_id: uuid.UUID,
    range_key: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    sale_type: SaleType | None = None,
    buyer_id: uuid.UUID | None = None,
    status: SaleStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Sale], int]:
    query = db.query(Sale).filter(Sale.seller_id == seller_id).options(selectinload(Sale.items))

    range_start, range_end = _range_bounds(range_key, start, end)
    if range_start is not None:
        query = query.filter(Sale.created_at >= range_start)
    if range_end is not None:
        query = query.filter(Sale.created_at <= range_end)
    if sale_type is not None:
        query = query.filter(Sale.sale_type == sale_type)
    if buyer_id is not None:
        query = query.filter(Sale.buyer_id == buyer_id)
    if status is not None:
        query = query.filter(Sale.status == status)

    total = query.count()
    items = (
        query.order_by(Sale.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return items, total


def get_sale(db: Session, sale_id: uuid.UUID, seller_id: uuid.UUID) -> Sale | None:
    return (
        db.query(Sale)
        .options(selectinload(Sale.items))
        .filter(Sale.id == sale_id, Sale.seller_id == seller_id)
        .first()
    )


def get_sale_by_receipt_code(db: Session, receipt_code: str) -> Sale | None:
    return (
        db.query(Sale)
        .options(selectinload(Sale.items))
        .filter(Sale.receipt_code == receipt_code.upper())
        .first()
    )


def search_buyers(db: Session, query_text: str, limit: int = 10) -> list[User]:
    like = f"%{query_text}%"
    return (
        db.query(User)
        .filter(User.role == UserRole.BUYER, User.is_active.is_(True))
        .filter(User.full_name.ilike(like) | User.email.ilike(like) | User.phone.ilike(like))
        .order_by(User.full_name.asc())
        .limit(limit)
        .all()
    )
