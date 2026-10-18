# Inventory Service

Owns `Product` data and all stock changes. Router: `app/routers/inventory.py` (prefix
`/products`), business logic in `app/services/inventory.py`. All endpoints below require
`Authorization: Bearer <token>` and `require_seller` (the caller must own the product — enforced
by filtering on `seller.id`, not a separate permission check).

Money fields are integer cents (`priceCents`). All request/response bodies are camelCase on the
wire (Pydantic `CamelModel` auto-converts to/from the backend's snake_case).

## `GET /products/low-stock`

Returns products where `stock_pieces <= low_stock_threshold`, ordered by `stock_pieces` ascending.
Response: `list[ProductRead]`.

## `GET /products/categories` and `DELETE /products/categories`

`GET` returns the distinct, non-empty `category` values across the caller's active products,
sorted case-insensitively (`list[str]`). There is no categories table: a category exists while at
least one product uses it. The frontend's `CategorySelect` lets sellers pick one, type a new one,
or delete one.

`DELETE /products/categories?name=<category>` clears that category from every active product of
the caller (sets it to `null`). Returns `204`.

## `GET /products`

List/search the caller's products.

**Query params:** `search` (name substring), `category`, `stock_status`
(`in_stock` | `low` | `out`), `page` (default 1), `pageSize` (default 20, max 100).

**Response:** `ProductListResponse` — `{ items: ProductRead[], total, page, pageSize }`.

`ProductRead` includes `costCents` (seller-only, `null` if unknown) and a computed `stockStatus`
(`in_stock` | `low` | `out`).

## `POST /products`

Create a product. `stock_pieces = 0` initially; if `stockPieces > 0` is supplied, it's applied via
`apply_stock_change` with reason `initial` (so it still generates an audit row).

**Request (`ProductCreate`):**

| Field | Type | Notes |
|---|---|---|
| `name` | string | required |
| `description` | string \| null | |
| `priceCents` | int | required, > 0 |
| `costCents` | int \| null | ≥ 0. What one selling unit costs the seller. Used for profit; recorded in `product_cost_history` |
| `unitType` | `piece` \| `bundle` \| `measure` | required |
| `unitLabel` | string \| null | ≤ 16 chars. Required for `measure` (422 otherwise), e.g. `kg`, `yd`; ignored/cleared for other types |
| `piecesPerUnit` | int | default 1, ≥ 1. Must be 1 unless `unitType = bundle` (400 otherwise) |
| `stockPieces` | int | default 0, ≥ 0. Thousandths of the unit for `measure` |
| `lowStockThreshold` | int | default 10, ≥ 0. Thousandths of the unit for `measure` |
| `category` | string \| null | |

**Response:** `ProductRead` (201).

## `GET /products/{productId}`

Fetch one owned product. 404 if not found, not owned, or soft-deleted (`is_active = false`).

## `PATCH /products/{productId}`

Partial update (`ProductUpdate` — same fields as create, all optional, `exclude_unset` applied).
Does **not** accept `stockPieces` — stock is only ever changed via quick-sell, sale, or restock.
A changed `costCents` goes through `set_product_cost` (source `manual`), which appends a
`product_cost_history` row. Past profit is unaffected, because sales keep their own cost snapshot.

## `DELETE /products/{productId}`

Soft-delete only: sets `is_active = false`. Returns `204`. Products are never hard-deleted because
`sale_items.product_id` references them and past receipts must keep resolving.

## `POST /products/{productId}/quick-sell`

The single-tap walk-in sale path (see [Data Flow](../architecture/data-flow.md)). Creates a
`walk_in` sale with `buyer_id = null` and deducts stock in one transaction.

**Request (`QuickSellRequest`):** `{ quantity: int (>0), paymentMethod: cash|gcash|maya|bank_transfer|other, unitPriceCents?: int }`

**Response (`QuickSellResult`):** `{ product: ProductRead, saleId, receiptCode, totalCents }`

**Errors:** `400` if `stock_pieces − quantity × piecesPerUnit < 0` (`InsufficientStockError`).

!!! note
    The current frontend has no quick-sell screen: `QuickSellSheet.jsx` and
    `api/products.quickSellProduct` exist but nothing mounts or calls them. Walk-in sales go
    through the New Sale cart (`POST /sales`). The endpoint and its tests are still in place.

## `POST /products/{productId}/restock`

Increases stock. Writes a `stock_movements` row with reason `restock`.

**Request (`RestockRequest`):** `{ quantity: int (>0), note?: string, unitCostCents?: int }`.
`unitCostCents` is the cost per selling unit for this delivery. If given, it becomes the
product's cost (`product_cost_history` source `restock`). If omitted, the cost stays the same.

**Response:** `ProductRead`.

## `POST /products/restock`

Restock several products in one go (the **Restock Items** screen, `RestockPicker.jsx`).

**Request (`BulkRestockRequest`):** `{ items: { productId, quantity (>0), unitCostCents? }[] (min 1), note?: string }`

Duplicate `productId`s are summed. Every product is resolved before any stock changes, so one
unknown or foreign ID fails the whole batch with `404`. Each product gets its own `restock`
movement, plus a cost update when `unitCostCents` is given. **Response:** `list[ProductRead]`.

## `POST /products/search-by-image`

Seller-side mirror of the catalog photo search, scoped to the caller's own products. Multipart
`file` (JPEG/PNG/WebP) plus a `query` form field (min length 1). **Stage 1:** the photo is
validated but not analyzed, and results are a keyword search on `query` (first 20 matches).

**Response (`ProductImageSearchResponse`):** `{ query, results: { product: ProductRead, confidence: null }[] }`.
**Errors:** `400` (not an image).

## `POST /products/{productId}/photo`

Multipart upload (`file`), JPEG/PNG/WebP only. Saves to `UPLOAD_DIR` under
`{productId}_{random8hex}{ext}` and sets `photoUrl` to `/uploads/{filename}` (served statically —
see `app.mount("/uploads", ...)` in `app/main.py`). Validation and saving live in
`app/services/uploads.py` (`validate_image`, `save_image`), which payout QR codes and payment
screenshots use as well.

**Response:** `ProductRead`.

---

## Buyer-facing catalog reads (`app/routers/catalog.py`)

Read-only browsing of the same `Product` data, no auth required. Prefix: none (mounted at
`/api/v1` root, tag `catalog`).

| Method & path | Description |
|---|---|
| `GET /catalog/products` | List active products across **all** sellers. Query: `search`, `category`, `sellerId`, `page`, `pageSize`. Returns `CatalogProductListResponse` (includes `sellerName`, `stockStatus`, but no seller/internal IDs beyond `sellerId`). |
| `GET /catalog/products/{productId}` | Single product, `CatalogProductRead`. 404 if missing. |
| `GET /catalog/sellers/{sellerId}` | Seller's public profile + active listings, `CatalogSellerRead`. |
| `POST /catalog/search-by-image` | Multipart `file` + `query` form field. **Stage 1 stub**: the photo is accepted (validated as JPEG/PNG/WebP) but not analyzed — it's a shortcut into a keyword search on `query`. See [Deferred Features](../deferred-features.md). Returns `ImageSearchResponse` with `confidence: null` on every result. |

Ordering (`POST /catalog/products/{productId}/order`) and buyer receipts (`GET /me/receipts`) are
documented in [Sales Service](sales-service.md), since they're powered by the sales service, not
inventory.
