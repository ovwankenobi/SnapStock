import uuid

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.payout_account import SellerPayoutAccount
from app.models.sale import PaymentMethod
from app.models.user import SellerProfile, User
from app.schemas.payout import METHODS_NEEDING_BANK_NAME, PayoutAccountCreate, PayoutAccountUpdate
from app.services import uploads as uploads_service


class PayoutAccountNotFoundError(Exception):
    pass


class InvalidPayoutAccountError(Exception):
    pass


def _profile(seller: User) -> SellerProfile:
    if seller.seller_profile is None:
        raise PayoutAccountNotFoundError("Seller profile not found")
    return seller.seller_profile


def _accounts_query(db: Session, profile: SellerProfile):
    return db.query(SellerPayoutAccount).filter(SellerPayoutAccount.seller_profile_id == profile.id)


def list_accounts(db: Session, seller: User) -> list[SellerPayoutAccount]:
    return (
        _accounts_query(db, _profile(seller))
        .order_by(SellerPayoutAccount.is_default.desc(), SellerPayoutAccount.created_at)
        .all()
    )


def get_owned_account(db: Session, seller: User, account_id: uuid.UUID) -> SellerPayoutAccount:
    account = (
        _accounts_query(db, _profile(seller)).filter(SellerPayoutAccount.id == account_id).first()
    )
    if account is None:
        raise PayoutAccountNotFoundError("Payout account not found")
    return account


def _make_default(db: Session, profile: SellerProfile, account: SellerPayoutAccount) -> None:
    _accounts_query(db, profile).filter(SellerPayoutAccount.id != account.id).update(
        {SellerPayoutAccount.is_default: False}, synchronize_session="fetch"
    )
    account.is_default = True


def create_account(db: Session, seller: User, data: PayoutAccountCreate) -> SellerPayoutAccount:
    profile = _profile(seller)
    is_first = _accounts_query(db, profile).count() == 0

    account = SellerPayoutAccount(
        seller_profile_id=profile.id,
        method=PaymentMethod(data.method),
        account_name=data.account_name.strip(),
        account_number=data.account_number.strip(),
        bank_name=(data.bank_name or "").strip() or None,
        is_default=False,
    )
    db.add(account)
    db.flush()

    if is_first or data.is_default:
        _make_default(db, profile, account)
    return account


def update_account(
    db: Session, seller: User, account_id: uuid.UUID, data: PayoutAccountUpdate
) -> SellerPayoutAccount:
    account = get_owned_account(db, seller, account_id)
    changes = data.model_dump(exclude_unset=True)

    if changes.get("method") is not None:
        account.method = PaymentMethod(changes["method"])
    for field in ("account_name", "account_number"):
        if changes.get(field) is not None:
            setattr(account, field, changes[field].strip())
    if "bank_name" in changes:
        account.bank_name = (changes["bank_name"] or "").strip() or None

    if account.method.value in METHODS_NEEDING_BANK_NAME and not account.bank_name:
        raise InvalidPayoutAccountError("Bank name is required for bank and other payout accounts")

    # Clearing the default directly is ignored, so a seller with accounts always has a default.
    if changes.get("is_default"):
        _make_default(db, _profile(seller), account)
    return account


def delete_account(db: Session, seller: User, account_id: uuid.UUID) -> None:
    account = get_owned_account(db, seller, account_id)
    was_default = account.is_default
    db.delete(account)
    db.flush()

    if was_default:
        replacement = (
            _accounts_query(db, _profile(seller)).order_by(SellerPayoutAccount.created_at).first()
        )
        if replacement is not None:
            replacement.is_default = True


def set_qr(db: Session, seller: User, account_id: uuid.UUID, file: UploadFile) -> SellerPayoutAccount:
    account = get_owned_account(db, seller, account_id)
    account.qr_url = uploads_service.save_image(file, prefix=f"payout_{account.id}")
    return account
