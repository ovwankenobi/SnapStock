import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.deps import require_seller
from app.database import get_db
from app.models.user import User
from app.schemas.payout import PayoutAccountCreate, PayoutAccountRead, PayoutAccountUpdate
from app.services import payouts as payouts_service
from app.services import uploads as uploads_service

router = APIRouter(prefix="/seller/payout-accounts", tags=["payouts"])


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("", response_model=list[PayoutAccountRead])
def list_payout_accounts(seller: User = Depends(require_seller), db: Session = Depends(get_db)):
    return payouts_service.list_accounts(db, seller)


@router.post("", response_model=PayoutAccountRead, status_code=status.HTTP_201_CREATED)
def create_payout_account(
    payload: PayoutAccountCreate,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    account = payouts_service.create_account(db, seller, payload)
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}", response_model=PayoutAccountRead)
def update_payout_account(
    account_id: uuid.UUID,
    payload: PayoutAccountUpdate,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    try:
        account = payouts_service.update_account(db, seller, account_id, payload)
    except payouts_service.PayoutAccountNotFoundError as exc:
        raise _not_found(exc) from exc
    except payouts_service.InvalidPayoutAccountError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payout_account(
    account_id: uuid.UUID,
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    try:
        payouts_service.delete_account(db, seller, account_id)
    except payouts_service.PayoutAccountNotFoundError as exc:
        raise _not_found(exc) from exc
    db.commit()


@router.post("/{account_id}/qr", response_model=PayoutAccountRead)
def upload_payout_qr(
    account_id: uuid.UUID,
    file: UploadFile = File(...),
    seller: User = Depends(require_seller),
    db: Session = Depends(get_db),
):
    try:
        account = payouts_service.set_qr(db, seller, account_id, file)
    except payouts_service.PayoutAccountNotFoundError as exc:
        raise _not_found(exc) from exc
    except uploads_service.InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(account)
    return account
