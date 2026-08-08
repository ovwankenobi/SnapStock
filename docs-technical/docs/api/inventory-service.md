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

## `GET /products`

List/search the caller's products.

**Query params:** `search` (name substring), `category`, `stock_status`
(`in_stock` | `low` | `out`), `page` (default 1), `pageSize` (default 20, max 100).

**Response:** `ProductListResponse` — `{ items: ProductRead[], total, page, pageSize }`.

## `POST /products`

Create a product. `stock_pieces = 0` initially; if `stockPieces > 0` is supplied, it's applied via
`apply_stock_change` with reason `initial` (so it still generates an audit row).

**Request (`ProductCreate`):**

| Field | Type | Notes |
|---|---|---|
| `name` | string | required |
| `description` | string \| null | |
| `priceCents` | int | required, > 0 |
| `unitType` | `piece` \| `bundle` \| `grams` | required |
| `piecesPerUnit` | int | default 1, ≥ 1. Must be 1 unless `unitType = bundle` (400 otherwise) |
| `stockPieces` | int | default 0, ≥ 0 |
| `lowStockThreshold` | int | default 10, ≥ 0 |
| `category` | string \| null | |

**Response:** `ProductRead` (201).

## `GET /products/{productId}`

Fetch one owned product. 404 if not found, not owned, or soft-deleted (`is_active = false`).

## `PATCH /products/{productId}`

Partial update (`ProductUpdate` — same fields as create, all optional, `exclude_unset` applied).
Does **not** accept `stockPieces` — stock is only ever changed via quick-sell, sale, or restock.

## `DELETE /products/{productId}`

Soft-delete only: sets `is_active = false`. Returns `204`. Products are never hard-deleted because
`sale_items.product_id` references them and past receipts must keep resolving.

## `POST /products/{productId}/quick-sell`

The single-tap walk-in sale path (see [Data Flow](../architecture/data-flow.md)). Creates a
`walk_in` sale with `buyer_id = null` and deducts stock in one transaction.

**Request (`QuickSellRequest`):** `{ quantity: int (>0), paymentMethod: cash|gcash|maya|bank_transfer|other }`

**Response (`QuickSellResult`):** `{ product: ProductRead, saleId, receiptCode, totalCents }`

**Errors:** `400` if `stock_pieces − quantity × piecesPerUnit < 0` (`InsufficientStockError`).

## `POST /products/{productId}/restock`

Increases stock. Writes a `stock_movements` row with reason `restock`.

**Request (`RestockRequest`):** `{ quantity: int (>0), note?: string }`

**Response:** `ProductRead`.

## `POST /products/{productId}/photo`

Multipart upload (`file`), JPEG/PNG/WebP only. Saves to `UPLOAD_DIR` under
`{productId}_{random8hex}{ext}` and sets `photoUrl` to `/uploads/{filename}` (served statically —
see `app.mount("/uploads", ...)` in `app/main.py`).

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
