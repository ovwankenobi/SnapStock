import os

TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/pos_system_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import psycopg2  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from psycopg2 import sql  # noqa: E402


def _ensure_test_database() -> None:
    conn = psycopg2.connect(
        host="localhost", port=5432, user="postgres", password="postgres", dbname="postgres"
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("pos_system_test",))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier("pos_system_test")))
    finally:
        conn.close()


_ensure_test_database()

import app.models  # noqa: E402,F401  (registers models on Base.metadata)
from app.core.rate_limit import limiter  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    limiter.reset()
    yield


@pytest.fixture()
def client():
    return TestClient(app)
