# Public Market POS

A mobile-first POS and inventory app for sellers in public markets and small retail (sari-sari stores, market stalls), with a companion buyer experience for digital orders, receipts, and messaging.

See [pos-system-build-plan.md](pos-system-build-plan.md) for the full product spec and phased build plan.

## Documentation

- **`/docs-technical`** — developer-facing MkDocs site (architecture, data-flow diagrams, API
  reference, database schema). Preview with `mkdocs serve` from that folder (see
  [docs-technical/README.md](docs-technical/README.md)); build a static site with `mkdocs build`,
  or publish with `mkdocs gh-deploy` if this repo has a GitHub remote.
- **`/docs-manuals`** — standalone, Word-conversion-ready user manuals for sellers and buyers
  (plain Markdown, no MkDocs/Mermaid syntax). Not part of the MkDocs site.

## Stack

- **Backend:** FastAPI · SQLAlchemy · Alembic · PostgreSQL · JWT auth (`python-jose`) · rate limiting (`slowapi`)
- **Frontend:** React 19 (Vite) · React Router · TanStack Query · Axios · Recharts · `qrcode.react`

## Repo layout

```
backend/    FastAPI + SQLAlchemy + Alembic
frontend/   Vite + React + React Router + TanStack Query
```

## Features

**Seller**
- Inventory management — create/edit/delete products, piece/bundle/per-unit (configurable measurement: kg, yd, m, …) unit types, categories, cost prices, low-stock alerts, single and bulk restock, product photos, search by photo
- New Sale (walk-in) — tap-to-add cart with a number pad, per-line price changes, a sale-level discount, and a payment sheet that shows your GCash/Maya/bank QR to the customer
- Online orders — approve or reject buyers' orders after checking their payment screenshot (New Sale → Buyer Account); each order also appears as a card in chat
- Receipts and transactions — printable/digital receipts, void or refund a sale, Transactions list by date range
- Analytics — insights feed plus Sales, Profit, Stock and Forecast tabs, using local business days (Asia/Manila)
- Payout accounts — GCash, Maya, bank or other accounts with QR codes, shown to buyers when they pay
- Messaging — chat with buyers per conversation, unread counts

**Buyer**
- Browse seller catalogs and product feed, search by photo (image search)
- Place orders, pay to the seller's account and upload a payment screenshot, cancel a pending order
- View transactions and digital receipts (QR-linked), public receipt lookup by code
- Message sellers

**Shared**
- Auth (register/login/JWT), profile
- Bilingual UI (English / Tagalog toggle)
- Light/dark theme
- Open the dev server from a phone on the same Wi-Fi (the Vite dev server proxies the API)

## Backend

### Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Start the local development database (requires Docker Desktop), from the repo root:

```bash
docker compose up -d db       # Postgres 16 on localhost:5432, data kept in the snapstock-pgdata volume
```

Then create the schema with `alembic upgrade head` (see [Migrations](#migrations)).
This container is for development only — in production, point `DATABASE_URL` at Amazon RDS.

Copy `.env` and adjust as needed (defaults work for local Postgres on `localhost:5432`):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/pos_system
SECRET_KEY=dev-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=["http://localhost:5173"]
UPLOAD_DIR=uploads
BUSINESS_TIMEZONE=Asia/Manila
```

`BUSINESS_TIMEZONE` sets the sellers' business day for "today" and analytics buckets.

### Run

```bash
uvicorn app.main:app --reload --port 6767
```

Health check: `GET http://localhost:6767/api/v1/health` → `{"status": "ok"}`

Interactive API docs (Swagger UI): `http://localhost:6767/docs`

### Migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```

### Seed data

```bash
python scripts/seed.py
```

### Tests

```bash
pytest
```

### API overview

All routes are prefixed with `/api/v1`.

| Router | Base path | Covers |
|---|---|---|
| `auth` | `/auth` | register, login, `me` (get/patch) |
| `inventory` | `/products` | CRUD, categories, low-stock, quick-sell, single and bulk restock, photo upload, search by photo |
| `sales` | `/sales` | create sale, list, buyer search, receipt lookup, void/refund, confirm/reject buyer orders |
| `catalog` | `/catalog`, `/me/orders`, `/me/receipts` | buyer-facing product/seller browsing, image search, ordering, payment proof upload, cancel order, buyer receipts |
| `analytics` | `/analytics` | summary, overview, top products, sales trend, patterns, inventory health, forecast, insights |
| `messages` | `/conversations` | list/create conversations, messages (including order cards), mark read |
| `payouts` | `/seller/payout-accounts` | seller payout accounts (CRUD, default account, QR upload) |

## Frontend

### Setup

```bash
cd frontend
npm install
```

`.env` (already present):

```
VITE_API_URL=/api/v1
```

The Vite dev server proxies `/api` and `/uploads` to the backend on `127.0.0.1:6767` and
listens on all interfaces, so a phone on the same Wi-Fi can open `http://<your-PC-IP>:5173`.

### Run

```bash
npm run dev
```

Loads at `http://localhost:5173`.

### Lint / build

```bash
npm run lint
npm run build
```

### Structure

```
src/
├── api/        # axios wrappers, one file per resource
├── features/   # auth, inventory, sales, analytics, dashboard, messages, payouts, buyer
├── components/ # shared UI primitives
├── hooks/
└── lib/        # apiClient, i18n, nav, dates, offline queue, formatting
```

## Running both

Start the backend (`uvicorn`, port 6767) and the frontend (`npm run dev`, port 5173) in separate terminals, then open `http://localhost:5173`. The frontend's `apiClient` calls `VITE_API_URL` (`/api/v1`), which the Vite proxy forwards to the backend. If you set `VITE_API_URL` to an absolute backend URL instead, the backend's `CORS_ORIGINS` must include the frontend's origin.
