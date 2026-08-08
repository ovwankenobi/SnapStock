# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A mobile-first POS and inventory app ("SnapStock" / Public Market POS) for sellers in public markets and small retail, with a companion buyer experience for digital orders, receipts, and messaging. Full product spec and phased build plan (including the reasoning behind schema decisions) is in [pos-system-build-plan.md](pos-system-build-plan.md) — read it when a change touches sales, stock, or receipts and the "why" isn't obvious from code.

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

Backend on port 6767, frontend on 5173, in separate terminals. Frontend's `apiClient` reads `VITE_API_URL` from `frontend/.env`; backend CORS reads `CORS_ORIGINS` from `backend/.env`.

## Architecture

### Backend layering

Routers → services → models, strictly. Business logic (stock math, receipt generation, sale aggregation) lives in `app/services/*.py`, never in routers. Routers handle auth deps, request/response schemas, and translating service exceptions (`InsufficientStockError`, `ProductNotFoundError`, `BuyerNotFoundError`, etc.) into `HTTPException`s.

- `app/models/` — SQLAlchemy models, one file per domain (`user`, `product`, `sale`, `stock_movement`, `conversation`). `mixins.py` provides `UUIDPkMixin`, `CreatedAtMixin`, `UpdatedAtMixin` — all tables use UUID PKs and UTC-aware timestamps via these.
- `app/schemas/` — Pydantic models. All response/request schemas extend `CamelModel` (`app/schemas/base.py`), which auto-converts `snake_case` ↔ `camelCase` at the API boundary (`alias_generator=to_camel`, `populate_by_name=True`, `from_attributes=True`). Never hand-roll camelCase field names — extend `CamelModel` and let it do the conversion.
- `app/core/deps.py` — `get_current_user`, `require_seller`, `require_buyer` FastAPI dependencies for auth/role gating. Every seller-scoped router endpoint takes `seller: User = Depends(require_seller)` and filters queries by `seller.id` — there is no separate ownership-check layer, so a missing filter is a data leak, not just a 403.
- `app/core/rate_limit.py` — shared `slowapi` `Limiter` instance, applied to auth endpoints via decorators + limits from `Settings` (`AUTH_REGISTER_RATE_LIMIT`, `AUTH_LOGIN_RATE_LIMIT`).

### Money, stock, and stock movements

- All money is integer cents (`*_cents` fields) — never floats.
- `Product.stock_pieces` is the single source of truth for stock and is **always** in individual pieces, regardless of `unit_type` (`piece` / `bundle` / `grams`). Selling `quantity` selling-units deducts `quantity * pieces_per_unit` pieces.
- All stock changes (`quick_sell`, itemized `create_sale`, restock) must go through `services/inventory.apply_stock_change`, which row-locks the product (`SELECT ... FOR UPDATE`), rejects changes that would drive stock negative (raising `InsufficientStockError`), and writes an append-only `stock_movements` audit row in the same transaction. Never mutate `stock_pieces` directly.
- `services/sales.create_sale` validates stock for **every** line item (aggregating duplicate `product_id`s first) before deducting any of them, so a multi-item sale either fully succeeds or fully fails.
- `sale_items` snapshots `product_name_snapshot` / `unit_price_cents_snapshot` / `unit_type_snapshot` at write time — past receipts must never change when a product is later edited or renamed.
- Products are soft-deleted (`is_active = false`) only; sales reference `product_id`, so hard deletes are never used.

### Sales model

Two `sale_type`s share one `sales`/`sale_items` schema: `walk_in` (no buyer, `buyer_id` nullable and null) and `itemized` (buyer required). Both deduct stock and count toward analytics identically — don't special-case one in shared aggregation/reporting code. `GET /sales/receipt/{receipt_code}` is the only public, unauthenticated sales endpoint (what the printed/QR receipt resolves to) and must only ever return the trimmed public-safe fields — no buyer/seller IDs, emails, or phone numbers.

### Frontend structure

```
src/
├── api/        # axios wrappers, one file per backend resource
├── features/   # auth, inventory, sales, dashboard, messages, buyer — feature-scoped pages + components
├── components/ # shared UI primitives (Badge, StatTile, QuantityStepper, etc.)
├── hooks/
└── lib/        # apiClient (axios + auth interceptor), i18n, offlineQueue, format helpers
```

- `lib/apiClient.js` attaches `Authorization: Bearer <token>` from `localStorage` on every request and redirects to `/login` on a 401 (except from the login/register endpoints themselves, to avoid a redirect loop on bad credentials).
- `lib/offlineQueue.js` queues quick-sell requests in `localStorage` when a request fails with a *network* error (no response, not a server rejection) and replays them on reconnect, stopping at the first entry that still fails on the network but dropping entries the server actively rejects (e.g. stock now gone). This is the highest-value resilience feature for the target environment (unreliable market wifi) — preserve this network-error-vs-rejection distinction in any related changes.
- `lib/i18n/` is a minimal two-JSON-dictionary (`en.json`, `tl.json`) lookup with dotted-key access and fallback to English — not a full i18n library. New user-facing strings should go through `translate()`/the `t()` helper rather than being hardcoded, in both dictionaries.
- Routing/role-gating is centralized in `App.jsx` via `<ProtectedRoute role="seller"|"buyer">`; `/r/:receiptCode` (public receipt) and `/login`/`/register` are the only unauthenticated routes.
- TanStack Query is used for all server state; mutations call `invalidateQueries` on the relevant list query rather than manually patching cache.

### Naming convention at the API boundary

Python/SQL is `snake_case`; the wire format and all frontend code is `camelCase`. The conversion happens automatically via `CamelModel` on the backend — never introduce manual camelCase↔snake_case mapping in routers, services, or frontend API wrappers.
