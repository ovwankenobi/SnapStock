import uuid

from sqlalchemy.orm import Session, selectinload

from app.models.product import Product
from app.models.sale import Sale
from app.models.user import SellerProfile, User, UserRole


class SellerNotFoundError(Exception):
    pass


def seller_names_by_id(db: Session, seller_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not seller_ids:
        return {}
    profiles = db.query(SellerProfile).filter(SellerProfile.user_id.in_(seller_ids)).all()
    return {profile.user_id: profile.business_name for profile in profiles}


def list_catalog_products(
    db: Session,
    search: str | None = None,
    category: str | None = None,
    seller_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], dict[uuid.UUID, str], int]:
    query = (
        db.query(Product)
        .join(User, User.id == Product.seller_id)
        .filter(Product.is_active.is_(True), User.is_active.is_(True), User.role == UserRole.SELLER)
    )

    if search:
        like = f"%{search}%"
        query = query.filter(Product.name.ilike(like) | Product.category.ilike(like))
    if category:
        query = query.filter(Product.category == category)
    if seller_id:
        query = query.filter(Product.seller_id == seller_id)

    total = query.count()
    items = (
        query.order_by(Product.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, seller_names_by_id(db, {p.seller_id for p in items}), total


def get_catalog_product(db: Session, product_id: uuid.UUID) -> Product | None:
    return (
        db.query(Product)
        .join(User, User.id == Product.seller_id)
        .filter(
            Product.id == product_id,
            Product.is_active.is_(True),
            User.is_active.is_(True),
            User.role == UserRole.SELLER,
        )
        .first()
    )


def get_seller_with_products(db: Session, seller_id: uuid.UUID) -> tuple[User, list[Product]]:
    seller = (
        db.query(User)
        .options(selectinload(User.seller_profile))
        .filter(User.id == seller_id, User.role == UserRole.SELLER, User.is_active.is_(True))
        .first()
    )
    if seller is None or seller.seller_profile is None:
        raise SellerNotFoundError("Seller not found")

    products = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.is_active.is_(True))
        .order_by(Product.created_at.desc())
        .all()
    )
    return seller, products


def list_buyer_receipts(
    db: Session, buyer_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> tuple[list[Sale], dict[uuid.UUID, str], int]:
    query = db.query(Sale).options(selectinload(Sale.items)).filter(Sale.buyer_id == buyer_id)

    total = query.count()
    items = (
        query.order_by(Sale.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return items, seller_names_by_id(db, {sale.seller_id for sale in items}), total
