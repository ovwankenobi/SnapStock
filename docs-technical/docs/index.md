# Public Market POS — Technical Docs

Public Market POS ("SnapStock") is a mobile-first point-of-sale and inventory app for sellers in
public markets and small retail (sari-sari stores, market stalls), with a companion buyer
experience for digital orders, receipts, and messaging.

This site documents the system for developers working on the codebase. For the full product
spec and the reasoning behind schema decisions, see `pos-system-build-plan.md` in the repo root.
For end-user instructions, see the standalone user manuals in `/docs-manuals` (not part of this
site — see [Deferred Features](deferred-features.md) and the repo README for details on why
those are kept separate).

## Tech stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI |
| ORM / migrations | SQLAlchemy · Alembic |
| Database | PostgreSQL |
| Auth | JWT (`python-jose`), `passlib`/`bcrypt` password hashing |
| Rate limiting | `slowapi` |
| Frontend framework | React 19 (Vite) |
| Routing | React Router |
| Server state | TanStack Query |
| HTTP client | Axios |
| Charts | Recharts |
| QR codes | `qrcode.react` |

## Repo structure

```
backend/
├── app/
│   ├── core/         # auth deps (get_current_user, require_seller, require_buyer), security, rate limiting
│   ├── models/        # SQLAlchemy models — one file per domain
│   ├── routers/       # FastAPI routers — auth, request/response wiring only
│   ├── schemas/        # Pydantic request/response models (CamelModel base)
│   ├── services/       # business logic — inventory, sales, catalog, messages, analytics
│   ├── config.py       # Settings (env-driven)
│   ├── database.py     # SQLAlchemy engine/session
│   └── main.py         # FastAPI app, router mounting, CORS, rate limit handler
├── alembic/            # migrations
├── scripts/seed.py      # demo data seeding
└── tests/               # pytest suite (requires local Postgres)

frontend/
├── src/
│   ├── api/            # axios wrappers, one file per backend resource
│   ├── features/       # auth, inventory, sales, dashboard, messages, buyer — feature-scoped pages
│   ├── components/     # shared UI primitives (Badge, StatTile, QuantityStepper, ...)
│   ├── hooks/
│   └── lib/            # apiClient, i18n, offlineQueue, format helpers
└── index.html

docs-technical/   # this site
docs-manuals/     # standalone Word-conversion-ready user manuals (sellers, buyers)
```

## Three app surfaces, one backend

- **Seller app** — inventory management, quick-sell, itemized checkout, sales history/analytics,
  messaging. Routes gated by `ProtectedRoute role="seller"`.
- **Buyer app** — catalog browsing, placing orders, digital receipts, messaging sellers. Routes
  gated by `ProtectedRoute role="buyer"`.
- **Backend API** — a single FastAPI app (`app/main.py`) exposing all routers under `/api/v1`,
  backed by one shared PostgreSQL database. See [Architecture Overview](architecture/overview.md).

Continue to [Getting Started](getting-started.md) to run the stack locally, or
[Architecture Overview](architecture/overview.md) for how the pieces fit together.
