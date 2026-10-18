import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAtMixin, UUIDPkMixin, UpdatedAtMixin
from app.models.sale import PaymentMethod


class SellerPayoutAccount(UUIDPkMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    """Where a seller receives non-cash payments (GCash, Maya, bank, ...).

    `method` reuses the sales `payment_method` enum so a buyer's chosen payment
    method maps straight onto the seller's matching account(s). CASH is never
    stored here — that's enforced at the schema layer.
    """

    __tablename__ = "seller_payout_accounts"

    seller_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String, nullable=False)
    account_number: Mapped[str] = mapped_column(String, nullable=False)
    # Bank name for BANK_TRANSFER, provider name (GoTyme, ShopeePay, ...) for OTHER.
    bank_name: Mapped[str | None] = mapped_column(String, nullable=True)
    qr_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    seller_profile: Mapped["SellerProfile"] = relationship(back_populates="payout_accounts")  # noqa: F821
