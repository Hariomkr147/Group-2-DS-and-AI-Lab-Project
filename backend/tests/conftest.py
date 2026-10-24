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
