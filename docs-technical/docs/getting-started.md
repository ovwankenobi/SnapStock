# Getting Started

This runs the backend, database migrations, and frontend locally. Backend serves on port
`6767`, frontend dev server on `5173`, in separate terminals.

## Prerequisites

- Python 3.11+ and a local PostgreSQL instance on `localhost:5432` (user/pass `postgres`/`postgres`)
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
```

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
VITE_API_URL=http://localhost:6767/api/v1
```

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
terminals. The frontend's `apiClient` reads `VITE_API_URL` to reach the backend; the backend's
CORS config (`CORS_ORIGINS`) must include the frontend's origin.
