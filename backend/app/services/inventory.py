import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product, UnitType
from app.models.product_cost import CostSource, ProductCostHistory
from app.models.sale import PaymentMethod, Sale, SaleItem, SaleType
from app.models.stock_movement import StockMovement, StockMovementReason


MEASURE_QUANTITY_SCALE = 1000


def quantity_scale(unit_type: UnitType) -> int:
    """How many stored quantity units make one selling unit (measure products store thousandths)."""
    return MEASURE_QUANTITY_SCALE if unit_type == UnitType.MEASURE else 1


def line_total_cents(price_cents: int, quantity: int, unit_type: UnitType) -> int:
    scale = quantity_scale(unit_type)
    # Integer half-up rounding, so 1.5 yd at 333 cents/yd never drifts through floats.
    return (quantity * price_cents * 2 + scale) // (2 * scale)


class InsufficientStockError(Exception):
    pass


class ProductNotFoundError(Exception):
    pass


def set_product_cost(db: Session, product: Product, cost_cents: int | None, source: CostSource) -> None:
    """Update the product's unit cost, logging it to product_cost_history when it changes."""
    if cost_cents is None or cost_cents == product.cost_cents:
        return
    product.cost_cents = cost_cents
    db.add(ProductCostHistory(product_id=product.id, cost_cents=cost_cents, source=source))


def build_sale_item(
    sale_id: uuid.UUID | None, product: Product, quantity: int, unit_price_cents: int | None = None
) -> SaleItem:
    """A sale line that snapshots name, list price, charged price and cost at write time.

    `unit_price_cents` is the price the seller agreed during the transaction; it
    defaults to the product's current price and never changes the product itself.
    """
    charged = product.price_cents if unit_price_cents is None else unit_price_cents
    return SaleItem(
        sale_id=sale_id,
        product_id=product.id,
        product_name_snapshot=product.name,
        list_price_cents_snapshot=product.price_cents,
        unit_price_cents_snapshot=charged,
        unit_cost_cents_snapshot=product.cost_cents,
        cost_total_cents=(
            line_total_cents(product.cost_cents, quantity, product.unit_type)
            if product.cost_cents is not None
            else None
        ),
        quantity=quantity,
        unit_type_snapshot=product.unit_type,
        unit_label_snapshot=product.unit_label,
        pieces_deducted=quantity * product.pieces_per_unit,
        line_total_cents=line_total_cents(charged, quantity, product.unit_type),
    )


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


def bulk_restock(
    db: Session,
    seller_id: uuid.UUID,
    items: list[tuple[uuid.UUID, int, int | None]],
    note: str | None = None,
) -> list[Product]:
    """Restock several products; each item is (product_id, quantity, optional new unit cost)."""
    quantities: dict[uuid.UUID, int] = {}
    costs: dict[uuid.UUID, int] = {}
    for product_id, quantity, unit_cost_cents in items:
        quantities[product_id] = quantities.get(product_id, 0) + quantity
        if unit_cost_cents is not None:
            costs[product_id] = unit_cost_cents

    # Resolve every product before changing any stock, so one bad id fails the whole batch.
    products = [get_owned_product(db, product_id, seller_id) for product_id in quantities]

    restocked = []
    for product in products:
        updated = apply_stock_change(
            db, product, change_pieces=quantities[product.id], reason=StockMovementReason.RESTOCK, note=note
        )
        set_product_cost(db, updated, costs.get(product.id), CostSource.RESTOCK)
        restocked.append(updated)
    return restocked


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


def list_categories(db: Session, seller_id: uuid.UUID) -> list[str]:
    rows = (
        db.query(Product.category)
        .filter(
            Product.seller_id == seller_id,
            Product.is_active.is_(True),
            Product.category.isnot(None),
            Product.category != "",
        )
        .distinct()
        .all()
    )
    return sorted((row[0] for row in rows), key=str.lower)


def clear_category(db: Session, seller_id: uuid.UUID, category: str) -> int:
    """Remove a category name from all of the seller's active products. Returns how many were changed."""
    count = (
        db.query(Product)
        .filter(
            Product.seller_id == seller_id,
            Product.is_active.is_(True),
            Product.category == category,
        )
        .update({Product.category: None}, synchronize_session=False)
    )
    db.commit()
    return count


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
    unit_price_cents: int | None = None,
) -> tuple[Product, Sale]:
    item = build_sale_item(None, product, quantity, unit_price_cents)

    sale = Sale(
        seller_id=product.seller_id,
        buyer_id=None,
        sale_type=SaleType.WALK_IN,
        subtotal_cents=item.line_total_cents,
        total_cents=item.line_total_cents,
        payment_method=payment_method,
        receipt_code=generate_receipt_code(),
    )
    db.add(sale)
    db.flush()

    item.sale_id = sale.id
    db.add(item)

    updated_product = apply_stock_change(
        db,
        product,
        change_pieces=-item.pieces_deducted,
        reason=StockMovementReason.QUICK_SELL,
        sale_id=sale.id,
    )

    db.commit()
    db.refresh(updated_product)
    db.refresh(sale)
    return updated_product, sale
