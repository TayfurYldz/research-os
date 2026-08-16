"""PostgreSQL spine tests. SQLite is not a substitute.

Requires RESEARCH_OS_TEST_DATABASE_URL pointing at a disposable database.
Skipped (not silently passed against another engine) when the URL is absent.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

_REPO = Path(__file__).resolve().parents[2]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from alembic import command
from alembic.config import Config

from research_os.data.postgres.engine import (
    TEST_DATABASE_URL_ENV,
    create_sync_engine,
)
from research_os.data.postgres.unit_of_work import PostgresUnitOfWork
from research_os.data.records import (
    AuditEventRecord,
    AuthorizationSourceRecord,
    ExperimentRecord,
    HypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchRunRecord,
    WorkerResultRecord,
)

TEST_URL = os.environ.get(TEST_DATABASE_URL_ENV)


def _now() -> datetime:
    return datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc)


def _alembic_upgrade(url: str) -> None:
    cfg = Config(str(_REPO / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@unittest.skipUnless(
    TEST_URL,
    f"{TEST_DATABASE_URL_ENV} not set; PostgreSQL integration tests skipped "
    "(SQLite is not a substitute)",
)
class PostgresSpineTests(unittest.TestCase):
    engine = None

    @classmethod
    def setUpClass(cls) -> None:
        assert TEST_URL is not None
        cls.engine = create_sync_engine(TEST_URL)
        _alembic_upgrade(TEST_URL)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.engine is not None:
            cls.engine.dispose()

    def setUp(self) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE program, audit_event CASCADE"))

    def _seed_run(self, uow: PostgresUnitOfWork) -> None:
        uow.programs.insert(
            ProgramRecord(program_id="prog-1", created_at=_now(), name="lab")
        )
        uow.authorization_sources.insert(
            AuthorizationSourceRecord(
                authorization_source_id="as-1",
                program_id="prog-1",
                state="ACTIVE",
                provenance_reference="written-auth-1",
                created_at=_now(),
            )
        )
        uow.research_runs.insert(
            ResearchRunRecord(
                research_run_id="run-1",
                program_id="prog-1",
                authorization_source_id="as-1",
                initiated_by_actor_id="operator-1",
                initiated_by_actor_type="HUMAN_OPERATOR",
                started_at=_now(),
            )
        )

    def test_migration_exposes_spine_tables(self) -> None:
        assert self.engine is not None
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename = 'program'"
                )
            ).all()
        self.assertEqual(len(rows), 1)

    def test_program_authorization_research_run_provenance(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            run = uow.research_runs.get("run-1")
            source = uow.authorization_sources.get("as-1")
            program = uow.programs.get("prog-1")
        self.assertIsNotNone(run)
        self.assertIsNotNone(source)
        self.assertIsNotNone(program)
        assert run is not None and source is not None
        self.assertEqual(run.program_id, source.program_id)
        self.assertEqual(run.authorization_source_id, source.authorization_source_id)

    def test_zero_budget_persists_as_zero(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.issued_budgets.insert(
                IssuedBudgetRecord(
                    budget_id="budget-zero",
                    research_run_id="run-1",
                    max_requests=0,
                    max_tool_calls=0,
                    max_runtime_ms=0,
                    max_concurrency=0,
                    issued_at=_now(),
                )
            )
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            budget = uow.issued_budgets.get("budget-zero")
        self.assertIsNotNone(budget)
        assert budget is not None
        self.assertEqual(budget.max_requests, 0)
        self.assertEqual(budget.max_concurrency, 0)

    def test_negative_budget_rejected_by_database(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.commit()
        with self.engine.begin() as connection:
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO issued_budget ("
                        "budget_id, research_run_id, max_requests, max_tool_calls, "
                        "max_runtime_ms, max_concurrency, issued_at"
                        ") VALUES ("
                        "'budget-neg', 'run-1', -1, 0, 0, 0, now()"
                        ")"
                    )
                )

    def test_foreign_key_rejects_unknown_program(self) -> None:
        assert self.engine is not None
        with self.engine.begin() as connection:
            with self.assertRaises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO authorization_source ("
                        "authorization_source_id, program_id, state, "
                        "provenance_reference, created_at"
                        ") VALUES ("
                        "'as-missing', 'no-such-program', 'ACTIVE', 'ref', now()"
                        ")"
                    )
                )

    def test_experiment_budget_must_belong_to_same_run(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.programs.insert(
                ProgramRecord(program_id="prog-2", created_at=_now())
            )
            uow.authorization_sources.insert(
                AuthorizationSourceRecord(
                    authorization_source_id="as-2",
                    program_id="prog-2",
                    state="ACTIVE",
                    provenance_reference="written-auth-2",
                    created_at=_now(),
                )
            )
            uow.research_runs.insert(
                ResearchRunRecord(
                    research_run_id="run-2",
                    program_id="prog-2",
                    authorization_source_id="as-2",
                    initiated_by_actor_id="operator-1",
                    initiated_by_actor_type="HUMAN_OPERATOR",
                    started_at=_now(),
                )
            )
            uow.issued_budgets.insert(
                IssuedBudgetRecord(
                    budget_id="budget-run1",
                    research_run_id="run-1",
                    max_requests=1,
                    max_tool_calls=1,
                    max_runtime_ms=1,
                    max_concurrency=1,
                    issued_at=_now(),
                )
            )
            uow.hypotheses.insert(
                HypothesisRecord(
                    hypothesis_id="hyp-2",
                    research_run_id="run-2",
                    claim="other run",
                    created_at=_now(),
                )
            )
            with self.assertRaises(Exception):
                uow.experiments.insert(
                    ExperimentRecord(
                        experiment_id="exp-cross",
                        research_run_id="run-2",
                        hypothesis_id="hyp-2",
                        budget_id="budget-run1",
                        execution_state="PLANNED",
                        created_at=_now(),
                    )
                )
            uow.rollback()

    def test_commit_persists_and_rollback_does_not(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            uow.hypotheses.insert(
                HypothesisRecord(
                    hypothesis_id="hyp-rollback",
                    research_run_id="run-1",
                    claim="should vanish",
                    created_at=_now(),
                )
            )
            uow.rollback()
        with PostgresUnitOfWork(self.engine) as uow:
            self.assertIsNone(uow.hypotheses.get("hyp-rollback"))
            uow.hypotheses.insert(
                HypothesisRecord(
                    hypothesis_id="hyp-commit",
                    research_run_id="run-1",
                    claim="should remain",
                    created_at=_now(),
                )
            )
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            self.assertIsNotNone(uow.hypotheses.get("hyp-commit"))

    def test_exit_without_commit_rolls_back(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            uow.hypotheses.insert(
                HypothesisRecord(
                    hypothesis_id="hyp-uncommitted",
                    research_run_id="run-1",
                    claim="no commit",
                    created_at=_now(),
                )
            )
        with PostgresUnitOfWork(self.engine) as uow:
            self.assertIsNone(uow.hypotheses.get("hyp-uncommitted"))

    def test_worker_result_does_not_create_observation(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.issued_budgets.insert(
                IssuedBudgetRecord(
                    budget_id="budget-1",
                    research_run_id="run-1",
                    max_requests=1,
                    max_tool_calls=1,
                    max_runtime_ms=1000,
                    max_concurrency=1,
                    issued_at=_now(),
                )
            )
            uow.hypotheses.insert(
                HypothesisRecord(
                    hypothesis_id="hyp-1",
                    research_run_id="run-1",
                    claim="claim",
                    created_at=_now(),
                )
            )
            uow.experiments.insert(
                ExperimentRecord(
                    experiment_id="exp-1",
                    research_run_id="run-1",
                    hypothesis_id="hyp-1",
                    budget_id="budget-1",
                    execution_state="PLANNED",
                    created_at=_now(),
                )
            )
            uow.worker_results.insert(
                WorkerResultRecord(
                    worker_result_id="wr-1",
                    experiment_id="exp-1",
                    research_run_id="run-1",
                    request_id="req-1",
                    correlation_id="corr-1",
                    worker_capability="diagnostic.echo",
                    action="echo",
                    authorization_decision_reference="authz-1",
                    budget_id="budget-1",
                    side_effect_level=0,
                    contract_version="v1",
                    worker_id="worker-1",
                    status="SUCCEEDED",
                    received_at=_now(),
                    raw_result={"ok": True},
                )
            )
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            self.assertIsNotNone(uow.worker_results.get("wr-1"))
            self.assertIsNone(uow.observations.get("wr-1"))
            uow.observations.insert(
                ObservationRecord(
                    observation_id="obs-1",
                    worker_result_id="wr-1",
                    observation_kind="http_status",
                    payload={"status": 200},
                    normalization_version="a3",
                    observed_at=_now(),
                    created_at=_now(),
                )
            )
            uow.commit()
        with PostgresUnitOfWork(self.engine) as uow:
            observation = uow.observations.get("obs-1")
        self.assertIsNotNone(observation)
        assert observation is not None
        self.assertEqual(observation.worker_result_id, "wr-1")

    def test_audit_event_is_append_only(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            uow.audit_events.insert(
                AuditEventRecord(
                    audit_event_id="ae-1",
                    occurred_at=_now(),
                    actor_id="operator-1",
                    actor_type="HUMAN_OPERATOR",
                    event_type="research_run_started",
                    subject_type="research_run",
                    subject_id="run-1",
                    payload={"note": "start"},
                )
            )
            uow.commit()
        with self.engine.connect() as connection:
            trans = connection.begin()
            with self.assertRaises(DBAPIError):
                connection.execute(
                    text(
                        "UPDATE audit_event SET event_type = 'tamper' "
                        "WHERE audit_event_id = 'ae-1'"
                    )
                )
            trans.rollback()

    def test_issued_budget_is_immutable(self) -> None:
        assert self.engine is not None
        with PostgresUnitOfWork(self.engine) as uow:
            self._seed_run(uow)
            uow.issued_budgets.insert(
                IssuedBudgetRecord(
                    budget_id="budget-imm",
                    research_run_id="run-1",
                    max_requests=3,
                    max_tool_calls=3,
                    max_runtime_ms=3,
                    max_concurrency=1,
                    issued_at=_now(),
                )
            )
            uow.commit()
        with self.engine.connect() as connection:
            trans = connection.begin()
            with self.assertRaises(DBAPIError):
                connection.execute(
                    text(
                        "UPDATE issued_budget SET max_requests = 99 "
                        "WHERE budget_id = 'budget-imm'"
                    )
                )
            trans.rollback()


if __name__ == "__main__":
    unittest.main()
