import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleType
from app.models.stock_movement import StockMovement, StockMovementReason


class InsufficientStockError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


def get_owned_product(db: Session, product_id: uuid.UUID, seller_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None or product.seller_id != seller_id or not product.is_active:
        raise ProductNotFoundError("Product not found")
    return product


def apply_stock_change(
    db: Session,
    product: Product,
    change_pieces: int,
    reason: StockMovementReason,
    sale_id: uuid.UUID | None = None,
    note: str | None = None,
) -> Product:
    locked = db.execute(
        select(Product).where(Product.id == product.id).with_for_update()
    ).scalar_one()

    new_stock = locked.stock_pieces + change_pieces
    if new_stock < 0:
        raise InsufficientStockError("Not enough stock available")

    locked.stock_pieces = new_stock
    db.add(
        StockMovement(
            product_id=locked.id,
            change_pieces=change_pieces,
            reason=reason,
            sale_id=sale_id,
            note=note,
        )
    )
    db.flush()
    return locked


def list_products(
    db: Session,
    seller_id: uuid.UUID,
    search: str | None = None,
    category: str | None = None,
    stock_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], int]:
    query = db.query(Product).filter(Product.seller_id == seller_id, Product.is_active.is_(True))

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(Product.category == category)
    if stock_status == "out":
        query = query.filter(Product.stock_pieces <= 0)
    elif stock_status == "low":
        query = query.filter(Product.stock_pieces > 0, Product.stock_pieces <= Product.low_stock_threshold)
    elif stock_status == "in_stock":
        query = query.filter(Product.stock_pieces > Product.low_stock_threshold)

    total = query.count()
    items = (
        query.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def list_low_stock(db: Session, seller_id: uuid.UUID) -> list[Product]:
    return (
        db.query(Product)
        .filter(
            Product.seller_id == seller_id,
            Product.is_active.is_(True),
            Product.stock_pieces <= Product.low_stock_threshold,
        )
        .order_by(Product.stock_pieces.asc())
        .all()
    )


def generate_receipt_code() -> str:
    return f"WI-{uuid.uuid4().hex[:10].upper()}"


def quick_sell(
    db: Session,
    product: Product,
    quantity: int,
    payment_method: PaymentMethod,
) -> tuple[Product, Sale]:
    pieces_to_deduct = quantity * product.pieces_per_unit
    line_total_cents = quantity * product.price_cents

    sale = Sale(
        seller_id=product.seller_id,
        buyer_id=None,
        sale_type=SaleType.WALK_IN,
        total_cents=line_total_cents,
        payment_method=payment_method,
        receipt_code=generate_receipt_code(),
    )
    db.add(sale)
    db.flush()

    db.add(
        SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            product_name_snapshot=product.name,
            unit_price_cents_snapshot=product.price_cents,
            quantity=quantity,
            unit_type_snapshot=product.unit_type,
            pieces_deducted=pieces_to_deduct,
            line_total_cents=line_total_cents,
        )
    )

    updated_product = apply_stock_change(
        db,
        product,
        change_pieces=-pieces_to_deduct,
        reason=StockMovementReason.QUICK_SELL,
        sale_id=sale.id,
    )

    db.commit()
    db.refresh(updated_product)
    db.refresh(sale)
    return updated_product, sale
