# Sales Service

Owns `Sale`/`SaleItem` data and is the only writer of the `sales` table. Router:
`app/routers/sales.py` (prefix `/sales`), business logic in `app/services/sales.py`. Stock
deduction is delegated to the Inventory Service's `apply_stock_change` — see
[Architecture Overview](../architecture/overview.md).

All money fields are integer cents. All endpoints require `Authorization: Bearer <token>` and
`require_seller` **except** `GET /sales/receipt/{receiptCode}`, which is the one public,
unauthenticated endpoint in the whole API.

## `GET /sales/buyers/search`

Search registered buyers by name, email or phone. The current frontend doesn't call it, because
the seller's New Sale → Buyer Account tab now only approves online orders (see below).

**Query:** `q` (min length 2). **Response:** `list[BuyerSearchResult]` (`id`, `fullName`, `email`, `phone`).

## `POST /sales`

Create a sale — either itemized (cart of products) or a walk-in lump sum with no line items.

**Request (`SaleCreate`):**

| Field | Type | Notes |
|---|---|---|
| `saleType` | `itemized` \| `walk_in` | |
| `buyerId` | UUID \| null | **required** if `itemized`; **must be null** if `walk_in` |
| `paymentMethod` | `cash`\|`gcash`\|`maya`\|`bank_transfer`\|`other` | |
| `items` | `{ productId, quantity, unitPriceCents?, byPiece? }[]` | required (non-empty) if `itemized`. `unitPriceCents` is the price agreed during the sale; omitted = the product's current price. It never changes the product. `byPiece: true` sells single pieces of a `bundle` product at bundle price ÷ pieces per bundle (400 for other unit types); see [Unit Conversion](../architecture/unit-conversion.md). `POST /catalog/products/{id}/order` takes the same optional `byPiece`. |
| `note` | string \| null | |
| `totalCents` | int \| null | only for a walk-in sale with **no** items (manual lump-sum amount); mutually exclusive with `items` |
| `discountCents` | int, default 0 | sale-level amount off the subtotal; only with `items`, and at most the subtotal |

Validated server-side (`SaleCreate.check_consistency`): exactly one of `items` or `totalCents`
must be provided, and `buyerId` presence must match `saleType`.

`subtotalCents` = the sum of line totals at the charged prices; `totalCents` = `subtotalCents - discountCents`.
Each line snapshots `listPriceCentsSnapshot` (the product price at sale time), `unitPriceCentsSnapshot`
(what was charged) and, server-side only, the unit cost. The cost is never returned to buyers.

Stock is validated for **every** line item (duplicate `productId`s aggregated first) before any
of them are deducted — a multi-item sale either fully succeeds or fully fails.

**Response:** `SaleRead` (201). **Errors:** `404` (`BuyerNotFoundError`, `ProductNotFoundError`),
`400` (`InsufficientStockError`, `InvalidDiscountError`).

`POST /products/{id}/quick-sell` takes the same optional `unitPriceCents`. The offline quick-sell
queue stores the whole payload, so a replayed sale charges the agreed price.

## `POST /sales/{saleId}/void` and `POST /sales/{saleId}/refund`

Body: `{ reason?: string }`. Both work only on a `completed` sale (otherwise `409`), return
every line's pieces to stock through `apply_stock_change` (reasons `void` / `refund`, with the
`sale_id`), and set `status`, `statusChangedAt` and `statusReason` in one transaction.

- **Void** means the sale was entered by mistake. It is excluded from every metric.
- **Refund** means a real sale came back. It counts in gross sales and is subtracted as `refundsCents`.

Partial refunds are not supported. Response: `SaleRead`.

## `POST /sales/{saleId}/proof`

Seller-only, multipart `file` (JPEG/PNG/WebP). Attaches or replaces the seller's photo of a walk-in
customer's digital payment confirmation, stored privately like a buyer's screenshot and returned as
`paymentProofUrl`. Only for `completed` `walk_in` sales (`409` otherwise, and `409` for cash); `404`
for another seller's sale; `400` for a bad image. The frontend calls it right after `POST /sales`
when the seller took a photo on the QR screen. A failed upload never undoes the sale, and the
receipt screen offers **Add payment photo** to try again. Response: `SaleRead`.

## `POST /sales/{saleId}/confirm-payment` and `POST /sales/{saleId}/reject`

Seller actions on a buyer's `pending_payment` order (`409` for any other status).

- **Confirm payment** (no body) sets `status = completed`. From then on the sale counts in every
  metric, linked to the buyer. A non-cash order needs a `paymentProofUrl` first (`409` otherwise);
  a cash order is confirmed when the cash is handed over.
- **Reject** (body `{ reason?: string }`) sets `status = cancelled` and returns the reserved stock
  with `cancel` movements. Cancelled orders are excluded from every metric.

`GET /sales?status=pending_payment` lists the orders waiting for confirmation. `SaleRead` and
`SaleListItem` carry `paymentProofUrl` / `proofSubmittedAt`; the public receipt never does.

In the frontend, sellers approve orders under **New Sale → Buyer Account**
(`/sales?path=account`, with `&order=<id>` for one order, rendered by
`features/sales/OrderApproval.jsx`). That tab shows a count of pending orders, the dashboard's
`PendingOrdersBanner` links to it, and the chat [order card](messaging-service.md#order-cards)
for each order does too. Sellers can't add items to an order. Walk-in is the only kind of sale
they ring up themselves.

## `GET /sales`

List/filter the caller's sales.

**Query params:** `range` (`today`\|`week`\|`month`\|`custom`), `start`/`end` (required if
`range=custom`), `saleType`, `paymentMethod`, `buyerId`, `status`, `page`, `pageSize` (max 100).

**Response:** `SaleListResponse` — `{ items: SaleListItem[], total, page, pageSize }`. Each item
includes a resolved `buyerName` (looked up separately, not stored on the sale) and `itemCount`.

The seller's **Transactions** page (`/transactions`, `features/sales/TransactionsPage.jsx`) lists
these by date range. Its **Delete transaction** action calls the void endpoint, so the sale stays
listed, marked Voided.

## `GET /sales/receipt/{receiptCode}`

**Public, no auth.** What the printed/QR receipt (`/r/:receiptCode` in the frontend) resolves to.
Returns only public-safe fields — no buyer/seller IDs, emails, or phone numbers.

**Response (`PublicReceipt`):** `businessName`, `receiptCode`, `saleType`, `items[]` (name,
quantity, unitType, unitPriceCents, lineTotalCents — all read from the `sale_items` **snapshot**
columns, not the live product), `subtotalCents`, `discountCents`, `totalCents`, `status` (never
the seller's `statusReason`), `paymentMethod`, `createdAt`.

## `GET /sales/{saleId}`

Fetch one of the caller's sales by ID. 404 if not found or not owned. Response: `SaleRead`.

---

## Buyer-facing ordering & receipts (`app/routers/catalog.py`)

These endpoints live in the catalog router file but call directly into
`services.sales.create_sale` / read `Sale` rows, so they belong to this service conceptually.

### `POST /catalog/products/{productId}/order`

Auth: `require_buyer`. Places an itemized, buyer-linked order for a single product — the buyer
version of ringing up a sale. Internally calls `create_sale(sale_type=ITEMIZED, buyer_id=buyer.id,
items=[(product_id, quantity)], status=PENDING_PAYMENT)`. Stock is deducted (reserved) right away,
but the sale counts in no metric until the seller confirms payment (see
[Data Flow](../architecture/data-flow.md)).

**Request (`BuyRequest`):** `{ quantity: int (>0), paymentMethod }`
**Response:** `SaleRead` (201, `status: "pending_payment"`). **Errors:** `400` (`InsufficientStockError`), `404` (product not found).

A **cash** order is reviewable straight away, so placing one also posts an
[order card](messaging-service.md#order-cards) into the buyer's chat with the seller.

### `GET /me/orders/{saleId}`

Auth: `require_buyer`, scoped to the buyer's own orders (`404` otherwise). **Response:**
`BuyerOrderRead` — `SaleRead` plus `sellerName` and the seller's `payoutAccounts`, so the order
page can show where to pay.

### `POST /me/orders/{saleId}/proof`

Multipart `file` (JPEG/PNG/WebP). Attaches or replaces the payment screenshot on a pending,
non-cash order and sets `paymentProofUrl` / `proofSubmittedAt`. Each upload posts an
[order card](messaging-service.md#order-cards) for the seller. **Errors:** `400` (not an
image), `404` (not this buyer's order), `409` (order no longer pending, or a cash order).

### `POST /me/orders/{saleId}/cancel`

The buyer withdraws a pending order: status → `cancelled`, stock returned with `cancel`
movements. `409` if it is no longer pending.

### `GET /me/receipts`

Auth: `require_buyer`. Paginated purchase history for the current buyer.

**Query:** `page`, `pageSize`. **Response:** `BuyerReceiptListResponse` — each item includes
`sellerName`, `saleType`, `totalCents`, `status`, `paymentMethod`, `receiptCode`, `createdAt`, `itemCount`.

---

## Related: analytics endpoints (`app/routers/analytics.py`)

Read-only aggregations over the same `sales`/`products` tables. Prefix `/analytics`, auth
`require_seller`. The service is the package `app/services/analytics/`: `sales.py` (sales and
profit), `inventory.py` (stock health and demand data), `forecast.py` (pure forecasting math)
and `insights.py` (rules).

**Business days.** "Today", ranges and every daily, weekday or hourly bucket use local calendar
days in `settings.BUSINESS_TIMEZONE` (default `Asia/Manila`), via `app/core/business_time.py`.
Presets: `today`, `week` (the last 7 local days, including today) and `month` (the last 30).
`range=custom` takes `start`/`end` as local `YYYY-MM-DD` dates, both inclusive.

**Status rules.** Voided, `pending_payment` and `cancelled` sales are invisible. Refunded sales count in gross sales and come back out as
`refundsCents`. Net sales, transactions, units and profit come from completed sales only. COGS
comes from the `sale_items` cost snapshots. `costCoveragePct` is the share of net sales that has a
known cost, so a margin based on partial data is labelled as partial.

| Method & path | Description |
|---|---|
| `GET /analytics/summary` | Today's sale count/net sales, low-stock count, week-over-week change %. |
| `GET /analytics/overview?range=&start=&end=` | `current` and `previous` (the equal-length window just before) period metrics: gross sales at list price, price adjustments, discounts, refunds, net sales, transactions, units, average sale, COGS, gross profit, margin %, cost coverage %, plus `changePct`. Gross − adjustments − discounts − refunds = net. |
| `GET /analytics/top-products?range=&limit=&sort=` | Top products from completed sales, `sort=revenue\|quantity\|profit`. Profit is per line, before sale-level discounts. |
| `GET /analytics/sales-trend?range=&granularity=` | Net sales, sale count and gross profit per `day`\|`week`\|`month` bucket, zero-filled. |
| `GET /analytics/patterns?weeks=8` | Average net sales and transactions per local weekday (Monday = 0) and per local hour. |
| `GET /analytics/inventory` | Per product: 7- and 30-day daily averages, days of stock left, suggested reorder (pieces for the next 14 days plus 3 days of safety stock), 30-day turnover, stock value at cost, and `status` (`out_of_stock`, `stockout_risk` = 7 days or less, `low`, `slow_moving` = no sale in 14 days, `overstocked` = more than 60 days, `healthy`). |
| `GET /analytics/forecast` | `{ accuracyPct, weekdayAdjusted, weekdayFactors, items[] }`. Each item has `forecast7`/`forecast14`, `method` (`history`, `fallback` or `none`) and `confidence`. The rate is 0.6 × the 7-day average + 0.4 × the 30-day average, and products with fewer than 14 selling days use a low-confidence fallback. Weekday factors apply once the shop has 4 weeks of history. `accuracyPct` = 100 − WAPE of a backtest that forecasts last week from the data before it. |
| `GET /analytics/insights` | Rule-based `{ code, severity, action, params, productId }`. The frontend translates `code`/`action`; `params` carries the figures (camelCase keys). Rules: `stockout_risk`, `overstock`, `low_margin`, `below_cost`, `missing_cost`, `sales_spike`/`sales_drop` (yesterday against the same weekday over 4 weeks), and `emerging_bestseller`. At most 3 per rule. |
