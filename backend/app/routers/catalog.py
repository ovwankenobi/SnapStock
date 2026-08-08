import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import require_buyer
from app.database import get_db
from app.models.product import Product
from app.models.sale import Sale, SaleType
from app.models.user import User
from app.schemas.catalog import (
    BuyerReceiptItem,
    BuyerReceiptListResponse,
    BuyRequest,
    CatalogProductListResponse,
    CatalogProductRead,
    CatalogSellerRead,
    ImageSearchResponse,
    ImageSearchResultItem,
)
from app.schemas.product import compute_stock_status
from app.schemas.sale import SaleItemRead, SaleRead
from app.services import catalog as catalog_service
from app.services import sales as sales_service

router = APIRouter(tags=["catalog"])

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _to_catalog_product(product: Product, seller_name: str) -> CatalogProductRead:
    return CatalogProductRead(
        id=product.id,
        seller_id=product.seller_id,
        seller_name=seller_name,
        name=product.name,
        description=product.description,
        photo_url=product.photo_url,
        price_cents=product.price_cents,
        unit_type=product.unit_type,
        pieces_per_unit=product.pieces_per_unit,
        category=product.category,
        stock_status=compute_stock_status(product.stock_pieces, product.low_stock_threshold),
    )


def _to_sale_read(sale: Sale, buyer_name: str | None) -> SaleRead:
    return SaleRead(
        id=sale.id,
        seller_id=sale.seller_id,
        buyer_id=sale.buyer_id,
        buyer_name=buyer_name,
        sale_type=sale.sale_type,
        total_cents=sale.total_cents,
        payment_method=sale.payment_method,
        receipt_code=sale.receipt_code,
        note=sale.note,
        created_at=sale.created_at,
        items=[SaleItemRead.model_validate(item) for item in sale.items],
    )


@router.get("/catalog/products", response_model=CatalogProductListResponse)
def list_catalog_products(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    seller_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    products, seller_names, total = catalog_service.list_catalog_products(
        db, search=search, category=category, seller_id=seller_id, page=page, page_size=page_size
    )
    items = [_to_catalog_product(p, seller_names.get(p.seller_id, "")) for p in products]
    return CatalogProductListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/catalog/products/{product_id}", response_model=CatalogProductRead)
def get_catalog_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = catalog_service.get_catalog_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    seller_name = catalog_service.seller_names_by_id(db, {product.seller_id}).get(product.seller_id, "")
    return _to_catalog_product(product, seller_name)


@router.get("/catalog/sellers/{seller_id}", response_model=CatalogSellerRead)
def get_catalog_seller(seller_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        seller, products = catalog_service.get_seller_with_products(db, seller_id)
    except catalog_service.SellerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found") from exc

    profile = seller.seller_profile
    return CatalogSellerRead(
        id=seller.id,
        business_name=profile.business_name,
        business_type=profile.business_type,
        address=profile.address,
        description=profile.description,
        photo_url=profile.photo_url,
        products=[_to_catalog_product(p, profile.business_name) for p in products],
    )


@router.post("/catalog/search-by-image", response_model=ImageSearchResponse)
def search_by_image(
    query: str = Form(min_length=1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Stage 1: the photo is accepted but not analyzed — it's a shortcut into a
    # pre-filled text search the buyer confirms. Stage 2 swaps this matching
    # step for real vision search without changing the request/response shape.
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo must be a JPEG, PNG, or WebP image",
        )

    products, seller_names, _ = catalog_service.list_catalog_products(db, search=query, page=1, page_size=20)
    results = [
        ImageSearchResultItem(product=_to_catalog_product(p, seller_names.get(p.seller_id, "")), confidence=None)
        for p in products
    ]
    return ImageSearchResponse(query=query, results=results)


@router.post("/catalog/products/{product_id}/order", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def buy_product(
    product_id: uuid.UUID,
    payload: BuyRequest,
    buyer: User = Depends(require_buyer),
    db: Session = Depends(get_db),
):
    product = catalog_service.get_catalog_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    try:
        sale = sales_service.create_sale(
            db,
            seller_id=product.seller_id,
            sale_type=SaleType.ITEMIZED,
            buyer_id=buyer.id,
            payment_method=payload.payment_method,
            items=[(product.id, payload.quantity)],
            note=None,
            total_cents_override=None,
        )
    except sales_service.InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except sales_service.ProductNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return _to_sale_read(sale, buyer.full_name)


@router.get("/me/receipts", response_model=BuyerReceiptListResponse)
def get_my_receipts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    buyer: User = Depends(require_buyer),
    db: Session = Depends(get_db),
):
    sales, seller_names, total = catalog_service.list_buyer_receipts(
        db, buyer_id=buyer.id, page=page, page_size=page_size
    )
    items = [
        BuyerReceiptItem(
            id=sale.id,
            seller_id=sale.seller_id,
            seller_name=seller_names.get(sale.seller_id, ""),
            sale_type=sale.sale_type,
            total_cents=sale.total_cents,
            payment_method=sale.payment_method,
            receipt_code=sale.receipt_code,
            created_at=sale.created_at,
            item_count=len(sale.items),
        )
        for sale in sales
    ]
    return BuyerReceiptListResponse(items=items, total=total, page=page, page_size=page_size)
