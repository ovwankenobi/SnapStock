"""Populate the database with a realistic demo dataset.

Produces 2 sellers (with distinct catalogs), 8 buyers, 30 products, and 200
sales spread across the trailing 60 days with a mix of walk-in and itemized
sales — enough data for a credible demo and for exercising analytics.

Run with:  python -m app.seed
"""

import random
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    BusinessType,
    PaymentMethod,
    Product,
    Sale,
    SaleItem,
    SaleType,
    SellerProfile,
    StockMovementReason,
    UnitType,
    User,
    UserRole,
)
from app.services.inventory import InsufficientStockError, apply_stock_change
from app.services.sales import generate_receipt_code

SEED_START = datetime.now(timezone.utc) - timedelta(days=70)
SALES_WINDOW_DAYS = 60
TOTAL_SALES = 200

PAYMENT_WEIGHTS = [
    (PaymentMethod.CASH, 60),
    (PaymentMethod.GCASH, 25),
    (PaymentMethod.MAYA, 10),
    (PaymentMethod.BANK_TRANSFER, 3),
    (PaymentMethod.OTHER, 2),
]

SELLERS = [
    {
        "email": "nena@example.com",
        "full_name": "Aling Nena Reyes",
        "business_name": "Nena's Sari-Sari Store",
        "business_type": BusinessType.RETAIL,
        "address": "Stall 12, Poblacion Public Market",
        "description": "Everyday grocery and household needs.",
        "products": [
            ("Pancit Canton", "Noodles", UnitType.PIECE, 1, 1500, 200),
            ("Corned Beef Can", "Canned Goods", UnitType.PIECE, 1, 4200, 150),
            ("Sardines in Tomato Sauce", "Canned Goods", UnitType.PIECE, 1, 2200, 180),
            ("Bottled Water 500ml", "Beverages", UnitType.PIECE, 1, 1500, 300),
            ("Coke 1.5L", "Beverages", UnitType.PIECE, 1, 6500, 90),
            ("Bar Soap", "Household", UnitType.PIECE, 1, 2000, 140),
            ("Detergent Powder Sachet", "Household", UnitType.PIECE, 1, 1200, 250),
            ("Shampoo Sachet (10s)", "Personal Care", UnitType.BUNDLE, 10, 4500, 600),
            ("Coffee 3-in-1 (10s)", "Beverages", UnitType.BUNDLE, 10, 4800, 500),
            ("Eggs (Tray of 30)", "Eggs", UnitType.BUNDLE, 30, 21000, 900),
            ("Cooking Oil 1L", "Cooking", UnitType.PIECE, 1, 9500, 70),
            ("Pancit Canton Family Pack", "Noodles", UnitType.PIECE, 1, 3000, 100),
            ("Toilet Paper Roll", "Household", UnitType.PIECE, 1, 2500, 130),
            ("Candles", "Household", UnitType.PIECE, 1, 1000, 200),
            ("Matches Box", "Household", UnitType.PIECE, 1, 500, 300),
        ],
    },
    {
        "email": "junmeatshop@example.com",
        "full_name": "Mang Jun Santos",
        "business_name": "Mang Jun's Palengke Meat & Produce",
        "business_type": BusinessType.BOTH,
        "address": "Row 4, Wet Section, Public Market",
        "description": "Fresh meat, poultry, seafood, and produce daily.",
        "products": [
            ("Pork Belly (Liempo)", "Pork", UnitType.GRAMS, 1, 32, 20000),
            ("Ground Pork", "Pork", UnitType.GRAMS, 1, 28, 15000),
            ("Pork Chop", "Pork", UnitType.GRAMS, 1, 30, 12000),
            ("Beef Brisket", "Beef", UnitType.GRAMS, 1, 38, 10000),
            ("Beef Ground", "Beef", UnitType.GRAMS, 1, 35, 8000),
            ("Whole Chicken", "Chicken", UnitType.GRAMS, 1, 19, 25000),
            ("Chicken Breast", "Chicken", UnitType.GRAMS, 1, 22, 15000),
            ("Chicken Wings", "Chicken", UnitType.GRAMS, 1, 21, 12000),
            ("Bangus (Milkfish)", "Fish", UnitType.GRAMS, 1, 18, 18000),
            ("Tilapia", "Fish", UnitType.GRAMS, 1, 14, 20000),
            ("Galunggong", "Fish", UnitType.GRAMS, 1, 16, 16000),
            ("Squid", "Seafood", UnitType.GRAMS, 1, 28, 8000),
            ("Shrimp", "Seafood", UnitType.GRAMS, 1, 35, 6000),
            ("Kalamansi (Bag)", "Produce", UnitType.PIECE, 1, 3000, 60),
            ("Tomatoes (Bag)", "Produce", UnitType.PIECE, 1, 4000, 50),
        ],
    },
]

BUYERS = [
    ("mariabuyer@example.com", "Maria Cruz"),
    ("juandelacruz@example.com", "Juan Dela Cruz"),
    ("liza.buyer@example.com", "Liza Fernandez"),
    ("pedro.buyer@example.com", "Pedro Ramos"),
    ("ana.buyer@example.com", "Ana Villanueva"),
    ("ramon.buyer@example.com", "Ramon Torres"),
    ("grace.buyer@example.com", "Grace Mendoza"),
    ("carlo.buyer@example.com", "Carlo Bautista"),
]


def _weighted_choice(pairs):
    values, weights = zip(*pairs)
    return random.choices(values, weights=weights, k=1)[0]


def _random_timestamp() -> datetime:
    day_offset = random.randint(0, SALES_WINDOW_DAYS - 1)
    hour = random.randint(6, 19)  # market hours
    minute = random.randint(0, 59)
    day = datetime.now(timezone.utc) - timedelta(days=day_offset)
    return day.replace(hour=hour, minute=minute, second=random.randint(0, 59), microsecond=0)


def _quantity_for(unit_type: UnitType) -> int:
    if unit_type == UnitType.GRAMS:
        return random.choice([250, 500, 1000, 1500])
    if unit_type == UnitType.BUNDLE:
        return random.randint(1, 2)
    return random.randint(1, 4)


def _affordable_quantity(product: Product, desired: int) -> int:
    pieces_per = product.pieces_per_unit
    max_units = product.stock_pieces // pieces_per
    return max(0, min(desired, max_units))


def clear_existing_data(db) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def create_sellers(db) -> list[dict]:
    created = []
    for spec in SELLERS:
        user = User(
            email=spec["email"],
            hashed_password=hash_password("password123"),
            full_name=spec["full_name"],
            role=UserRole.SELLER,
            created_at=SEED_START,
            updated_at=SEED_START,
        )
        db.add(user)
        db.flush()

        db.add(
            SellerProfile(
                user_id=user.id,
                business_name=spec["business_name"],
                business_type=spec["business_type"],
                address=spec["address"],
                description=spec["description"],
            )
        )

        products = []
        for name, category, unit_type, pieces_per_unit, price_cents, stock in spec["products"]:
            product = Product(
                seller_id=user.id,
                name=name,
                description=f"{name} — fresh from {spec['business_name']}.",
                price_cents=price_cents,
                unit_type=unit_type,
                pieces_per_unit=pieces_per_unit,
                stock_pieces=0,
                low_stock_threshold=max(5, round(stock * 0.12)),
                category=category,
                created_at=SEED_START,
                updated_at=SEED_START,
            )
            db.add(product)
            db.flush()
            apply_stock_change(
                db, product, change_pieces=stock, reason=StockMovementReason.INITIAL
            )
            products.append(product)

        created.append({"user": user, "products": products})

    db.commit()
    return created


def create_buyers(db) -> list[User]:
    buyers = []
    for email, full_name in BUYERS:
        user = User(
            email=email,
            hashed_password=hash_password("password123"),
            full_name=full_name,
            role=UserRole.BUYER,
            created_at=SEED_START,
            updated_at=SEED_START,
        )
        db.add(user)
        buyers.append(user)
    db.commit()
    return buyers


def _build_sale_with_items(db, seller: User, buyer: User | None, products: list[Product], created_at: datetime) -> Sale | None:
    candidates = [p for p in products if p.stock_pieces > 0]
    if not candidates:
        return None
    random.shuffle(candidates)

    line_plan = []
    for product in candidates[: random.randint(1, 3) if buyer else 1]:
        desired = _quantity_for(product.unit_type)
        quantity = _affordable_quantity(product, desired)
        if quantity > 0:
            line_plan.append((product, quantity))
    if not line_plan:
        return None

    total_cents = sum(product.price_cents * quantity for product, quantity in line_plan)
    sale = Sale(
        seller_id=seller.id,
        buyer_id=buyer.id if buyer else None,
        sale_type=SaleType.ITEMIZED if buyer else SaleType.WALK_IN,
        total_cents=total_cents,
        payment_method=_weighted_choice(PAYMENT_WEIGHTS),
        receipt_code=generate_receipt_code(db),
        created_at=created_at,
    )
    db.add(sale)
    db.flush()

    for product, quantity in line_plan:
        pieces = quantity * product.pieces_per_unit
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name_snapshot=product.name,
                unit_price_cents_snapshot=product.price_cents,
                quantity=quantity,
                unit_type_snapshot=product.unit_type,
                pieces_deducted=pieces,
                line_total_cents=product.price_cents * quantity,
            )
        )
        try:
            apply_stock_change(
                db,
                product,
                change_pieces=-pieces,
                reason=StockMovementReason.SALE if buyer else StockMovementReason.QUICK_SELL,
                sale_id=sale.id,
            )
        except InsufficientStockError:
            db.rollback()
            return None

    return sale


def _build_aggregate_walk_in(db, seller: User, created_at: datetime) -> Sale:
    total_cents = random.randint(5000, 50000)
    sale = Sale(
        seller_id=seller.id,
        buyer_id=None,
        sale_type=SaleType.WALK_IN,
        total_cents=total_cents,
        payment_method=_weighted_choice(PAYMENT_WEIGHTS),
        receipt_code=generate_receipt_code(db),
        note="Assorted items",
        created_at=created_at,
    )
    db.add(sale)
    return sale


def create_sales(db, sellers: list[dict], buyers: list[User]) -> int:
    created_count = 0
    attempts = 0
    max_attempts = TOTAL_SALES * 4

    while created_count < TOTAL_SALES and attempts < max_attempts:
        attempts += 1
        seller_entry = random.choice(sellers)
        seller = seller_entry["user"]
        products = seller_entry["products"]
        created_at = _random_timestamp()

        roll = random.random()
        if roll < 0.35:
            sale = _build_sale_with_items(db, seller, random.choice(buyers), products, created_at)
        elif roll < 0.90:
            sale = _build_sale_with_items(db, seller, None, products, created_at)
        else:
            sale = _build_aggregate_walk_in(db, seller, created_at)

        if sale is not None:
            db.commit()
            created_count += 1
        else:
            db.rollback()

    return created_count


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Clearing existing data...")
        clear_existing_data(db)

        print("Creating sellers and products...")
        sellers = create_sellers(db)

        print("Creating buyers...")
        buyers = create_buyers(db)

        print("Generating sales across the last 60 days...")
        created_count = create_sales(db, sellers, buyers)

        total_products = sum(len(entry["products"]) for entry in sellers)
        print(
            f"Done: {len(sellers)} sellers, {total_products} products, "
            f"{len(buyers)} buyers, {created_count} sales."
        )
        print("Login with password123 for any seeded account, e.g. nena@example.com / password123")
    finally:
        db.close()


if __name__ == "__main__":
    run()
