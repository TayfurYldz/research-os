"""Synchronous Unit of Work. Explicit commit; otherwise rollback. Core does not own this."""

from __future__ import annotations

from sqlalchemy.engine import Connection, Engine

from research_os.data.errors import PersistenceError
from research_os.data.postgres.repositories import (
    PostgresAuditEventRepository,
    PostgresAuthorizationSourceRepository,
    PostgresExperimentRepository,
    PostgresHypothesisRepository,
    PostgresIssuedBudgetRepository,
    PostgresObservationRepository,
    PostgresProgramRepository,
    PostgresResearchRunRepository,
    PostgresWorkerResultRepository,
)


class PostgresUnitOfWork:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None
        self._transaction = None
        self._committed = False
        self.programs: PostgresProgramRepository
        self.authorization_sources: PostgresAuthorizationSourceRepository
        self.research_runs: PostgresResearchRunRepository
        self.issued_budgets: PostgresIssuedBudgetRepository
        self.hypotheses: PostgresHypothesisRepository
        self.experiments: PostgresExperimentRepository
        self.worker_results: PostgresWorkerResultRepository
        self.observations: PostgresObservationRepository
        self.audit_events: PostgresAuditEventRepository

    def __enter__(self) -> PostgresUnitOfWork:
        self._connection = self._engine.connect()
        self._transaction = self._connection.begin()
        self._committed = False
        self.programs = PostgresProgramRepository(self._connection)
        self.authorization_sources = PostgresAuthorizationSourceRepository(
            self._connection
        )
        self.research_runs = PostgresResearchRunRepository(self._connection)
        self.issued_budgets = PostgresIssuedBudgetRepository(self._connection)
        self.hypotheses = PostgresHypothesisRepository(self._connection)
        self.experiments = PostgresExperimentRepository(self._connection)
        self.worker_results = PostgresWorkerResultRepository(self._connection)
        self.observations = PostgresObservationRepository(self._connection)
        self.audit_events = PostgresAuditEventRepository(self._connection)
        return self

    def commit(self) -> None:
        if self._transaction is None:
            raise PersistenceError("unit of work has no active transaction")
        self._transaction.commit()
        self._committed = True

    def rollback(self) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()
        self._committed = False

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if self._transaction is not None and self._transaction.is_active:
                if exc_type is not None or not self._committed:
                    self._transaction.rollback()
        finally:
            if self._connection is not None:
                self._connection.close()
        return False
