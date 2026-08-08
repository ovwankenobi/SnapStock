import random
import string
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleType
from app.models.stock_movement import StockMovementReason
from app.models.user import User, UserRole
from app.services.inventory import apply_stock_change

# Excludes 0/O and 1/I, which are easy to misread on a printed receipt.
RECEIPT_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
RECEIPT_CODE_LENGTH = 8
MAX_RECEIPT_CODE_ATTEMPTS = 10

RANGE_TRAILING_DAYS = {"week": 7, "month": 30}


class ProductNotFoundError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


class BuyerNotFoundError(Exception):
    pass


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
    items: list[tuple[uuid.UUID, int]],
    note: str | None,
    total_cents_override: int | None,
) -> Sale:
    if buyer_id is not None:
        buyer = db.get(User, buyer_id)
        if buyer is None or buyer.role != UserRole.BUYER:
            raise BuyerNotFoundError("Buyer not found")

    # Aggregate by product first so stock is validated for every line before
    # anything is deducted, even if the same product appears on multiple lines.
    aggregated: dict[uuid.UUID, int] = {}
    for product_id, quantity in items:
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

    total_cents = (
        sum(quantity * products[product_id].price_cents for product_id, quantity in items)
        if items
        else total_cents_override
    )

    sale = Sale(
        seller_id=seller_id,
        buyer_id=buyer_id,
        sale_type=sale_type,
        total_cents=total_cents,
        payment_method=payment_method,
        receipt_code=generate_receipt_code(db),
        note=note,
    )
    db.add(sale)
    db.flush()

    for product_id, quantity in items:
        product = products[product_id]
        pieces = quantity * product.pieces_per_unit
        line_total = quantity * product.price_cents
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                unit_price_cents_snapshot=product.price_cents,
                quantity=quantity,
                unit_type_snapshot=product.unit_type,
                pieces_deducted=pieces,
                line_total_cents=line_total,
            )
        )
        apply_stock_change(
            db,
            product,
            change_pieces=-pieces,
            reason=StockMovementReason.SALE,
            sale_id=sale.id,
        )

    db.commit()
    db.refresh(sale)
    return sale


def _range_bounds(
    range_key: str | None, start: datetime | None, end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    if range_key == "custom":
        return start, end
    if range_key == "today":
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0), None
    if range_key in RANGE_TRAILING_DAYS:
        now = datetime.now(timezone.utc)
        return now - timedelta(days=RANGE_TRAILING_DAYS[range_key]), None
    return None, None


def list_sales(
    db: Session,
    seller_id: uuid.UUID,
    range_key: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    sale_type: SaleType | None = None,
    buyer_id: uuid.UUID | None = None,
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
        .filter((User.email.ilike(like)) | (User.phone.ilike(like)))
        .order_by(User.full_name.asc())
        .limit(limit)
        .all()
    )
