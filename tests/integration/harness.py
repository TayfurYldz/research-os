"""Shared PostgreSQL integration harness. SQLite is not a substitute.

Requires an explicit RESEARCH_OS_TEST_DATABASE_URL. Tests TRUNCATE this database.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import Engine

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_REPO / "tests") not in sys.path:
    sys.path.insert(0, str(_REPO / "tests"))

from research_os.data.postgres.engine import (
    DATABASE_URL_ENV,
    TEST_DATABASE_URL_ENV,
    create_sync_engine,
    redacted_database_url,
    validate_test_database_url,
)
from research_os.data.postgres.unit_of_work import PostgresUnitOfWork
from research_os.data.records import (
    AuthorizationSourceRecord,
    ExperimentRecord,
    HypothesisRecord,
    IssuedBudgetRecord,
    ProgramRecord,
    ResearchRunRecord,
)

NOW = datetime(2026, 8, 16, 21, 0, tzinfo=timezone.utc)
DESTRUCTIVE_NOTICE = (
    "DESTRUCTIVE PostgreSQL integration tests: TRUNCATE CASCADE will run against "
    "the explicit test database only."
)


class PostgresUnitOfWorkFactory:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def open(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self._engine)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def configured_test_url() -> str | None:
    raw = os.environ.get(TEST_DATABASE_URL_ENV)
    if not raw or not raw.strip():
        return None
    return validate_test_database_url(
        raw,
        application_url=os.environ.get(DATABASE_URL_ENV),
    )


def alembic_upgrade(url: str) -> None:
    cfg = Config(str(_REPO / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def warn_destructive(url: str) -> None:
    print(f"{DESTRUCTIVE_NOTICE} target={redacted_database_url(url)}", flush=True)


def truncate_spine(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE program, audit_event CASCADE"))


def seed_authorized_spine(uow: PostgresUnitOfWork) -> None:
    uow.programs.insert(ProgramRecord(program_id="prog-1", created_at=NOW, name="lab"))
    uow.authorization_sources.insert(
        AuthorizationSourceRecord(
            authorization_source_id="as-1",
            program_id="prog-1",
            state="ACTIVE",
            provenance_reference="written-auth-1",
            created_at=NOW,
        )
    )
    uow.research_runs.insert(
        ResearchRunRecord(
            research_run_id="run-1",
            program_id="prog-1",
            authorization_source_id="as-1",
            initiated_by_actor_id="operator-1",
            initiated_by_actor_type="HUMAN_OPERATOR",
            started_at=NOW,
        )
    )
    uow.issued_budgets.insert(
        IssuedBudgetRecord(
            budget_id="budget-1",
            research_run_id="run-1",
            max_requests=1,
            max_tool_calls=1,
            max_runtime_ms=10_000,
            max_concurrency=1,
            issued_at=NOW,
        )
    )
    uow.hypotheses.insert(
        HypothesisRecord(
            hypothesis_id="hyp-1",
            research_run_id="run-1",
            claim="diagnostic runtime returns the provided echo value",
            origin_reference="human-seed-1",
            created_at=NOW,
        )
    )
    uow.experiments.insert(
        ExperimentRecord(
            experiment_id="exp-1",
            research_run_id="run-1",
            hypothesis_id="hyp-1",
            budget_id="budget-1",
            execution_state="PLANNED",
            created_at=NOW,
        )
    )
