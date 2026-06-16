"""
Shared pytest fixtures for OpsPilot's test suite.

NOTE ON ASSUMPTIONS:
This conftest assumes the following from your existing codebase (adjust the
imports/paths below if your actual names differ):
  - `app.main.app`                 -> the FastAPI() instance
  - `app.db.base.Base`              -> the SQLAlchemy declarative base
  - `app.core.dependencies.get_db`  -> the dependency that yields a DB session

Because OpsPilot relies on pgvector (a Postgres extension), these tests run
against a real Postgres instance rather than SQLite. Locally, point
DATABASE_URL at a throwaway test database; in CI, the postgres service
container defined in .github/workflows/ci.yml is used automatically.

STILL UNVERIFIED: `test_user_payload` guesses role="agent", department="IT"
as values your UserCreate schema / UserRole enum will accept. Share
app/schemas/user.py and app/models/enums.py to confirm or correct these.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.dependencies import get_db, get_redis
from app.db.base import Base
from app.main import app


class FakeRedis:
    """In-memory Redis stub — covers setex / get / delete used by auth routes."""

    def __init__(self):
        self._store: dict = {}

    def setex(self, name, time, value):
        self._store[name] = value

    def get(self, name):
        return self._store.get(name)

    def delete(self, *names):
        for name in names:
            self._store.pop(name, None)

TEST_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://test_user:test_pass@localhost:5432/opspilot_test",
)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables once per test session, drop them when done."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    """A DB session wrapped in a transaction that's rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """A TestClient with get_db and get_redis overridden for isolated testing."""
    fake_redis = FakeRedis()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    def _override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_redis] = _override_get_redis
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user_payload():
    return {
        "email": "testuser@example.com",
        "password": "StrongPass123!",
        "full_name": "Test User",
        "role": "agent",        # <-- verify against app/models/enums.py UserRole
        "department": "IT",     # <-- verify field is actually required/this shape
        "is_active": True,
    }


@pytest.fixture()
def auth_headers(client, test_user_payload):
    """
    Registers a fresh user and returns ready-to-use Authorization headers.

    /auth/register already returns {access_token, refresh_token, token_type}
    directly, so there's no need for a separate /auth/login round trip here.
    """
    register_resp = client.post("/api/v1/auth/register", json=test_user_payload)
    token = register_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}