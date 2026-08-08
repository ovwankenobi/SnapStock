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
- Inventory management — create/edit/delete products, piece/grams/bundle unit types, low-stock alerts, restock, product photos
- Quick sell — 1–2 tap manual stock deduction for walk-in sales, no scanning required
- Sales — record walk-in and itemized (buyer-linked) sales, buyer search, printable/digital receipts
- Analytics — sales summary, top products, sales trend, demand forecast
- Messaging — chat with buyers per conversation, unread counts

**Buyer**
- Browse seller catalogs and product feed, search by photo (image search)
- Place orders, view digital receipts (QR-linked), public receipt lookup by code
- Message sellers

**Shared**
- Auth (register/login/JWT), profile
- Bilingual UI (English / Tagalog toggle)
- Light/dark theme
- Offline-queue support for actions made while disconnected

## Backend

### Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Copy `.env` and adjust as needed (defaults work for local Postgres on `localhost:5432`):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/pos_system
SECRET_KEY=dev-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=["http://localhost:5173"]
UPLOAD_DIR=uploads
```

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
| `inventory` | `/products` | CRUD, low-stock, quick-sell, restock, photo upload |
| `sales` | `/sales` | create sale, list, buyer search, receipt lookup |
| `catalog` | `/catalog`, `/me/receipts` | buyer-facing product/seller browsing, image search, ordering, buyer receipts |
| `analytics` | `/analytics` | summary, top products, sales trend, forecast |
| `messages` | `/conversations` | list/create conversations, messages, mark read |

## Frontend

### Setup

```bash
cd frontend
npm install
```

`.env` (already present):

```
VITE_API_URL=http://localhost:6767/api/v1
```

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
├── features/   # auth, inventory, sales, dashboard, messages, buyer
├── components/ # shared UI primitives
├── hooks/
└── lib/        # apiClient, i18n, offline queue, formatting
```

## Running both

Start the backend (`uvicorn`, port 6767) and the frontend (`npm run dev`, port 5173) in separate terminals. The frontend's `apiClient` talks to the backend at `VITE_API_URL`, and the backend's CORS config allows the frontend's origin.
