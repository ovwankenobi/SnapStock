# Public Market POS — Build Plan

A phased implementation spec for a mobile-first POS + inventory system serving small/public-market sellers and their customers.

**Stack:** React (Vite) · FastAPI · PostgreSQL (SQLAlchemy + Alembic)

**How to use this document:** Each phase below is self-contained. Hand one phase at a time to an AI coding assistant along with the "Shared Context" section. Do not skip ahead — later phases assume earlier ones are complete and tested.

---

## Shared Context

> Include this section verbatim at the start of every phase prompt.

### Product summary

A POS and inventory app for sellers in public markets and small retail (sari-sari stores, market stalls). Two roles:

- **Seller** — manages inventory, records sales, views analytics, messages buyers.
- **Buyer** — browses products, buys, receives digital receipts, messages sellers.

### The three constraints that shape the design

1. **Not every customer is a digital user.** Many walk-in customers have no phone, no account, and will never scan a QR code. A sale must be recordable and a receipt issuable without any buyer identity. Therefore `sales.buyer_id` is **nullable**.

2. **Sellers won't scan barcodes.** Public market sellers are fast and hands-busy. Inventory deduction must be a 1–2 tap manual action ("quick sell"), not a scan-driven flow. Automatic deduction happens only for digital orders.

3. **Products sell by piece, by grams *and* by bundle.** A product has a `unit_type` (`piece`, `grams`, or `bundle`) and a `pieces_per_unit` count. Selling one bundle or grams deducts `pieces_per_unit` from stock. The schema absorbs this so the UI never forces a choice.

### Two sale types

| | `itemized` | `walk_in` |
|---|---|---|
| Buyer account | Required (`buyer_id` set) | None (`buyer_id` null) |
| Line items | Full `sale_items` rows | Optional / aggregate only |
| Receipt | Digital, QR-linked, in buyer's app | Printed or shown on seller screen |
| Stock deduction | Automatic on order or Manual via quick sell | Manual via quick sell |

Both types deduct stock, both count toward totals and analytics.

### Conventions

- **Money:** store as integer minor units (centavos). Never floats. Field names end in `_cents`.
- **Timestamps:** UTC, timezone-aware, `created_at` / `updated_at` on every table.
- **IDs:** UUID primary keys.
- **API:** REST, JSON, `/api/v1` prefix. Plural resource nouns.
- **Errors:** FastAPI `HTTPException` with a consistent `{"detail": "..."}` body.
- **Naming:** `snake_case` in Python and SQL, `camelCase` in TypeScript. Convert at the API boundary using Pydantic aliases.

### Target repo layout

```
pos-system/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic models
│   │   ├── routers/         # one file per feature
│   │   ├── services/        # business logic (stock math, receipts)
│   │   └── core/            # auth, security, dependencies
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/             # fetch wrappers, one file per resource
    │   ├── features/
    │   │   ├── auth/
    │   │   ├── inventory/
    │   │   ├── sales/
    │   │   ├── messages/
    │   │   └── buyer/
    │   ├── components/      # shared UI primitives
    │   ├── hooks/
    │   ├── lib/
    │   └── App.jsx
    └── package.json
```

---

## Phase 0 — Scaffolding

**Goal:** Both servers run, talk to each other, and a health check passes end to end.

### Instructions

1. Create the repo layout above.

2. **Backend:**
   - `requirements.txt`: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pydantic-settings`, `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`, `pytest`, `httpx`.
   - `app/config.py`: a `Settings` class using `pydantic-settings` reading `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ORIGINS`, `UPLOAD_DIR`.
   - `app/database.py`: SQLAlchemy engine, `SessionLocal`, declarative `Base`, and a `get_db()` dependency that yields and closes a session.
   - `app/main.py`: FastAPI app, CORS middleware reading origins from settings, and `GET /api/v1/health` returning `{"status": "ok"}`.
   - Initialize Alembic pointed at `Base.metadata`.

3. **Frontend:**
   - Scaffold with Vite React template.
   - Install: `react-router-dom`, `@tanstack/react-query`, `axios`.
   - `.env`: `VITE_API_URL=http://localhost:6767/api/v1`
   - `src/lib/apiClient.js`: an axios instance with `baseURL` from env, plus a request interceptor that attaches `Authorization: Bearer <token>` when a token exists in storage, and a response interceptor that redirects to login on 401.
   - `src/App.jsx`: React Router with a placeholder route per screen, wrapped in a `QueryClientProvider`.

4. Write a `README.md` with setup and run commands for both halves.

### Done when

- `uvicorn app.main:app --reload` serves the health endpoint.
- `npm run dev` loads, and a temporary component successfully fetches `/health` with no CORS error in the console.

---

## Phase 0.5 — Design integration

**Goal:** The seven Claude Design mockups (Login/role-select, Seller dashboard, Inventory, Checkout/receipt, Sales history, Messages, Buyer home) become reusable React components — not code that gets used as-is.

Claude Design typically exports each screen as a single self-contained block of markup with hardcoded sample data. Treat it as a visual reference, not final production code. Do this once, before Phase 3, so every later phase has real components to plug data into instead of building UI from scratch.

### Instructions

1. **Export raw.** Pull each screen's exported code into a scratch folder, unmodified: `frontend/src/_design/<ScreenName>.jsx` (or `.html` if that's the export format). Do not refactor yet.

2. **Convert HTML to JSX, if needed.** If the export is plain HTML rather than JSX, run this pass first:

   | HTML | JSX |
   |---|---|
   | `class="..."` | `className="..."` |
   | `<img src="...">` | `<img src="..." />` (self-close all void tags) |
   | `for="..."` on `<label>` | `htmlFor="..."` |
   | `onclick="doThing()"` | `onClick={doThing}` |
   | inline `style="color: red"` | `style={{ color: "red" }}` (camelCase keys, object not string) |
   | `<!-- comment -->` | `{/* comment */}` |
   | `<svg stroke-width="2">` | `<svg strokeWidth="2">` (SVG attrs go camelCase too) |

3. **Find the seams.** In each screen, identify: anything inside a `.map()`, anything repeated across two or more screens, and anything with its own conditional styling logic (a status badge, a stock indicator). Each of these is a component boundary.

4. **Extract bottom-up.** Pull the smallest pieces first into `src/components/` (shared primitives — badges, buttons, avatars) and `src/features/<feature>/` (feature-specific pieces — `ProductCard`, `ReceiptView`, `ConversationRow`). While extracting, rename hardcoded sample fields to match the API contract in this document (e.g. `price` → `priceCents`, `stock` → `stockPieces`, add the `stockStatus` derived field rather than recomputing it client-side).

5. **Rebuild each page as a thin shell.** The page component (`InventoryListPage`, `CheckoutPage`, etc.) should end up mostly doing data-fetching and layout, importing the extracted components rather than containing raw markup itself. Hardcoded sample arrays get replaced with props or query results in the phase that builds that feature (Phase 3 for inventory, Phase 4 for checkout, etc.) — Phase 0.5 itself does not need working API calls yet, just components with a clean prop interface.

6. **Delete `src/_design/`** once every screen has been decomposed. Nothing should still import from it.

### Done when

- Every screen has been decomposed into a page + a set of named components under `src/components/` or `src/features/*/`.
- No component still contains hardcoded sample data — data comes in via props.
- Field names in props match the `_cents` / `snake_case`-to-`camelCase` conventions from Shared Context, not whatever the design tool happened to name them.
- `src/_design/` no longer exists and nothing references it.

---

## Phase 1 — Database schema and migrations

**Goal:** Every table exists, relationships are correct, and migrations run cleanly.

### Instructions

Create SQLAlchemy models in `app/models/`, one file per domain. Then generate and apply an Alembic migration.

**`users`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `email` | str | unique, indexed |
| `hashed_password` | str | |
| `full_name` | str | |
| `role` | enum | `seller` \| `buyer` |
| `phone` | str | nullable |
| `preferred_language` | str | default `en` |
| `is_active` | bool | default true |
| `created_at`, `updated_at` | datetime | |

**`seller_profiles`** — one-to-one with a `seller` user

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK → users, unique |
| `business_name` | str | |
| `business_type` | enum | `wholesale` \| `retail` \| `both` |
| `address` | text | nullable |
| `description` | text | nullable |
| `photo_url` | str | nullable |

**`products`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `seller_id` | UUID | FK → users, indexed |
| `name` | str | indexed |
| `description` | text | nullable |
| `photo_url` | str | nullable |
| `price_cents` | int | price per selling unit |
| `unit_type` | enum | `piece` \| `bundle` |\ `grams`|
| `pieces_per_unit` | int | default 1; >1 only for bundles |
| `stock_pieces` | int | **always stored in pieces**, never in bundles |
| `low_stock_threshold` | int | default 10, in pieces |
| `category` | str | nullable, indexed |
| `is_active` | bool | default true |
| `created_at`, `updated_at` | datetime | |

> **Critical:** `stock_pieces` is the single source of truth and is always counted in individual pieces. A bundle sale deducts `quantity × pieces_per_unit`. Never store stock in mixed units.

**`sales`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `seller_id` | UUID | FK → users, indexed |
| `buyer_id` | UUID | FK → users, **nullable**, indexed |
| `sale_type` | enum | `itemized` \| `walk_in` |
| `total_cents` | int | |
| `payment_method` | enum | `cash` \| `gcash` \| `maya` \| `bank_transfer` \| `other` |
| `receipt_code` | str | unique, indexed — short human-readable code |
| `note` | text | nullable — free text for walk-in aggregate sales |
| `created_at` | datetime | indexed (drives all date-range analytics) |

**`sale_items`**

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `sale_id` | UUID | FK → sales, indexed, cascade delete |
| `product_id` | UUID | FK → products, nullable (product may be deleted later) |
| `product_name_snapshot` | str | denormalized — history must survive product edits |
| `unit_price_cents_snapshot` | int | denormalized |
| `quantity` | int | in selling units, not pieces |
| `unit_type_snapshot` | enum | |
| `pieces_deducted` | int | computed at write time |
| `line_total_cents` | int | |

> **Critical:** snapshot the product name, price, and unit type onto every sale item. If a seller renames a product or changes its price, past receipts must not change.

**`stock_movements`** — audit log, append-only

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | PK |
| `product_id` | UUID | FK → products, indexed |
| `change_pieces` | int | negative for sales, positive for restock |
| `reason` | enum | `sale` \| `quick_sell` \| `restock` \| `correction` \| `initial` |
| `sale_id` | UUID | FK → sales, nullable |
| `note` | text | nullable |
| `created_at` | datetime | |

**`conversations`** and **`messages`**

- `conversations`: `id`, `seller_id`, `buyer_id`, `product_id` (nullable — conversation may be about a specific product), `last_message_at`, `created_at`. Unique constraint on `(seller_id, buyer_id, product_id)`.
- `messages`: `id`, `conversation_id`, `sender_id`, `body` (text), `read_at` (nullable), `created_at`.

### Done when

- `alembic upgrade head` creates every table on a clean database.
- `alembic downgrade base` reverses cleanly.
- A seed script inserts one seller, one buyer, and five products with a mix of `piece` and `bundle` unit types.

---

## Phase 2 — Auth

**Goal:** Register, log in, and protect routes by role.

### Instructions

**Backend** — `app/core/security.py` and `app/routers/auth.py`:

- Password hashing with `passlib` bcrypt.
- JWT access tokens via `python-jose`. Payload: `sub` (user id), `role`, `exp`.
- Dependencies in `app/core/deps.py`:
  - `get_current_user` — decodes the token, loads the user, raises 401 on failure.
  - `require_seller` — wraps the above, raises 403 if `role != seller`.
  - `require_buyer` — same for buyers.

Endpoints:

| Method | Path | Body / Notes |
|---|---|---|
| POST | `/auth/register` | email, password, full_name, role, optional business fields when role is seller (creates the `seller_profiles` row in the same transaction) |
| POST | `/auth/login` | OAuth2 password form → `{access_token, token_type, user}` |
| GET | `/auth/me` | current user + profile |
| PATCH | `/auth/me` | update name, phone, language, profile fields |

**Frontend** — `src/features/auth/`:

- `AuthContext` holding `{user, token, login, logout, isLoading}`, persisting the token to `localStorage` and rehydrating on mount.
- `LoginPage`, `RegisterPage` (with the role choice as the first step, matching the design's Seller/Buyer split).
- A `ProtectedRoute` component taking an optional `role` prop; redirects unauthenticated users to login and wrong-role users to their own home.
- A language toggle (English / Tagalog) writing to `preferred_language`. Wire up a simple `t()` helper backed by two JSON dictionaries — full i18n library is not needed yet, but do not hardcode user-facing strings.

### Done when

- A seller can register, log in, and hit a seller-only endpoint.
- A buyer receives 403 on that same endpoint.
- Refreshing the page keeps the user logged in; an expired token bounces to login.

---

## Phase 3 — Inventory (the core vertical slice)

**Goal:** Full CRUD on products, plus the quick-sell action. This is the make-or-break phase — get it fully working before touching anything else.

### Instructions

**Backend** — `app/services/inventory.py` and `app/routers/inventory.py`:

Business logic lives in the service, not the router.

```
def apply_stock_change(db, product, change_pieces, reason, sale_id=None, note=None):
    # 1. Lock the product row (SELECT ... FOR UPDATE) to prevent race conditions
    # 2. Reject if the result would be negative — raise a domain error
    # 3. Update product.stock_pieces
    # 4. Insert a stock_movements row
    # 5. Return the updated product
```

Endpoints (all seller-scoped — a seller may only ever touch their own products):

| Method | Path | Notes |
|---|---|---|
| GET | `/products` | query params: `search`, `category`, `stock_status` (`in_stock`/`low`/`out`), `page`, `page_size` |
| POST | `/products` | initial stock creates an `initial` stock movement |
| GET | `/products/{id}` | |
| PATCH | `/products/{id}` | does **not** change stock — stock has its own endpoints |
| DELETE | `/products/{id}` | soft delete: set `is_active = false`; never hard delete, sales reference it |
| POST | `/products/{id}/quick-sell` | body: `{quantity, payment_method}`. Creates a `walk_in` sale **and** deducts stock atomically in one transaction |
| POST | `/products/{id}/restock` | body: `{quantity, note}` |
| GET | `/products/low-stock` | all products where `stock_pieces <= low_stock_threshold` |
| POST | `/products/{id}/photo` | multipart upload; save to `UPLOAD_DIR`, store the URL |

> **Critical:** quick-sell is a single atomic transaction. Either the sale row, the sale_items row, the stock deduction, and the stock movement all commit, or none do. Wrap it and let exceptions roll back.

Compute a derived `stock_status` field in the Pydantic response schema: `out` when 0, `low` when `<= low_stock_threshold`, else `in_stock`. The frontend should never recompute this.

**Frontend** — `src/features/inventory/`. Reuse the components extracted in Phase 0.5 (`ProductCard`, `StockBadge`, etc.) rather than rebuilding the UI from scratch — this phase wires them to real data and behavior:

- `InventoryListPage` — searchable, filterable product list. Each row: photo thumbnail, name, price, stock count with a colored status badge, and a quick-sell control.
- `QuickSellSheet` — a bottom sheet opening on tap with a large quantity stepper defaulting to 1, a payment method selector, and one confirm button. **Target: two taps for the common case.** Show optimistic UI, roll back on error.
- `ProductFormPage` — create/edit with photo upload, name, description, price, unit type toggle (piece/bundle), and a conditional `pieces_per_unit` field that only appears when bundle is selected.
- `LowStockBanner` — dismissible banner on the dashboard listing products needing restock.
- Use TanStack Query with `invalidateQueries` on the product list after any mutation.

### Done when

- A seller creates a bundle product with 10 pieces per bundle and 100 pieces of stock.
- Quick-selling 2 bundles drops stock to 80 and creates one `walk_in` sale with the correct total.
- Attempting to sell more than available stock returns a clear error and changes nothing.
- The low-stock badge appears at the right threshold.

---

## Phase 4 — Sales, checkout, and receipts

**Goal:** Both sale paths work, and every sale produces a receipt.

### Instructions

**Backend** — `app/services/sales.py`, `app/routers/sales.py`:

| Method | Path | Notes |
|---|---|---|
| POST | `/sales` | body: `{sale_type, buyer_id?, payment_method, items: [{product_id, quantity}], note?}`. Validates stock for every line before deducting any of them. |
| GET | `/sales` | filters: `range` (`today`/`week`/`month`/`custom` with `start`/`end`), `sale_type`, `buyer_id`, pagination |
| GET | `/sales/{id}` | full detail with items |
| GET | `/sales/receipt/{receipt_code}` | **public, no auth** — this is what the QR code resolves to |

Receipt code generation: 8–10 characters, uppercase alphanumeric, excluding easily confused characters (`0`, `O`, `1`, `I`). Retry on collision.

The public receipt endpoint returns a trimmed payload — business name, items, total, timestamp, payment method. Never expose buyer or seller internal IDs, emails, or phone numbers here.

**Frontend** — `src/features/sales/`:

- `CheckoutPage` with the two-path split from the design:
  - **Walk-in** — the default and fastest path. Add items, confirm, done. No identity step at all.
  - **Buyer account** — search a buyer by phone or email, or scan their code, then attach and confirm.
- `ReceiptPage` — displays the receipt with a rendered QR code (use `qrcode.react`) pointing at the public receipt URL, plus print and share buttons. `window.print()` with a print-only stylesheet is sufficient for the printed path.
- `SalesHistoryPage` — transaction list with a range filter. **Walk-in and itemized entries must be visually distinguishable at a glance** — use a badge plus a subtle background tint, not color alone (accessibility).
- `PublicReceiptPage` — an unauthenticated route at `/r/:receiptCode` that anyone with the QR link can open.

### Done when

- A walk-in sale of three different products completes in under five taps and produces a scannable receipt.
- Opening the receipt URL in a private window (logged out) works.
- Sales history correctly separates the two types and filters by range.

---

## Phase 5 — Dashboard and analytics

**Goal:** The seller home screen answers "how am I doing today" in one glance.

### Instructions

**Backend** — `app/routers/analytics.py`:

| Method | Path | Returns |
|---|---|---|
| GET | `/analytics/summary` | today's sale count, today's revenue, low-stock count, week-over-week revenue change |
| GET | `/analytics/top-products` | params `range`, `limit`. Aggregates `sale_items` by quantity and revenue. |
| GET | `/analytics/sales-trend` | daily revenue and count buckets over the requested range, for charting |
| GET | `/analytics/forecast` | see below |

**Demand forecasting:** keep it simple and honest. Use a trailing moving average of daily pieces sold per product (7-day and 30-day), project days-of-stock-remaining as `stock_pieces / avg_daily_pieces`, and flag products projected to run out within 7 days. Do not build an ML model. Label the output clearly as an estimate in the UI, and return `null` rather than a fabricated number for products with fewer than 14 days of sales history.

Write these as single aggregate SQL queries with `GROUP BY`, not Python loops over fetched rows.

**Frontend** — `src/features/dashboard/`:

- `SellerDashboard` with stat cards (today's sales, revenue, low stock alerts, top seller), a sales trend chart (Recharts), and icon shortcuts to inventory, sales history, messages, and profile.
- Pinnable cards: let the seller choose which stats appear at the top, persisted to `localStorage`.
- Light/dark mode toggle via a CSS-variable theme and a `data-theme` attribute on the root, persisted to `localStorage` and defaulting to the system preference.

### Done when

- The dashboard loads in under a second with 500 seeded sales.
- Forecast returns `null`, not a garbage number, for a brand-new product.

---

## Phase 6 — Buyer experience

**Goal:** Buyers can find products, buy, and keep their receipts.

### Instructions

**Backend** — `app/routers/catalog.py`:

| Method | Path | Notes |
|---|---|---|
| GET | `/catalog/products` | public browse across all active sellers; search, category, seller filters |
| GET | `/catalog/sellers/{id}` | seller profile and their product list |
| GET | `/me/receipts` | buyer's own sales, newest first |
| POST | `/catalog/search-by-image` | see below |

**Image-based search:** implement in two stages. Ship stage one first.

- *Stage 1 (build now):* accept the upload, then return category and keyword matches based on a text query the buyer confirms. The camera becomes a shortcut to a pre-filled search, not magic. This is honest, cheap, and works offline-ish.
- *Stage 2 (defer):* plug in an actual vision model or embedding-similarity search over product photos. Design the endpoint contract now so stage two is a drop-in replacement — request takes an image, response is a ranked product list with confidence scores.

**Frontend** — `src/features/buyer/`:

- `BuyerHomePage` — search bar with a camera icon, category chips, product feed.
- `ProductDetailPage` — photos, price, seller info, a "message seller" button, and a buy action.
- `MyReceiptsPage` — the buyer's receipt history, each opening the same receipt view.

### Done when

- A buyer browses, opens a product, and sees the correct seller.
- Image search returns a sensible result set and never silently fails.

---

## Phase 7 — Messaging

**Goal:** Sellers and buyers can talk, optionally about a specific product.

### Instructions

**Backend** — `app/routers/messages.py`:

| Method | Path | Notes |
|---|---|---|
| GET | `/conversations` | current user's conversations, sorted by `last_message_at` |
| POST | `/conversations` | body: `{other_user_id, product_id?}`. Idempotent — returns the existing conversation if one matches. |
| GET | `/conversations/{id}/messages` | paginated, newest first |
| POST | `/conversations/{id}/messages` | sends; updates `last_message_at` |
| POST | `/conversations/{id}/read` | marks all as read |

Start with polling (TanStack Query `refetchInterval` of 5–10s on the active conversation). WebSockets are a later optimization — do not build them now.

Authorization: verify on every request that the current user is one of the two participants. Do not rely on the frontend to scope this.

**Frontend** — `src/features/messages/`:

- `ConversationListPage` with unread indicators.
- `ChatPage` with a message list and composer. If the conversation has a `product_id`, pin a compact product card at the top.
- A "message seller" entry point from the buyer's product detail page.

### Done when

- Two browser sessions (seller and buyer) can hold a conversation with messages appearing within the poll interval.
- Neither party can read a conversation they aren't part of.

---

## Phase 8 — Polish and hardening

**Goal:** Make it usable by a real seller in a real market.

### Instructions

1. **Empty, loading, and error states** for every list and screen. A blank screen is a bug.
2. **Offline resilience** — the frontend should queue quick-sell actions in `localStorage` when the request fails from a network error and retry on reconnect. Market wifi is unreliable and this is the highest-value polish item.
3. **Input validation** on both sides. Never trust the client. Pydantic validators for ranges (no negative prices, no zero quantities), and inline field errors in forms.
4. **Rate limiting** on auth endpoints (`slowapi` or equivalent).
5. **Tests** — pytest covering, at minimum: stock cannot go negative; bundle math deducts correctly; a walk-in sale creates no buyer reference; the public receipt endpoint leaks no private fields; role guards reject the wrong role.
6. **Accessibility** — tap targets at least 44px, labeled form inputs, status conveyed by icon or text as well as color, and a keyboard-navigable flow.
7. **Seed script** producing a realistic demo dataset: two sellers, 30 products, 200 sales across 60 days with a mix of types. Needed for a credible demo and for testing analytics.

---

## Build order and dependencies

```
Phase 0    Scaffolding
   ↓
Phase 0.5  Design integration (Claude Design → components)
   ↓
Phase 1  Schema  ──────────────┐
   ↓                           │
Phase 2  Auth                  │
   ↓                           │
Phase 3  Inventory  ← the vertical slice; validate everything here
   ↓                           │
Phase 4  Sales & receipts      │
   ↓                           │
   ├── Phase 5  Dashboard      │  (needs sales data)
   ├── Phase 6  Buyer          │  (needs catalog + receipts)
   └── Phase 7  Messaging      │  (independent, can run in parallel)
                               ↓
Phase 8  Polish
```

Phases 5, 6, and 7 are independent of each other. If working with more than one person or agent, split them there.

---

## Prompt template for each phase

When handing a phase to a coding model, use this shape:

```
Build Phase N of the Public Market POS system.

[paste the entire "Shared Context" section]

[paste the full text of the phase]

Additional context:
- The repo is at <path>. Phases 0 through N-1 are complete.
- Existing relevant files: <list them, or paste the schema/models>

Work in this order:
1. Backend models and schemas
2. Backend service layer (business logic)
3. Backend routers
4. A quick manual test of each endpoint
5. Frontend API client functions
6. Frontend components and pages

Show me the file tree of what you created before writing the code.
Flag anything in the spec that is ambiguous or that you think is wrong
rather than guessing.
```

That last line matters. A spec written up front will have gaps — you want them surfaced, not silently papered over.

---

## Decisions deliberately deferred

Not scope creep, just noted so nobody rebuilds around them later:

- **Real payment gateway integration.** Payment method is recorded, not processed. Adding GCash/Maya APIs later touches only the sales service.
- **Real-time messaging via WebSockets.** Polling is fine at this scale.
- **True vision-based image search.** The endpoint contract is designed for it; the implementation is stage one.
- **Multi-branch / multi-staff sellers.** The schema assumes one seller account per business. Adding staff means a `staff` table and a `staff_id` on sales.
- **Offline-first sync with conflict resolution.** Phase 8 covers retry queuing, which is not the same thing. Full offline-first is a much larger project.
