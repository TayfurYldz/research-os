"""Synchronous SQLAlchemy engine bootstrap. Credentials are not logged."""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

from research_os.data.errors import PersistenceInputError

DATABASE_URL_ENV = "RESEARCH_OS_DATABASE_URL"
TEST_DATABASE_URL_ENV = "RESEARCH_OS_TEST_DATABASE_URL"


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
