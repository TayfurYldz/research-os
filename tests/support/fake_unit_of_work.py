"""In-memory Unit of Work for Application tests. Not a PostgreSQL substitute."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from research_os.data.errors import PersistenceConflictError, PersistenceError
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


class _Store:
    def __init__(self) -> None:
        self.programs: dict[str, ProgramRecord] = {}
        self.authorization_sources: dict[str, AuthorizationSourceRecord] = {}
        self.research_runs: dict[str, ResearchRunRecord] = {}
        self.issued_budgets: dict[str, IssuedBudgetRecord] = {}
        self.hypotheses: dict[str, HypothesisRecord] = {}
        self.experiments: dict[str, ExperimentRecord] = {}
        self.worker_results: dict[str, WorkerResultRecord] = {}
        self.worker_results_by_request: dict[str, str] = {}
        self.observations: dict[str, ObservationRecord] = {}
        self.audit_events: dict[str, AuditEventRecord] = {}


class _Repo:
    def __init__(self, store: dict[str, Any], fail_on_insert: bool = False) -> None:
        self._store = store
        self._fail_on_insert = fail_on_insert

    def insert(self, record: Any) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        key = _id_of(record)
        if key in self._store:
            raise PersistenceConflictError("duplicate id")
        self._store[key] = record

    def get(self, record_id: str) -> Any | None:
        return self._store.get(record_id)


def _id_of(record: Any) -> str:
    if isinstance(record, ProgramRecord):
        return record.program_id
    if isinstance(record, AuthorizationSourceRecord):
        return record.authorization_source_id
    if isinstance(record, ResearchRunRecord):
        return record.research_run_id
    if isinstance(record, IssuedBudgetRecord):
        return record.budget_id
    if isinstance(record, HypothesisRecord):
        return record.hypothesis_id
    if isinstance(record, ExperimentRecord):
        return record.experiment_id
    if isinstance(record, WorkerResultRecord):
        return record.worker_result_id
    if isinstance(record, ObservationRecord):
        return record.observation_id
    if isinstance(record, AuditEventRecord):
        return record.audit_event_id
    raise PersistenceError("unknown record identity")


class _WorkerResultRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.worker_results, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: WorkerResultRecord) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        if record.request_id in self._root.worker_results_by_request:
            raise PersistenceConflictError("duplicate request_id")
        super().insert(record)
        self._root.worker_results_by_request[record.request_id] = record.worker_result_id

    def get_by_request_id(self, request_id: str) -> WorkerResultRecord | None:
        worker_result_id = self._root.worker_results_by_request.get(request_id)
        if worker_result_id is None:
            return None
        return self._root.worker_results.get(worker_result_id)


class _ObservationRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.observations, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_worker_result(self, worker_result_id: str) -> list[ObservationRecord]:
        return [
            record
            for record in self._root.observations.values()
            if record.worker_result_id == worker_result_id
        ]


class FakeUnitOfWork:
    def __init__(self, store: _Store | None = None, fail_on: str | None = None) -> None:
        self._store = store or _Store()
        self._fail_on = fail_on
        self._committed = False
        self._snapshot: _Store | None = None
        self.programs = _Repo(self._store.programs)
        self.authorization_sources = _Repo(self._store.authorization_sources)
        self.research_runs = _Repo(self._store.research_runs)
        self.issued_budgets = _Repo(self._store.issued_budgets)
        self.hypotheses = _Repo(self._store.hypotheses)
        self.experiments = _Repo(self._store.experiments)
        self.worker_results = _WorkerResultRepo(
            self._store, fail_on_insert=fail_on == "worker_results"
        )
        self.observations = _ObservationRepo(
            self._store, fail_on_insert=fail_on == "observations"
        )
        self.audit_events = _Repo(
            self._store.audit_events, fail_on_insert=fail_on == "audit_events"
        )

    def __enter__(self) -> FakeUnitOfWork:
        self._snapshot = deepcopy(self._store)
        self._committed = False
        return self

    def commit(self) -> None:
        self._committed = True
        self._snapshot = None

    def rollback(self) -> None:
        if self._snapshot is not None:
            self._restore(self._snapshot)
        self._committed = False

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None or not self._committed:
            self.rollback()
        return False

    def _restore(self, snapshot: _Store) -> None:
        self._store.programs.clear()
        self._store.programs.update(snapshot.programs)
        self._store.authorization_sources.clear()
        self._store.authorization_sources.update(snapshot.authorization_sources)
        self._store.research_runs.clear()
        self._store.research_runs.update(snapshot.research_runs)
        self._store.issued_budgets.clear()
        self._store.issued_budgets.update(snapshot.issued_budgets)
        self._store.hypotheses.clear()
        self._store.hypotheses.update(snapshot.hypotheses)
        self._store.experiments.clear()
        self._store.experiments.update(snapshot.experiments)
        self._store.worker_results.clear()
        self._store.worker_results.update(snapshot.worker_results)
        self._store.worker_results_by_request.clear()
        self._store.worker_results_by_request.update(snapshot.worker_results_by_request)
        self._store.observations.clear()
        self._store.observations.update(snapshot.observations)
        self._store.audit_events.clear()
        self._store.audit_events.update(snapshot.audit_events)


class FakeUnitOfWorkFactory:
    def __init__(self, store: _Store | None = None, fail_on: str | None = None) -> None:
        self.store = store or _Store()
        self.fail_on = fail_on

    def open(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self.store, fail_on=self.fail_on)
