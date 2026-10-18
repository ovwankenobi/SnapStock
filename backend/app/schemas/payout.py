import uuid
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel

# Cash is never a payout account, since buyers just hand it over.
PayoutMethod = Literal["gcash", "maya", "bank_transfer", "other"]
METHODS_NEEDING_BANK_NAME = {"bank_transfer", "other"}


class PayoutAccountRead(CamelModel):
    id: uuid.UUID
    method: PayoutMethod
    account_name: str
    account_number: str
    bank_name: str | None = None
    qr_url: str | None = None
    is_default: bool


class PayoutAccountCreate(CamelModel):
    method: PayoutMethod
    account_name: str = Field(min_length=1)
    account_number: str = Field(min_length=1)
    bank_name: str | None = None
    is_default: bool = False

    @model_validator(mode="after")
    def check_bank_name(self) -> "PayoutAccountCreate":
        if self.method in METHODS_NEEDING_BANK_NAME and not (self.bank_name or "").strip():
            raise ValueError("bank_name is required for bank_transfer and other payout accounts")
        return self


class PayoutAccountUpdate(CamelModel):
    method: PayoutMethod | None = None
    account_name: str | None = Field(default=None, min_length=1)
    account_number: str | None = Field(default=None, min_length=1)
    bank_name: str | None = None
    is_default: bool | None = None
