import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import require_seller
from app.models.product import Product, UnitType
from app.models.stock_movement import StockMovementReason
from app.models.user import User
from app.database import get_db
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
    QuickSellRequest,
    QuickSellResult,
    RestockRequest,
)
from app.services import inventory as inventory_service

router = APIRouter(prefix="/products", tags=["inventory"])

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _get_owned_or_404(db: Session, product_id: uuid.UUID, seller: User) -> Product:
    try:
        return inventory_service.get_owned_product(db, product_id, seller.id)
    except inventory_service.ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found") from exc


@router.get("/low-stock", response_model=list[ProductRead])
def get_low_stock_products(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return inventory_service.list_low_stock(db, seller.id)


@router.get("", response_model=ProductListResponse)
def list_products(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    stock_status: str | None = Query(default=None, pattern="^(in_stock|low|out)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    items, total = inventory_service.list_products(
        db,
        seller_id=seller.id,
        search=search,
        category=category,
        stock_status=stock_status,
        page=page,
        page_size=page_size,
    )
    return ProductListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    if payload.unit_type != UnitType.BUNDLE and payload.pieces_per_unit != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pieces_per_unit only applies to bundle products",
        )

    product = Product(
        seller_id=seller.id,
        name=payload.name,
        description=payload.description,
        price_cents=payload.price_cents,
        unit_type=payload.unit_type,
        pieces_per_unit=payload.pieces_per_unit,
        stock_pieces=0,
        low_stock_threshold=payload.low_stock_threshold,
        category=payload.category,
    )
    db.add(product)
    db.flush()

    if payload.stock_pieces > 0:
        inventory_service.apply_stock_change(
            db, product, change_pieces=payload.stock_pieces, reason=StockMovementReason.INITIAL
        )

    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: uuid.UUID,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return _get_owned_or_404(db, product_id, seller)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = _get_owned_or_404(db, product_id, seller)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: uuid.UUID,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = _get_owned_or_404(db, product_id, seller)
    product.is_active = False
    db.commit()


@router.post("/{product_id}/quick-sell", response_model=QuickSellResult)
def quick_sell_product(
    product_id: uuid.UUID,
    payload: QuickSellRequest,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = _get_owned_or_404(db, product_id, seller)
    try:
        updated_product, sale = inventory_service.quick_sell(
            db, product, quantity=payload.quantity, payment_method=payload.payment_method
        )
    except inventory_service.InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return QuickSellResult(
        product=updated_product,
        sale_id=sale.id,
        receipt_code=sale.receipt_code,
        total_cents=sale.total_cents,
    )


@router.post("/{product_id}/restock", response_model=ProductRead)
def restock_product(
    product_id: uuid.UUID,
    payload: RestockRequest,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = _get_owned_or_404(db, product_id, seller)
    updated_product = inventory_service.apply_stock_change(
        db,
        product,
        change_pieces=payload.quantity,
        reason=StockMovementReason.RESTOCK,
        note=payload.note,
    )
    db.commit()
    db.refresh(updated_product)
    return updated_product


@router.post("/{product_id}/photo", response_model=ProductRead)
def upload_product_photo(
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    product = _get_owned_or_404(db, product_id, seller)

    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo must be a JPEG, PNG, or WebP image",
        )

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    filename = f"{product.id}_{uuid.uuid4().hex[:8]}{extension}"
    destination = upload_dir / filename

    with destination.open("wb") as buffer:
        buffer.write(file.file.read())

    product.photo_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(product)
    return product
