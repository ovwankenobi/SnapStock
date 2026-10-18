"""Populate the database with a realistic demo dataset.

Produces 2 sellers (with distinct catalogs), 8 buyers, 31 products with cost
prices, and 200 sales spread across the trailing 60 days with a mix of walk-in
and itemized sales — busier on weekends, during local market hours, with the
odd haggled price, discount, void and refund — enough data for a credible demo
and for exercising every analytics tab.

Run with:  python -m app.seed
"""

import random
from datetime import datetime, time, timedelta, timezone

from app.core.business_time import BUSINESS_TZ, local_today
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models import (
    BusinessType,
    CostSource,
    PaymentMethod,
    Product,
    Sale,
    SaleType,
    SellerProfile,
    StockMovementReason,
    UnitType,
    User,
    UserRole,
)
from app.services.inventory import (
    InsufficientStockError,
    apply_stock_change,
    build_sale_item,
    set_product_cost,
)
from app.services.sales import generate_receipt_code, refund_sale, void_sale

SEED_START = datetime.now(timezone.utc) - timedelta(days=70)
SALES_WINDOW_DAYS = 60
TOTAL_SALES = 200
# Relative traffic Monday..Sunday: market days are busiest on weekends.
WEEKDAY_WEIGHTS = [0.8, 0.8, 0.9, 0.9, 1.1, 1.6, 1.5]
# Share of a product's price that is its cost.
COST_RATIO_RANGE = (0.6, 0.8)
PRICE_EDIT_CHANCE = 0.08
DISCOUNT_CHANCE = 0.06

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
            ("Plastic Twine (Tali)", "Household", UnitType.MEASURE, 1, 500, 100000, "m"),
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
            ("Pork Belly (Liempo)", "Pork", UnitType.MEASURE, 1, 32000, 20000, "kg"),
            ("Ground Pork", "Pork", UnitType.MEASURE, 1, 28000, 15000, "kg"),
            ("Pork Chop", "Pork", UnitType.MEASURE, 1, 30000, 12000, "kg"),
            ("Beef Brisket", "Beef", UnitType.MEASURE, 1, 38000, 10000, "kg"),
            ("Beef Ground", "Beef", UnitType.MEASURE, 1, 35000, 8000, "kg"),
            ("Whole Chicken", "Chicken", UnitType.MEASURE, 1, 19000, 25000, "kg"),
            ("Chicken Breast", "Chicken", UnitType.MEASURE, 1, 22000, 15000, "kg"),
            ("Chicken Wings", "Chicken", UnitType.MEASURE, 1, 21000, 12000, "kg"),
            ("Bangus (Milkfish)", "Fish", UnitType.MEASURE, 1, 18000, 18000, "kg"),
            ("Tilapia", "Fish", UnitType.MEASURE, 1, 14000, 20000, "kg"),
            ("Galunggong", "Fish", UnitType.MEASURE, 1, 16000, 16000, "kg"),
            ("Squid", "Seafood", UnitType.MEASURE, 1, 28000, 8000, "kg"),
            ("Shrimp", "Seafood", UnitType.MEASURE, 1, 35000, 6000, "kg"),
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
    """A moment during local market hours (6am-7pm), weighted toward weekends."""
    today = local_today()
    days = [today - timedelta(days=offset) for offset in range(SALES_WINDOW_DAYS)]
    day = random.choices(days, weights=[WEEKDAY_WEIGHTS[d.weekday()] for d in days], k=1)[0]
    at = time(random.randint(6, 18), random.randint(0, 59), random.randint(0, 59))
    local = datetime.combine(day, at, tzinfo=BUSINESS_TZ)
    return min(local.astimezone(timezone.utc), datetime.now(timezone.utc))


def _quantity_for(unit_type: UnitType) -> int:
    if unit_type == UnitType.MEASURE:
        # Thousandths of the product's unit: 0.25, 0.5, 1, 1.5.
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
        for name, category, unit_type, pieces_per_unit, price_cents, stock, *rest in spec["products"]:
            product = Product(
                seller_id=user.id,
                name=name,
                description=f"{name} — fresh from {spec['business_name']}.",
                price_cents=price_cents,
                unit_type=unit_type,
                unit_label=rest[0] if rest else None,
                pieces_per_unit=pieces_per_unit,
                stock_pieces=0,
                low_stock_threshold=max(5, round(stock * 0.12)),
                category=category,
                created_at=SEED_START,
                updated_at=SEED_START,
            )
            db.add(product)
            db.flush()
            set_product_cost(db, product, round(price_cents * random.uniform(*COST_RATIO_RANGE)), CostSource.MANUAL)
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

    # Now and then the seller haggles a line down by 5-15%.
    items = [
        build_sale_item(
            None,
            product,
            quantity,
            round(product.price_cents * random.uniform(0.85, 0.95)) if random.random() < PRICE_EDIT_CHANCE else None,
        )
        for product, quantity in line_plan
    ]
    subtotal_cents = sum(item.line_total_cents for item in items)
    discount_cents = round(subtotal_cents * 0.05, -2) if buyer and random.random() < DISCOUNT_CHANCE else 0
    sale = Sale(
        seller_id=seller.id,
        buyer_id=buyer.id if buyer else None,
        sale_type=SaleType.ITEMIZED if buyer else SaleType.WALK_IN,
        subtotal_cents=subtotal_cents,
        discount_cents=discount_cents,
        total_cents=subtotal_cents - discount_cents,
        payment_method=_weighted_choice(PAYMENT_WEIGHTS),
        receipt_code=generate_receipt_code(db),
        created_at=created_at,
    )
    db.add(sale)
    db.flush()

    for (product, _), item in zip(line_plan, items):
        item.sale_id = sale.id
        db.add(item)
        try:
            apply_stock_change(
                db,
                product,
                change_pieces=-item.pieces_deducted,
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


def reverse_some_sales(db, sellers: list[dict]) -> None:
    """Void one recent sale and refund another per seller, so the status flows show up in reports."""
    for entry in sellers:
        recent = (
            db.query(Sale)
            .filter(Sale.seller_id == entry["user"].id, Sale.total_cents > 0)
            .order_by(Sale.created_at.desc())
            .limit(10)
            .all()
        )
        itemized = [sale for sale in recent if sale.items]
        if len(itemized) >= 2:
            void_sale(db, itemized[0].id, entry["user"].id, "Rang up twice")
            refund_sale(db, itemized[1].id, entry["user"].id, "Item returned")


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
        reverse_some_sales(db, sellers)

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
