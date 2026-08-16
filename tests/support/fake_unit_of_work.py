"""In-memory Unit of Work for Application tests. Not a PostgreSQL substitute."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from research_os.data.errors import (
    PersistenceConflictError,
    PersistenceError,
    PersistenceInputError,
)
from research_os.data.records import (
    ALLOWED_EXECUTION_ATTEMPT_STATES,
    ALLOWED_EXPERIMENT_STATES,
    AuditEventRecord,
    AuthorizationSourceRecord,
    ExecutionAttemptRecord,
    ExperimentRecord,
    HypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchReasoningRecord,
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
        self.execution_attempts: dict[str, ExecutionAttemptRecord] = {}
        self.execution_attempts_by_request: dict[str, str] = {}
        self.worker_results: dict[str, WorkerResultRecord] = {}
        self.worker_results_by_request: dict[str, str] = {}
        self.observations: dict[str, ObservationRecord] = {}
        self.research_reasoning: dict[str, ResearchReasoningRecord] = {}
        self.audit_events: dict[str, AuditEventRecord] = {}
        self.open_transactions = 0
        self.set_state_calls = 0


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
    if isinstance(record, ExecutionAttemptRecord):
        return record.attempt_id
    if isinstance(record, WorkerResultRecord):
        return record.worker_result_id
    if isinstance(record, ObservationRecord):
        return record.observation_id
    if isinstance(record, ResearchReasoningRecord):
        return record.reasoning_record_id
    if isinstance(record, AuditEventRecord):
        return record.audit_event_id
    raise PersistenceError("unknown record identity")


class _HypothesisRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.hypotheses, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[HypothesisRecord]:
        return sorted(
            [
                record
                for record in self._root.hypotheses.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.hypothesis_id,
        )


class _ExperimentRepo(_Repo):
    def set_execution_state(self, experiment_id: str, execution_state: str) -> None:
        if execution_state not in ALLOWED_EXPERIMENT_STATES:
            raise PersistenceInputError("execution_state is not a domain execution state")
        current = self.get(experiment_id)
        if current is None:
            raise PersistenceError("experiment not found for execution_state update")
        self._store[experiment_id] = ExperimentRecord(
            experiment_id=current.experiment_id,
            research_run_id=current.research_run_id,
            hypothesis_id=current.hypothesis_id,
            budget_id=current.budget_id,
            execution_state=execution_state,
            created_at=current.created_at,
        )

    def list_for_research_run(self, research_run_id: str) -> list[ExperimentRecord]:
        return sorted(
            [
                record
                for record in self._store.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.experiment_id,
        )


class _ExecutionAttemptRepo(_Repo):
    def __init__(
        self,
        store: _Store,
        fail_on_insert: bool = False,
        fail_on_set_state: bool = False,
    ) -> None:
        super().__init__(store.execution_attempts, fail_on_insert=fail_on_insert)
        self._root = store
        self._fail_on_set_state = fail_on_set_state

    def insert(self, record: ExecutionAttemptRecord) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        if record.request_id in self._root.execution_attempts_by_request:
            raise PersistenceConflictError("duplicate request_id")
        super().insert(record)
        self._root.execution_attempts_by_request[record.request_id] = record.attempt_id

    def get_by_request_id(self, request_id: str) -> ExecutionAttemptRecord | None:
        attempt_id = self._root.execution_attempts_by_request.get(request_id)
        if attempt_id is None:
            return None
        return self._root.execution_attempts.get(attempt_id)

    def list_for_experiment(self, experiment_id: str) -> list[ExecutionAttemptRecord]:
        return [
            record
            for record in self._root.execution_attempts.values()
            if record.experiment_id == experiment_id
        ]

    def set_state(
        self,
        attempt_id: str,
        state: str,
        *,
        dispatch_started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        if self._fail_on_set_state:
            self._root.set_state_calls += 1
            if self._root.set_state_calls >= 2:
                raise PersistenceError("injected persistence failure")
        if state not in ALLOWED_EXECUTION_ATTEMPT_STATES:
            raise PersistenceInputError("state is not an ExecutionAttempt state")
        current = self.get(attempt_id)
        if current is None:
            raise PersistenceError("execution_attempt not found for state update")
        self._store[attempt_id] = ExecutionAttemptRecord(
            attempt_id=current.attempt_id,
            request_id=current.request_id,
            experiment_id=current.experiment_id,
            research_run_id=current.research_run_id,
            correlation_id=current.correlation_id,
            worker_capability=current.worker_capability,
            action=current.action,
            target_reference=current.target_reference,
            budget_id=current.budget_id,
            side_effect_level=current.side_effect_level,
            authorization_decision_reference=current.authorization_decision_reference,
            state=state,
            created_at=current.created_at,
            authorized_at=current.authorized_at,
            dispatch_started_at=(
                dispatch_started_at
                if dispatch_started_at is not None
                else current.dispatch_started_at
            ),
            completed_at=completed_at if completed_at is not None else current.completed_at,
        )


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

    def list_for_research_run(self, research_run_id: str) -> list[WorkerResultRecord]:
        return sorted(
            [
                record
                for record in self._root.worker_results.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.worker_result_id,
        )


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

    def list_for_research_run(self, research_run_id: str) -> list[ObservationRecord]:
        result_ids = {
            record.worker_result_id
            for record in self._root.worker_results.values()
            if record.research_run_id == research_run_id
        }
        return sorted(
            [
                record
                for record in self._root.observations.values()
                if record.worker_result_id in result_ids
            ],
            key=lambda record: record.observation_id,
        )


class _ResearchReasoningRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.research_reasoning, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[ResearchReasoningRecord]:
        return sorted(
            [
                record
                for record in self._root.research_reasoning.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.reasoning_record_id,
        )

    def list_for_hypothesis(self, hypothesis_id: str) -> list[ResearchReasoningRecord]:
        return sorted(
            [
                record
                for record in self._root.research_reasoning.values()
                if record.hypothesis_id == hypothesis_id
            ],
            key=lambda record: record.reasoning_record_id,
        )


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
        self.hypotheses = _HypothesisRepo(
            self._store, fail_on_insert=fail_on == "hypotheses"
        )
        self.experiments = _ExperimentRepo(self._store.experiments)
        self.execution_attempts = _ExecutionAttemptRepo(
            self._store,
            fail_on_insert=fail_on == "execution_attempts",
            fail_on_set_state=fail_on == "attempt_outcome",
        )
        self.worker_results = _WorkerResultRepo(
            self._store, fail_on_insert=fail_on == "worker_results"
        )
        self.observations = _ObservationRepo(
            self._store, fail_on_insert=fail_on == "observations"
        )
        self.research_reasoning = _ResearchReasoningRepo(
            self._store, fail_on_insert=fail_on == "research_reasoning"
        )
        self.audit_events = _Repo(
            self._store.audit_events, fail_on_insert=fail_on == "audit_events"
        )

    def __enter__(self) -> FakeUnitOfWork:
        self._store.open_transactions += 1
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
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._store.open_transactions = max(0, self._store.open_transactions - 1)
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
        self._store.execution_attempts.clear()
        self._store.execution_attempts.update(snapshot.execution_attempts)
        self._store.execution_attempts_by_request.clear()
        self._store.execution_attempts_by_request.update(
            snapshot.execution_attempts_by_request
        )
        self._store.worker_results.clear()
        self._store.worker_results.update(snapshot.worker_results)
        self._store.worker_results_by_request.clear()
        self._store.worker_results_by_request.update(snapshot.worker_results_by_request)
        self._store.observations.clear()
        self._store.observations.update(snapshot.observations)
        self._store.research_reasoning.clear()
        self._store.research_reasoning.update(snapshot.research_reasoning)
        self._store.audit_events.clear()
        self._store.audit_events.update(snapshot.audit_events)


class FakeUnitOfWorkFactory:
    def __init__(self, store: _Store | None = None, fail_on: str | None = None) -> None:
        self.store = store or _Store()
        self.fail_on = fail_on

    def open(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self.store, fail_on=self.fail_on)
