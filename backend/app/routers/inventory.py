import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import require_seller
from app.models.product import Product, UnitType
from app.models.product_cost import CostSource
from app.models.stock_movement import StockMovementReason
from app.models.user import User
from app.database import get_db
from app.schemas.product import (
    BulkRestockRequest,
    ProductCreate,
    ProductImageSearchResponse,
    ProductImageSearchResultItem,
    ProductListResponse,
    ProductRead,
    ProductUpdate,
    QuickSellRequest,
    QuickSellResult,
    RestockRequest,
)
from app.services import inventory as inventory_service
from app.services import uploads as uploads_service

router = APIRouter(prefix="/products", tags=["inventory"])


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


@router.get("/categories", response_model=list[str])
def list_product_categories(
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return inventory_service.list_categories(db, seller.id)


@router.delete("/categories", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_category(
    name: str = Query(min_length=1),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    inventory_service.clear_category(db, seller.id, name)


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
        unit_label=payload.unit_label,
        pieces_per_unit=payload.pieces_per_unit,
        stock_pieces=0,
        low_stock_threshold=payload.low_stock_threshold,
        category=payload.category,
    )
    db.add(product)
    db.flush()
    inventory_service.set_product_cost(db, product, payload.cost_cents, CostSource.MANUAL)

    if payload.stock_pieces > 0:
        inventory_service.apply_stock_change(
            db, product, change_pieces=payload.stock_pieces, reason=StockMovementReason.INITIAL
        )

    db.commit()
    db.refresh(product)
    return product


@router.post("/restock", response_model=list[ProductRead])
def bulk_restock_products(
    payload: BulkRestockRequest,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    try:
        products = inventory_service.bulk_restock(
            db,
            seller.id,
            items=[(item.product_id, item.quantity, item.unit_cost_cents) for item in payload.items],
            note=payload.note,
        )
    except inventory_service.ProductNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found") from exc

    db.commit()
    for product in products:
        db.refresh(product)
    return products


@router.post("/search-by-image", response_model=ProductImageSearchResponse)
def search_products_by_image(
    query: str = Form(min_length=1),
    file: UploadFile = File(...),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    # Stage 1, mirroring the catalog's search-by-image: the photo is validated but
    # not analyzed, and matching is a keyword search over the seller's own products.
    try:
        uploads_service.validate_image(file)
    except uploads_service.InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    products, _ = inventory_service.list_products(db, seller_id=seller.id, search=query, page=1, page_size=20)
    return ProductImageSearchResponse(
        query=query,
        results=[ProductImageSearchResultItem(product=p, confidence=None) for p in products],
    )


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
    changes = payload.model_dump(exclude_unset=True)
    # Cost goes through the history log; clearing it (null) is not supported, a cost only gets corrected.
    cost_cents = changes.pop("cost_cents", None)
    for field, value in changes.items():
        setattr(product, field, value)
    inventory_service.set_product_cost(db, product, cost_cents, CostSource.MANUAL)

    if product.unit_type != UnitType.BUNDLE and product.pieces_per_unit != 1:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pieces_per_unit only applies to bundle products",
        )
    if product.unit_type == UnitType.MEASURE and not product.unit_label:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="unit_label is required for measure products",
        )
    if product.unit_type != UnitType.MEASURE:
        product.unit_label = None
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
            db,
            product,
            quantity=payload.quantity,
            payment_method=payload.payment_method,
            unit_price_cents=payload.unit_price_cents,
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
    inventory_service.set_product_cost(db, updated_product, payload.unit_cost_cents, CostSource.RESTOCK)
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

    try:
        product.photo_url = uploads_service.save_image(file, prefix=str(product.id))
    except uploads_service.InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    db.refresh(product)
    return product
