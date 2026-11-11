"""Tests run against a real PostgreSQL.

Order of preference: TEST_DATABASE_URL, an embedded PostgreSQL started by pgserver
(a dev dependency, no Docker needed), then a temporary SQLite file.
"""
import os
import tempfile

_server = None


def _database_url() -> str:
    global _server
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    try:
        import pgserver
    except ImportError:
        return f"sqlite:///{tempfile.mkdtemp()}/test.db"
    _server = pgserver.get_server(tempfile.mkdtemp(), cleanup_mode="delete")
    return _server.get_uri().replace("postgresql://", "postgresql+psycopg://", 1)


os.environ["DATABASE_URL"] = _database_url()  # must be set before app.db is imported
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password-123"
os.environ["SECRET_KEY"] = "test-secret-key-with-enough-length-0123456789"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.security import limiter


@pytest.fixture()
def anon():
    """A client with no token."""
    Base.metadata.drop_all(engine)  # clean database per test; startup recreates it and seeds the sample pack
    limiter.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client(anon):
    """A client signed in as the admin account."""
    r = anon.post("/auth/login", json={"username": "admin", "password": "test-password-123"})
    assert r.status_code == 200
    anon.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return anon
