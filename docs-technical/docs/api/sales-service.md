# Sales Service

Owns `Sale`/`SaleItem` data and is the only writer of the `sales` table. Router:
`app/routers/sales.py` (prefix `/sales`), business logic in `app/services/sales.py`. Stock
deduction is delegated to the Inventory Service's `apply_stock_change` — see
[Architecture Overview](../architecture/overview.md).

All money fields are integer cents. All endpoints require `Authorization: Bearer <token>` and
`require_seller` **except** `GET /sales/receipt/{receiptCode}`, which is the one public,
unauthenticated endpoint in the whole API.

## `GET /sales/buyers/search`

Search registered buyers by email or phone, for the seller's buyer-linked checkout flow.

**Query:** `q` (min length 2). **Response:** `list[BuyerSearchResult]` (`id`, `fullName`, `email`, `phone`).

## `POST /sales`

Create a sale — either itemized (cart of products) or a walk-in lump sum with no line items.

**Request (`SaleCreate`):**

| Field | Type | Notes |
|---|---|---|
| `saleType` | `itemized` \| `walk_in` | |
| `buyerId` | UUID \| null | **required** if `itemized`; **must be null** if `walk_in` |
| `paymentMethod` | `cash`\|`gcash`\|`maya`\|`bank_transfer`\|`other` | |
| `items` | `{ productId, quantity }[]` | required (non-empty) if `itemized` |
| `note` | string \| null | |
| `totalCents` | int \| null | only for a walk-in sale with **no** items (manual lump-sum amount); mutually exclusive with `items` |

Validated server-side (`SaleCreate.check_consistency`): exactly one of `items` or `totalCents`
must be provided, and `buyerId` presence must match `saleType`.

Stock is validated for **every** line item (duplicate `productId`s aggregated first) before any
of them are deducted — a multi-item sale either fully succeeds or fully fails.

**Response:** `SaleRead` (201). **Errors:** `404` (`BuyerNotFoundError`, `ProductNotFoundError`),
`400` (`InsufficientStockError`).

## `GET /sales`

List/filter the caller's sales.

**Query params:** `range` (`today`\|`week`\|`month`\|`custom`), `start`/`end` (required if
`range=custom`), `saleType`, `buyerId`, `page`, `pageSize`.

**Response:** `SaleListResponse` — `{ items: SaleListItem[], total, page, pageSize }`. Each item
includes a resolved `buyerName` (looked up separately, not stored on the sale) and `itemCount`.

## `GET /sales/receipt/{receiptCode}`

**Public, no auth.** What the printed/QR receipt (`/r/:receiptCode` in the frontend) resolves to.
Returns only public-safe fields — no buyer/seller IDs, emails, or phone numbers.

**Response (`PublicReceipt`):** `businessName`, `receiptCode`, `saleType`, `items[]` (name,
quantity, unitType, unitPriceCents, lineTotalCents — all read from the `sale_items` **snapshot**
columns, not the live product), `totalCents`, `paymentMethod`, `createdAt`.

## `GET /sales/{saleId}`

Fetch one of the caller's sales by ID. 404 if not found or not owned. Response: `SaleRead`.

---

## Buyer-facing ordering & receipts (`app/routers/catalog.py`)

These endpoints live in the catalog router file but call directly into
`services.sales.create_sale` / read `Sale` rows, so they belong to this service conceptually.

### `POST /catalog/products/{productId}/order`

Auth: `require_buyer`. Places an itemized, buyer-linked order for a single product — the buyer
version of ringing up a sale. Internally calls `create_sale(sale_type=ITEMIZED, buyer_id=buyer.id,
items=[(product_id, quantity)])`. There is **no seller-confirmation step**: the order completes
immediately if stock allows (see [Data Flow](../architecture/data-flow.md)).

**Request (`BuyRequest`):** `{ quantity: int (>0), paymentMethod }`
**Response:** `SaleRead` (201). **Errors:** `400` (`InsufficientStockError`), `404` (product not found).

### `GET /me/receipts`

Auth: `require_buyer`. Paginated purchase history for the current buyer.

**Query:** `page`, `pageSize`. **Response:** `BuyerReceiptListResponse` — each item includes
`sellerName`, `saleType`, `totalCents`, `paymentMethod`, `receiptCode`, `createdAt`, `itemCount`.

---

## Related: analytics endpoints (`app/routers/analytics.py`)

Read-only aggregations over the same `sales`/`products` tables. Prefix `/analytics`, auth
`require_seller`.

| Method & path | Description |
|---|---|
| `GET /analytics/summary` | Today's sale count/revenue, low-stock count, week-over-week revenue change %. |
| `GET /analytics/top-products?range=&limit=` | Top products by quantity/revenue over `today`\|`week`\|`month`. |
| `GET /analytics/sales-trend?range=` | Per-day sale count + revenue series for charting. |
| `GET /analytics/forecast` | Per-product demand forecast: average daily pieces sold (7-/30-day), estimated `daysOfStockRemaining`, and `atRisk` (≤ 7 days left). Requires ≥14 distinct days of sales history for a product before it forecasts anything — otherwise the average/remaining-days fields are `null`. |
