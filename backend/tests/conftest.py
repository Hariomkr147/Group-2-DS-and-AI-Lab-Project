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
os.environ["SOCRATIC_PROVIDER"] = "templates"  # no model calls in tests unless a test sets a fake model
os.environ["MESSAGE_CLASSIFIER_PROVIDER"] = "templates"  # the message classifier is a model call too
os.environ["STEP_FINDER_PROVIDER"] = "none"
os.environ["NCERT_ENABLED"] = ""

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app
from app.security import limiter


@pytest.fixture(autouse=True)
def fake_conversation_classifier(monkeypatch):
    """The conversation classifier is a model call; tests use fixed labels instead (tests/fake_classifier.py)."""
    from app.services import conversation

    from .fake_classifier import fake_classify
    real = conversation.classify
    monkeypatch.setattr(conversation, "classify", fake_classify)
    return real


@pytest.fixture(autouse=True)
def fake_path_classifier(monkeypatch):
    """The lesson-movement classifier (socratic.classify_path) is a model call too: fixed labels in tests."""
    from app.services import socratic

    from .fake_classifier import fake_classify_path
    real = socratic.classify_path
    monkeypatch.setattr(socratic, "classify_path", fake_classify_path)
    return real


@pytest.fixture(autouse=True)
def fake_input_check(monkeypatch):
    """Qwen's input check (socratic.check_input) is a model call too: fixed labels in tests."""
    from app.services import socratic

    from .fake_classifier import fake_check_input
    real = socratic.check_input
    monkeypatch.setattr(socratic, "check_input", fake_check_input)
    return real


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


@pytest.fixture()
def ncert_client(monkeypatch, request):
    monkeypatch.setenv("NCERT_ENABLED", "1")
    return request.getfixturevalue("client")
