# Getting Started

This runs the backend, database migrations, and frontend locally. Backend serves on port
`6767`, frontend dev server on `5173`, in separate terminals.

## Prerequisites

- Python 3.11+ and PostgreSQL on `localhost:5432` (user/pass `postgres`/`postgres`). The repo's
  `docker-compose.yml` provides one: `docker compose up -d db` from the repo root starts
  Postgres 16 with data in the `snapstock-pgdata` volume (development only).
- Node.js for the frontend

## Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env` (defaults work for local Postgres):

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/pos_system
SECRET_KEY=dev-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=["http://localhost:5173"]
UPLOAD_DIR=uploads
BUSINESS_TIMEZONE=Asia/Manila
```

`BUSINESS_TIMEZONE` (IANA name, default `Asia/Manila`) defines the sellers' business day for
"today", date ranges and daily/weekday/hourly analytics buckets. `tzdata` is in
`requirements.txt` so this works on Windows too. `AUTH_REGISTER_RATE_LIMIT` (default `5/minute`)
and `AUTH_LOGIN_RATE_LIMIT` (default `10/minute`) are also configurable.

Apply migrations, then run the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 6767
```

- Health check: `GET http://localhost:6767/api/v1/health` → `{"status": "ok"}`
- Interactive API docs (Swagger UI): `http://localhost:6767/docs`

### Seed demo data

```bash
python scripts/seed.py
```

### Run tests

```bash
pytest
```

Tests require a live Postgres on `localhost:5432`. `tests/conftest.py` auto-creates a separate
`pos_system_test` database, applies `Base.metadata.create_all` for the session, and truncates all
tables between tests.

### New migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
alembic downgrade base   # reverse all, if needed
```

## Frontend

```bash
cd frontend
npm install
```

`frontend/.env`:

```
VITE_API_URL=/api/v1
```

The URL is relative on purpose. The Vite dev server (`vite.config.js`) proxies `/api` and
`/uploads` to the backend at `http://127.0.0.1:6767` and listens on all interfaces
(`server.host: true`). A phone on the same Wi-Fi can open `http://<your-PC-IP>:5173` and only
needs to reach that one port. Because requests are same-origin through the proxy, CORS doesn't
come into play in development. If you point `VITE_API_URL` at an absolute URL instead, add the
frontend's origin to the backend's `CORS_ORIGINS`.

Run the dev server:

```bash
npm run dev
```

Loads at `http://localhost:5173`.

```bash
npm run lint   # oxlint, not eslint
npm run build
```

## Running both

Start the backend (`uvicorn`, port 6767) and the frontend (`npm run dev`, port 5173) in separate
terminals, then open `http://localhost:5173` (or `http://<your-PC-IP>:5173` on a phone). The
frontend's `apiClient` sends requests to `VITE_API_URL` (`/api/v1`), and the Vite proxy forwards
them to the backend.
