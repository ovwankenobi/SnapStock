"""Seed a fresh database with one seller, one buyer, and five products.

Pass --sales to also backfill historical sales across the last 60 days, useful
for exercising analytics/dashboard performance and the demand forecast.
"""

import argparse
import random
import string
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    BusinessType,
    PaymentMethod,
    Product,
    Sale,
    SaleItem,
    SaleType,
    SellerProfile,
    UnitType,
    User,
    UserRole,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Excludes 0/O and 1/I to match the real receipt code generator's alphabet.
RECEIPT_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


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
                description="Sold by the gram.",
                price_cents=6,
                unit_type=UnitType.GRAMS,
                pieces_per_unit=1,
                stock_pieces=50000,
                low_stock_threshold=5000,
                category="Staples",
            ),
        ]
        db.add_all(products)

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
    if product.unit_type == UnitType.GRAMS:
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

    for _ in range(count):
        created_at = now - timedelta(days=random.uniform(0, days), hours=random.uniform(0, 10))
        is_itemized = random.random() < 0.3
        chosen = random.sample(products, k=random.randint(1, min(3, len(products))))

        line_items = []
        total_cents = 0
        for product in chosen:
            quantity = _sale_quantity(product)
            line_total = quantity * product.price_cents
            total_cents += line_total
            line_items.append((product, quantity, line_total))

        sale = Sale(
            seller_id=seller.id,
            buyer_id=buyer.id if is_itemized else None,
            sale_type=SaleType.ITEMIZED if is_itemized else SaleType.WALK_IN,
            total_cents=total_cents,
            payment_method=random.choice(payment_methods),
            receipt_code=_random_receipt_code(existing_codes),
            created_at=created_at,
        )
        db.add(sale)
        db.flush()

        for product, quantity, line_total in line_items:
            db.add(
                SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    product_name_snapshot=product.name,
                    unit_price_cents_snapshot=product.price_cents,
                    quantity=quantity,
                    unit_type_snapshot=product.unit_type,
                    pieces_deducted=quantity * product.pieces_per_unit,
                    line_total_cents=line_total,
                )
            )

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
