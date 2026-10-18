# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A mobile-first POS and inventory app ("SnapStock" / Public Market POS) for sellers in public markets and small retail, with a companion buyer experience for digital orders, receipts, and messaging. Full product spec and phased build plan (including the reasoning behind schema decisions) is in [pos-system-build-plan.md](pos-system-build-plan.md) — read it when a change touches sales, stock, or receipts and the "why" isn't obvious from code.

**Design mobile-first.** This is a mobile website first and foremost — sellers use it on phones at their stalls. Design and build every screen for phone width (~360–430px) first, then enhance for larger screens with `min-width` media queries. Use touch-sized targets (≥44px), keep primary actions within thumb reach, avoid hover-only interactions, prefer native mobile inputs (e.g. `<input type="date">`, `inputmode="numeric"`), and never allow horizontal page scroll. Desktop layouts are a secondary enhancement, not the baseline.

**Stack:** FastAPI · SQLAlchemy · Alembic · PostgreSQL · JWT auth (`python-jose`) · `slowapi` rate limiting — React 19 (Vite) · React Router · TanStack Query · Axios · Recharts · `qrcode.react`.

## Commands

### Backend (`backend/`)

```bash
.venv/Scripts/activate                        # Windows; source .venv/bin/activate on macOS/Linux
uvicorn app.main:app --reload --port 6767      # run
pytest                                          # run all tests
pytest tests/test_inventory.py                  # run one file
pytest tests/test_inventory.py::test_name -v    # run one test
alembic revision --autogenerate -m "message"    # new migration
alembic upgrade head                            # apply migrations
alembic downgrade base                          # reverse all
python scripts/seed.py                          # seed demo data
```

Tests require a live Postgres on `localhost:5432` (user/pass `postgres`/`postgres`). `tests/conftest.py` auto-creates a separate `pos_system_test` database, applies `Base.metadata.create_all` for the session, and truncates all tables between tests — no manual test-DB setup needed, but Postgres itself must be running.

### Frontend (`frontend/`)

```bash
npm run dev      # dev server at http://localhost:5173
npm run build
npm run lint      # oxlint, not eslint
```

### Running both

Backend on port 6767, frontend on 5173, in separate terminals. `frontend/.env` sets `VITE_API_URL=/api/v1` (relative), and `vite.config.js` proxies `/api` and `/uploads` to `127.0.0.1:6767` with `server.host: true`, so phones on the LAN only need the Vite port. Keep API and upload URLs relative to work with the proxy (`API_ORIGIN` in `lib/apiClient.js` resolves against `window.location`). Backend CORS (`CORS_ORIGINS` in `backend/.env`) only matters if `VITE_API_URL` is made absolute. Local Postgres: `docker compose up -d db` from the repo root.

## Architecture

### Backend layering

Routers → services → models, strictly. Business logic (stock math, receipt generation, sale aggregation) lives in `app/services/*.py`, never in routers. Routers handle auth deps, request/response schemas, and translating service exceptions (`InsufficientStockError`, `ProductNotFoundError`, `BuyerNotFoundError`, etc.) into `HTTPException`s.

- `app/models/` — SQLAlchemy models, one file per domain (`user`, `product`, `product_cost`, `sale`, `stock_movement`, `conversation`, `payout_account`). `mixins.py` provides `UUIDPkMixin`, `CreatedAtMixin`, `UpdatedAtMixin` — all tables use UUID PKs and UTC-aware timestamps via these.
- `app/schemas/` — Pydantic models. All response/request schemas extend `CamelModel` (`app/schemas/base.py`), which auto-converts `snake_case` ↔ `camelCase` at the API boundary (`alias_generator=to_camel`, `populate_by_name=True`, `from_attributes=True`). Never hand-roll camelCase field names — extend `CamelModel` and let it do the conversion.
- `app/core/deps.py` — `get_current_user`, `require_seller`, `require_buyer` FastAPI dependencies for auth/role gating. Every seller-scoped router endpoint takes `seller: User = Depends(require_seller)` and filters queries by `seller.id` — there is no separate ownership-check layer, so a missing filter is a data leak, not just a 403.
- `app/core/rate_limit.py` — shared `slowapi` `Limiter` instance, applied to auth endpoints via decorators + limits from `Settings` (`AUTH_REGISTER_RATE_LIMIT`, `AUTH_LOGIN_RATE_LIMIT`).
- `app/services/uploads.py` — `validate_image` / `save_image` (JPEG/PNG/WebP into `UPLOAD_DIR`, served at `/uploads`). Use it for every upload: product photos, payout QR codes, payment screenshots, and both search-by-image endpoints.
- Seller payout accounts (`/seller/payout-accounts`, `services/payouts.py`, `models/payout_account.py`) belong to `seller_profiles` and reuse the `payment_method` enum without `cash`. The first account becomes the default, and setting another as default clears the old one. `features/payouts/PaymentMethodPicker.jsx` always offers Cash, greys out methods the seller has no account for, and shows the matching QR, both in the buyer's `BuySheet` and on the seller's walk-in `PaymentSheet`.

### Money, stock, and stock movements

- All money is integer cents (`*_cents` fields) — never floats.
- `Product.stock_pieces` is the single source of truth for stock and is **always** in individual pieces, regardless of `unit_type` (`piece` / `bundle` / `measure`). Selling `quantity` selling-units deducts `quantity * pieces_per_unit` pieces.
- `measure` products have a seller-chosen `unit_label` (kg, yd, m, …) and store `stock_pieces`, `low_stock_threshold`, and every wire `quantity` in **thousandths of that unit** (`pieces_per_unit` is always 1); `price_cents` is per whole unit. Always compute line totals with `services/inventory.line_total_cents` (frontend mirror: `lineTotalCents` in `lib/format.js`), never `quantity * price_cents`.
- All stock changes (`quick_sell`, itemized `create_sale`, restock) must go through `services/inventory.apply_stock_change`, which row-locks the product (`SELECT ... FOR UPDATE`), rejects changes that would drive stock negative (raising `InsufficientStockError`), and writes an append-only `stock_movements` audit row in the same transaction. Never mutate `stock_pieces` directly.
- `services/sales.create_sale` validates stock for **every** line item (aggregating duplicate `product_id`s first) before deducting any of them, so a multi-item sale either fully succeeds or fully fails.
- `sale_items` snapshots `product_name_snapshot` / `unit_price_cents_snapshot` / `unit_type_snapshot` / `unit_label_snapshot` at write time — past receipts must never change when a product is later edited or renamed.
- Products are soft-deleted (`is_active = false`) only; sales reference `product_id`, so hard deletes are never used.
- Sellers can edit a line's price during checkout or quick-sell (`unitPriceCents`). `unit_price_cents_snapshot` is what was charged and `list_price_cents_snapshot` is the product price at that moment. The product's own price never changes. Sales carry `subtotal_cents`, a sale-level `discount_cents`, and `total_cents = subtotal - discount`. Build lines with `services/inventory.build_sale_item` so all of these, plus the cost snapshot, are filled in.
- `products.cost_cents` changes only through `services/inventory.set_product_cost`, which appends to `product_cost_history`. Profit and COGS always come from the `sale_items` cost snapshots (`unit_cost_cents_snapshot` / `cost_total_cents`), never from the live product cost, so editing a cost never rewrites past profit.
- `sales.status` is `completed`, `voided`, `refunded`, `pending_payment` or `cancelled`. Void and refund go through `services/sales.void_sale` / `refund_sale`, which return the stock with `void` / `refund` movements. Analytics count only `completed` sales (plus `refunded` for gross sales / refunds) — never filter with `!= voided`, because pending and cancelled orders must stay out too. Refunded sales count in gross sales and are subtracted as refunds. Net sales, units and profit use completed sales only.
- Buyer orders (`POST /catalog/products/{id}/order`) are created `pending_payment`: stock is deducted (reserved) but nothing counts yet. The buyer uploads a payment screenshot (`services/sales.submit_payment_proof`; not for cash orders), then the seller calls `confirm_payment` (→ `completed`, linked to the buyer) or `reject_order`; the buyer can `cancel_order_by_buyer`. Reject/cancel → `cancelled`, with stock returned through a `cancel` movement. `payment_proof_url` is for the seller and buyer only and must never appear on the public receipt.
- Sellers approve online orders under New Sale → Buyer Account (`/sales?path=account&order=<id>`, `features/sales/OrderApproval.jsx`). That tab is approval-only: sellers can't add items there, and walk-in is the only sale they ring up themselves. When an order becomes reviewable (a cash order is placed, or proof is uploaded), `services/messages.post_order_card` posts a chat message from the buyer with `messages.sale_id` set. `GET /conversations/{id}/messages` attaches the live `order` summary, and `features/messages/OrderCardBubble.jsx` renders it as a card that links to the approval screen.
- Analytics days are local business days in `settings.BUSINESS_TIMEZONE` (Asia/Manila), never UTC. Use `app/core/business_time.py` (`resolve_range`, `local_day_expr`, …) for "today", ranges and daily/weekday/hourly buckets.

### Sales model

Two `sale_type`s share one `sales`/`sale_items` schema: `walk_in` (no buyer, `buyer_id` nullable and null) and `itemized` (buyer required). Both deduct stock and count toward analytics identically — don't special-case one in shared aggregation/reporting code. `GET /sales/receipt/{receipt_code}` is the only public, unauthenticated sales endpoint (what the printed/QR receipt resolves to) and must only ever return the trimmed public-safe fields — no buyer/seller IDs, emails, or phone numbers.

### Frontend structure

```
src/
├── api/        # axios wrappers, one file per backend resource
├── features/   # auth, inventory, sales, analytics, dashboard, messages, payouts, buyer — feature-scoped pages + components
├── components/ # shared UI primitives (Badge, StatTile, QuantityStepper, etc.)
├── hooks/
└── lib/        # apiClient (axios + auth interceptor), i18n, offlineQueue, format helpers
```

- `lib/apiClient.js` attaches `Authorization: Bearer <token>` from `localStorage` on every request and redirects to `/login` on a 401 (except from the login/register endpoints themselves, to avoid a redirect loop on bad credentials).
- `lib/offlineQueue.js` queues quick-sell requests in `localStorage` when a request fails with a *network* error (no response, not a server rejection) and replays them on reconnect, stopping at the first entry that still fails on the network but dropping entries the server actively rejects (e.g. stock now gone). This is the highest-value resilience feature for the target environment (unreliable market wifi) — preserve this network-error-vs-rejection distinction in any related changes. Right now nothing adds to the queue: `features/inventory/QuickSellSheet.jsx` isn't mounted, and walk-in sales go through the New Sale cart (`POST /sales`), which isn't queued. `InventoryPage` only drains old entries.
- `lib/i18n/` is a minimal two-JSON-dictionary (`en.json`, `tl.json`) lookup with dotted-key access and fallback to English — not a full i18n library. New user-facing strings should go through `translate()`/the `t()` helper rather than being hardcoded, in both dictionaries. `t(key, params)` fills `{name}` placeholders.
- `/analytics` (`features/analytics/`) is the Analytics hub: an insights feed plus Sales, Profit, Stock and Forecast tabs, selected with `?tab=`. The seller's receipt list is its own nav item, Transactions (`/transactions`, `features/sales/TransactionsPage.jsx`); the old `/sales/history` redirects there. Insights arrive as `code` + `params` and are translated in `insightText.js`.
- Routing/role-gating is centralized in `App.jsx` via `<ProtectedRoute role="seller"|"buyer">`; `/r/:receiptCode` (public receipt) and `/login`/`/register` are the only unauthenticated routes.
- TanStack Query is used for all server state; mutations call `invalidateQueries` on the relevant list query rather than manually patching cache.

### Naming convention at the API boundary

Python/SQL is `snake_case`; the wire format and all frontend code is `camelCase`. The conversion happens automatically via `CamelModel` on the backend — never introduce manual camelCase↔snake_case mapping in routers, services, or frontend API wrappers.
