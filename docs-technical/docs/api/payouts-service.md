# Payout Accounts

Where a seller receives non-cash payments: their GCash, Maya, bank or other e-wallet accounts,
each optionally with a QR code. Buyers see these accounts on the order page, and the seller can
show the matching QR to a walk-in customer. Router: `app/routers/payouts.py` (prefix
`/seller/payout-accounts`), business logic in `app/services/payouts.py`, model
`SellerPayoutAccount` (`app/models/payout_account.py`).

All endpoints require `Authorization: Bearer <token>` and `require_seller`. Accounts hang off the
seller's `seller_profiles` row, and every query filters by that profile, so a seller can only
see and change their own accounts.

## Rules

- `method` reuses the sales `payment_method` enum **minus `cash`**: `gcash`, `maya`,
  `bank_transfer` or `other`. Cash is never a payout account because buyers just hand it over.
- `bankName` is required for `bank_transfer` (the bank) and `other` (the provider, e.g. GoTyme,
  ShopeePay). The schema rejects a missing one with `422`.
- Exactly one account is the default. The first account a seller creates becomes the default
  automatically, and setting `isDefault: true` on another account clears it everywhere else.
- Lists come back default first, then oldest first.

**`PayoutAccountRead`:** `id`, `method`, `accountName`, `accountNumber`, `bankName`, `qrUrl`,
`isDefault`.

## `GET /seller/payout-accounts`

List the caller's accounts. **Response:** `list[PayoutAccountRead]`.

## `POST /seller/payout-accounts`

**Request (`PayoutAccountCreate`):** `{ method, accountName, accountNumber, bankName?, isDefault? }`
(`accountName` and `accountNumber` are trimmed and must not be empty).

**Response:** `PayoutAccountRead` (201).

## `PATCH /seller/payout-accounts/{accountId}`

Partial update (`PayoutAccountUpdate`, all fields optional). **Errors:** `404` if the account
isn't the caller's; `422` if the change leaves a `bank_transfer`/`other` account without a
`bankName`.

## `DELETE /seller/payout-accounts/{accountId}`

Returns `204`. **Errors:** `404`.

## `POST /seller/payout-accounts/{accountId}/qr`

Multipart `file` (JPEG/PNG/WebP), saved through `services/uploads.save_image` and stored as
`qrUrl` (`/uploads/...`). Uploading again replaces the QR. **Errors:** `400` (not an image),
`404`.

---

## Where the accounts show up

- **Buyer order page:** `GET /me/orders/{saleId}` returns the seller's `payoutAccounts`, so the
  buyer can scan a QR or copy an account number before uploading their payment screenshot (see
  [Sales Service](sales-service.md)).
- **Payment-method pickers:** `features/payouts/PaymentMethodPicker.jsx` always offers Cash and
  greys out every other method the seller has no account for. It is used in the buyer's
  `BuySheet` and in the seller's walk-in `PaymentSheet`, where it shows the matching QR for the
  customer to scan.
- **Onboarding:** after a seller registers, `RegisterPage` offers to add a first account (it can
  be skipped). Until the seller has one, the dashboard shows `PayoutSetupBanner`. Sellers manage
  accounts later under **Profile → Payout accounts** (`PayoutAccountsSection`).
