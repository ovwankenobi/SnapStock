import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.deps import require_seller
from app.database import get_db
from app.models.sale import PaymentMethod, Sale, SaleStatus, SaleType
from app.models.user import User
from app.schemas.sale import (
    BuyerSearchResult,
    PublicReceipt,
    PublicReceiptItem,
    SaleCreate,
    SaleItemRead,
    SaleListItem,
    SaleListResponse,
    SaleRead,
    SaleStatusChange,
)
from app.services import sales as sales_service
from app.services import uploads as uploads_service

router = APIRouter(prefix="/sales", tags=["sales"])


def _buyer_names(db: Session, sales: list[Sale]) -> dict[uuid.UUID, str]:
    buyer_ids = {sale.buyer_id for sale in sales if sale.buyer_id is not None}
    if not buyer_ids:
        return {}
    buyers = db.query(User).filter(User.id.in_(buyer_ids)).all()
    return {buyer.id: buyer.full_name for buyer in buyers}


def _to_sale_read(db: Session, sale: Sale) -> SaleRead:
    buyer_name = None
    if sale.buyer_id is not None:
        buyer = db.get(User, sale.buyer_id)
        buyer_name = buyer.full_name if buyer else None
    return SaleRead(
        id=sale.id,
        seller_id=sale.seller_id,
        buyer_id=sale.buyer_id,
        buyer_name=buyer_name,
        sale_type=sale.sale_type,
        subtotal_cents=sale.subtotal_cents,
        discount_cents=sale.discount_cents,
        total_cents=sale.total_cents,
        status=sale.status,
        status_changed_at=sale.status_changed_at,
        status_reason=sale.status_reason,
        payment_method=sale.payment_method,
        receipt_code=sale.receipt_code,
        note=sale.note,
        created_at=sale.created_at,
        payment_proof_url=uploads_service.private_url(sale.payment_proof_url),
        proof_submitted_at=sale.proof_submitted_at,
        items=[SaleItemRead.model_validate(item) for item in sale.items],
    )


@router.get("/buyers/search", response_model=list[BuyerSearchResult])
def search_buyers(
    q: str = Query(min_length=2),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return sales_service.search_buyers(db, q)


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(
    payload: SaleCreate,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    try:
        sale = sales_service.create_sale(
            db,
            seller_id=seller.id,
            sale_type=payload.sale_type,
            buyer_id=payload.buyer_id,
            payment_method=payload.payment_method,
            items=[
                (item.product_id, item.quantity, item.unit_price_cents, item.by_piece) for item in payload.items
            ],
            note=payload.note,
            total_cents_override=payload.total_cents,
            discount_cents=payload.discount_cents,
        )
    except sales_service.BuyerNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except sales_service.ProductNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (
        sales_service.InsufficientStockError,
        sales_service.InvalidDiscountError,
        sales_service.InvalidSaleUnitError,
    ) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _to_sale_read(db, sale)


@router.get("", response_model=SaleListResponse)
def list_sales(
    range_filter: str | None = Query(default=None, alias="range", pattern="^(today|week|month|custom)$"),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    sale_type: SaleType | None = Query(default=None),
    payment_method: PaymentMethod | None = Query(default=None),
    buyer_id: uuid.UUID | None = Query(default=None),
    sale_status: SaleStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    if range_filter == "custom" and (start is None or end is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start and end are required when range=custom",
        )

    items, total = sales_service.list_sales(
        db,
        seller_id=seller.id,
        range_key=range_filter,
        start=start,
        end=end,
        sale_type=sale_type,
        payment_method=payment_method,
        buyer_id=buyer_id,
        status=sale_status,
        page=page,
        page_size=page_size,
    )
    buyer_names = _buyer_names(db, items)
    list_items = [
        SaleListItem(
            id=sale.id,
            buyer_id=sale.buyer_id,
            buyer_name=buyer_names.get(sale.buyer_id) if sale.buyer_id else None,
            sale_type=sale.sale_type,
            subtotal_cents=sale.subtotal_cents,
            discount_cents=sale.discount_cents,
            total_cents=sale.total_cents,
            status=sale.status,
            status_changed_at=sale.status_changed_at,
            status_reason=sale.status_reason,
            payment_method=sale.payment_method,
            receipt_code=sale.receipt_code,
            note=sale.note,
            created_at=sale.created_at,
            payment_proof_url=uploads_service.private_url(sale.payment_proof_url),
            proof_submitted_at=sale.proof_submitted_at,
            item_count=len(sale.items),
        )
        for sale in items
    ]
    return SaleListResponse(items=list_items, total=total, page=page, page_size=page_size)


@router.get("/receipt/{receipt_code}", response_model=PublicReceipt)
def get_public_receipt(receipt_code: str, db: Session = Depends(get_db)):
    sale = sales_service.get_sale_by_receipt_code(db, receipt_code)
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")

    seller = (
        db.query(User).options(joinedload(User.seller_profile)).filter(User.id == sale.seller_id).first()
    )
    business_name = seller.seller_profile.business_name if seller and seller.seller_profile else "Store"

    return PublicReceipt(
        business_name=business_name,
        receipt_code=sale.receipt_code,
        sale_type=sale.sale_type,
        items=[
            PublicReceiptItem(
                name=item.product_name_snapshot,
                quantity=item.quantity,
                unit_type=item.unit_type_snapshot,
                unit_label=item.unit_label_snapshot,
                unit_price_cents=item.unit_price_cents_snapshot,
                line_total_cents=item.line_total_cents,
            )
            for item in sale.items
        ],
        subtotal_cents=sale.subtotal_cents,
        discount_cents=sale.discount_cents,
        total_cents=sale.total_cents,
        status=sale.status,
        payment_method=sale.payment_method,
        created_at=sale.created_at,
    )


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(
    sale_id: uuid.UUID,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    sale = sales_service.get_sale(db, sale_id, seller.id)
    if sale is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    return _to_sale_read(db, sale)


def _change_status(change, db: Session, sale_id: uuid.UUID, seller: User, payload: SaleStatusChange) -> SaleRead:
    try:
        sale = change(db, sale_id, seller.id, payload.reason)
    except (sales_service.SaleStatusError, sales_service.PaymentProofMissingError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if sale is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    return _to_sale_read(db, sale)


@router.post("/{sale_id}/void", response_model=SaleRead)
def void_sale(
    sale_id: uuid.UUID,
    payload: SaleStatusChange,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return _change_status(sales_service.void_sale, db, sale_id, seller, payload)


@router.post("/{sale_id}/refund", response_model=SaleRead)
def refund_sale(
    sale_id: uuid.UUID,
    payload: SaleStatusChange,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return _change_status(sales_service.refund_sale, db, sale_id, seller, payload)


@router.post("/{sale_id}/confirm-payment", response_model=SaleRead)
def confirm_payment(
    sale_id: uuid.UUID,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    """Confirm a buyer's order was paid: it becomes a completed sale linked to the buyer."""
    return _change_status(
        lambda db, sale_id, seller_id, _reason: sales_service.confirm_payment(db, sale_id, seller_id),
        db,
        sale_id,
        seller,
        SaleStatusChange(),
    )


@router.post("/{sale_id}/proof", response_model=SaleRead)
def upload_sale_proof(
    sale_id: uuid.UUID,
    file: UploadFile = File(...),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    """Attach the seller's photo of a walk-in customer's payment confirmation."""
    try:
        sale = sales_service.attach_seller_payment_proof(db, sale_id, seller.id, file)
    except uploads_service.InvalidImageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (sales_service.SaleStatusError, sales_service.PaymentProofNotAllowedError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if sale is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found")
    return _to_sale_read(db, sale)


@router.post("/{sale_id}/reject", response_model=SaleRead)
def reject_order(
    sale_id: uuid.UUID,
    payload: SaleStatusChange,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    return _change_status(sales_service.reject_order, db, sale_id, seller, payload)

