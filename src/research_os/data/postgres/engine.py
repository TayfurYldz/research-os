"""Synchronous SQLAlchemy engine bootstrap. Credentials are not logged."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from research_os.data.errors import PersistenceInputError

DATABASE_URL_ENV = "RESEARCH_OS_DATABASE_URL"
TEST_DATABASE_URL_ENV = "RESEARCH_OS_TEST_DATABASE_URL"

UNSAFE_TEST_DATABASE_NAMES = frozenset(
    {
        "postgres",
        "template0",
        "template1",
        "research_os",
    }
)


def redacted_database_url(url: str) -> str:
    """Render a URL with the password hidden. Never log the raw URL."""
    return make_url(url).render_as_string(hide_password=True)


def validate_test_database_url(
    url: str,
    *,
    application_url: str | None = None,
) -> str:
    """Refuse SQLite, system catalogs, and the application database URL.

    Isolation is by explicit RESEARCH_OS_TEST_DATABASE_URL only. Unrelated
    PG* environment variables are not consulted.
    """
    if not isinstance(url, str) or not url.strip():
        raise PersistenceInputError(f"{TEST_DATABASE_URL_ENV} is required")
    cleaned = url.strip()
    parsed = make_url(cleaned)
    if parsed.get_backend_name() != "postgresql":
        raise PersistenceInputError(
            "test database must be PostgreSQL; SQLite is not a substitute"
        )
    database = (parsed.database or "").strip()
    if not database:
        raise PersistenceInputError("test database URL must include a database name")
    if database.lower() in UNSAFE_TEST_DATABASE_NAMES:
        raise PersistenceInputError(
            "test database name looks like a system or production database"
        )
    if "test" not in database.lower():
        raise PersistenceInputError(
            "test database name must contain 'test' so destructive tests stay isolated"
        )
    if application_url and application_url.strip() == cleaned:
        raise PersistenceInputError(
            f"{TEST_DATABASE_URL_ENV} must not equal {DATABASE_URL_ENV}"
        )
    return cleaned


def redacted_database_url(url: str) -> str:
    """Render a URL with the password hidden. Never log the raw URL."""
    return make_url(url).render_as_string(hide_password=True)


def database_url_from_env(*, testing: bool = False) -> str:
    name = TEST_DATABASE_URL_ENV if testing else DATABASE_URL_ENV
    url = os.environ.get(name)
    if not url or not url.strip():
        raise PersistenceInputError(f"{name} is required")
    return url.strip()


def create_sync_engine(url: str) -> Engine:
    if not isinstance(url, str) or not url.strip():
        raise PersistenceInputError("database url is required")
    return create_engine(
        url.strip(),
        future=True,
        hide_parameters=True,
        pool_pre_ping=True,
    )
