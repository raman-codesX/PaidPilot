import importlib
from unittest.mock import patch

import app.db.session as session


def test_postgres_does_not_use_sqlite_connect_args(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://user:password@localhost/testdb",
    )

    with patch("sqlalchemy.create_engine") as mock_create_engine:
        importlib.reload(session)

        _, kwargs = mock_create_engine.call_args

        assert kwargs.get("connect_args") == {}


def test_database_url_can_be_configured(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "sqlite:///./test_configured.db",
    )

    importlib.reload(session)

    assert session.DATABASE_URL == "sqlite:///./test_configured.db"