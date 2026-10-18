"""Seed a fresh database with one seller, one buyer, and five products.

Products get cost prices. Pass --sales to also backfill historical sales across
the last 60 days (weekend-heavy, with a few haggled prices, discounts, a void and
a refund), useful for exercising every analytics tab and the demand forecast.
"""

import argparse
import random
import string
from datetime import datetime, time, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.business_time import BUSINESS_TZ, local_today
from app.database import SessionLocal
from app.models import (
    BusinessType,
    CostSource,
    PaymentMethod,
    Product,
    Sale,
    SaleStatus,
    SaleType,
    SellerProfile,
    UnitType,
    User,
    UserRole,
)
from app.services.inventory import build_sale_item, set_product_cost

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Excludes 0/O and 1/I to match the real receipt code generator's alphabet.
RECEIPT_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
# Relative traffic Monday..Sunday: market days are busiest on weekends.
WEEKDAY_WEIGHTS = [0.8, 0.8, 0.9, 0.9, 1.1, 1.6, 1.5]


def seed() -> tuple[User, User, list[Product]]:
    db = SessionLocal()
    try:
        seller = User(
            email="seller@example.com",
            hashed_password=pwd_context.hash("password123"),
            full_name="Aling Nena",
            role=UserRole.SELLER,
            phone="09171234567",
        )
        buyer = User(
            email="buyer@example.com",
            hashed_password=pwd_context.hash("password123"),
            full_name="Juan Dela Cruz",
            role=UserRole.BUYER,
            phone="09179876543",
        )
        db.add_all([seller, buyer])
        db.flush()

        db.add(
            SellerProfile(
                user_id=seller.id,
                business_name="Aling Nena's Sari-Sari Store",
                business_type=BusinessType.RETAIL,
                address="Stall 12, Public Market, Quezon City",
                description="Fresh produce and everyday essentials.",
            )
        )

        products = [
            Product(
                seller_id=seller.id,
                name="Itlog (Egg)",
                description="Fresh chicken eggs, sold by piece.",
                price_cents=1200,
                unit_type=UnitType.PIECE,
                pieces_per_unit=1,
                stock_pieces=300,
                low_stock_threshold=30,
                category="Poultry",
            ),
            Product(
                seller_id=seller.id,
                name="Kalamansi",
                description="Sold by piece.",
                price_cents=100,
                unit_type=UnitType.PIECE,
                pieces_per_unit=1,
                stock_pieces=500,
                low_stock_threshold=50,
                category="Produce",
            ),
            Product(
                seller_id=seller.id,
                name="Instant Noodles (Bundle of 5)",
                description="Sold per bundle of 5 packs.",
                price_cents=6000,
                unit_type=UnitType.BUNDLE,
                pieces_per_unit=5,
                stock_pieces=250,
                low_stock_threshold=25,
                category="Groceries",
            ),
            Product(
                seller_id=seller.id,
                name="Bottled Water (Bundle of 6)",
                description="Sold per bundle of 6 bottles.",
                price_cents=9000,
                unit_type=UnitType.BUNDLE,
                pieces_per_unit=6,
                stock_pieces=180,
                low_stock_threshold=24,
                category="Beverages",
            ),
            Product(
                seller_id=seller.id,
                name="Bigas (Rice)",
                description="Sold by the kilo.",
                price_cents=6000,
                unit_type=UnitType.MEASURE,
                unit_label="kg",
                pieces_per_unit=1,
                stock_pieces=50000,
                low_stock_threshold=5000,
                category="Staples",
            ),
        ]
        db.add_all(products)
        db.flush()
        for product in products:
            set_product_cost(db, product, round(product.price_cents * random.uniform(0.6, 0.8)), CostSource.MANUAL)

        db.commit()
        for product in products:
            db.refresh(product)
        db.refresh(seller)
        db.refresh(buyer)
        print(f"Seeded seller={seller.email} buyer={buyer.email} products={len(products)}")
        return seller, buyer, products
    finally:
        db.close()


def _random_receipt_code(existing: set[str]) -> str:
    while True:
        code = "".join(random.choices(RECEIPT_ALPHABET, k=8))
        if code not in existing:
            existing.add(code)
            return code


def _sale_quantity(product: Product) -> int:
    if product.unit_type == UnitType.MEASURE:
        return random.choice([250, 500, 1000, 1500])
    return random.randint(1, 5)


def seed_sales_history(
    db: Session, seller: User, buyer: User, products: list[Product], count: int = 500, days: int = 60
) -> None:
    """Backfill historical sales, backdated across `days`, for analytics/dashboard testing.

    Skips real stock deduction — this is bulk historical data for charts and
    performance testing, not a stock-accurate replay. `apply_stock_change`
    already has its own coverage for the correctness of live deductions.
    """
    existing_codes = {code for (code,) in db.query(Sale.receipt_code).all()}
    payment_methods = [PaymentMethod.CASH, PaymentMethod.GCASH, PaymentMethod.MAYA, PaymentMethod.OTHER]
    now = datetime.now(timezone.utc)
    today = local_today()
    window = [today - timedelta(days=offset) for offset in range(days)]
    weights = [WEEKDAY_WEIGHTS[day.weekday()] for day in window]

    sales = []
    for _ in range(count):
        # A local market-hours moment (6am-7pm Manila), not a UTC one.
        day = random.choices(window, weights=weights, k=1)[0]
        local = datetime.combine(day, time(random.randint(6, 18), random.randint(0, 59)), tzinfo=BUSINESS_TZ)
        created_at = min(local.astimezone(timezone.utc), now)
        is_itemized = random.random() < 0.3
        chosen = random.sample(products, k=random.randint(1, min(3, len(products))))

        items = [
            build_sale_item(
                None,
                product,
                _sale_quantity(product),
                round(product.price_cents * random.uniform(0.85, 0.95)) if random.random() < 0.08 else None,
            )
            for product in chosen
        ]
        subtotal_cents = sum(item.line_total_cents for item in items)
        discount_cents = round(subtotal_cents * 0.05, -2) if is_itemized and random.random() < 0.06 else 0

        sale = Sale(
            seller_id=seller.id,
            buyer_id=buyer.id if is_itemized else None,
            sale_type=SaleType.ITEMIZED if is_itemized else SaleType.WALK_IN,
            subtotal_cents=subtotal_cents,
            discount_cents=discount_cents,
            total_cents=subtotal_cents - discount_cents,
            payment_method=random.choice(payment_methods),
            receipt_code=_random_receipt_code(existing_codes),
            created_at=created_at,
        )
        db.add(sale)
        db.flush()
        for item in items:
            item.sale_id = sale.id
            db.add(item)
        sales.append(sale)

    # One mistaken sale and one return, so voids and refunds show up in the reports.
    # (Stock isn't replayed for this backfill, so only the status changes.)
    recent = sorted(sales, key=lambda sale: sale.created_at, reverse=True)
    for sale, status, reason in ((recent[0], SaleStatus.VOIDED, "Rang up twice"),
                                 (recent[1], SaleStatus.REFUNDED, "Item returned")):
        sale.status = status
        sale.status_changed_at = now
        sale.status_reason = reason

    db.commit()
    print(f"Seeded {count} historical sales across the last {days} days")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sales", action="store_true", help="also backfill historical sales")
    parser.add_argument("--sales-count", type=int, default=500)
    parser.add_argument("--sales-days", type=int, default=60)
    args = parser.parse_args()

    seller_user, buyer_user, seeded_products = seed()

    if args.sales:
        session = SessionLocal()
        try:
            seed_sales_history(
                session, seller_user, buyer_user, seeded_products, count=args.sales_count, days=args.sales_days
            )
        finally:
            session.close()
