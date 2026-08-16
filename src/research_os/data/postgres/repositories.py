"""SQLAlchemy Core repositories. Not imported by Core, Research, or Workers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import select, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from research_os.data.errors import (
    PersistenceConflictError,
    PersistenceError,
    PersistenceInputError,
)
from research_os.data.postgres import mapping as map_row
from research_os.data.postgres import tables
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
    ResearchRunRecord,
    WorkerResultRecord,
    require_opaque_id,
)

T = TypeVar("T")


def _raise_integrity(exc: IntegrityError) -> None:
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate == "23505":
        raise PersistenceConflictError(
            "persistence unique constraint failed"
        ) from exc
    raise PersistenceError("persistence integrity constraint failed") from exc


def _execute_write(connection: Connection, statement) -> None:
    try:
        connection.execute(statement)
    except IntegrityError as exc:
        _raise_integrity(exc)
    except SQLAlchemyError as exc:
        raise PersistenceError("persistence write failed") from exc


def _fetch_one(
    connection: Connection,
    table,
    id_column,
    record_id: str,
    builder: Callable[[Any], T],
) -> T | None:
    try:
        row = connection.execute(
            select(table).where(id_column == record_id)
        ).mappings().one_or_none()
    except SQLAlchemyError as exc:
        raise PersistenceError("persistence read failed") from exc
    if row is None:
        return None
    return builder(row)


class PostgresProgramRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ProgramRecord) -> None:
        _execute_write(
            self._connection,
            tables.program.insert().values(
                program_id=record.program_id,
                name=record.name,
                created_at=record.created_at,
            ),
        )

    def get(self, program_id: str) -> ProgramRecord | None:
        require_opaque_id(program_id, "program_id")
        return _fetch_one(
            self._connection,
            tables.program,
            tables.program.c.program_id,
            program_id,
            map_row.program_from_row,
        )


class PostgresAuthorizationSourceRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: AuthorizationSourceRecord) -> None:
        _execute_write(
            self._connection,
            tables.authorization_source.insert().values(
                authorization_source_id=record.authorization_source_id,
                program_id=record.program_id,
                state=record.state,
                provenance_reference=record.provenance_reference,
                effective_from=record.effective_from,
                effective_until=record.effective_until,
                created_at=record.created_at,
            ),
        )

    def get(self, authorization_source_id: str) -> AuthorizationSourceRecord | None:
        require_opaque_id(authorization_source_id, "authorization_source_id")
        return _fetch_one(
            self._connection,
            tables.authorization_source,
            tables.authorization_source.c.authorization_source_id,
            authorization_source_id,
            map_row.authorization_source_from_row,
        )


class PostgresResearchRunRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchRunRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_run.insert().values(
                research_run_id=record.research_run_id,
                program_id=record.program_id,
                authorization_source_id=record.authorization_source_id,
                initiated_by_actor_id=record.initiated_by_actor_id,
                initiated_by_actor_type=record.initiated_by_actor_type,
                started_at=record.started_at,
            ),
        )

    def get(self, research_run_id: str) -> ResearchRunRecord | None:
        require_opaque_id(research_run_id, "research_run_id")
        return _fetch_one(
            self._connection,
            tables.research_run,
            tables.research_run.c.research_run_id,
            research_run_id,
            map_row.research_run_from_row,
        )


class PostgresIssuedBudgetRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: IssuedBudgetRecord) -> None:
        _execute_write(
            self._connection,
            tables.issued_budget.insert().values(
                budget_id=record.budget_id,
                research_run_id=record.research_run_id,
                max_requests=record.max_requests,
                max_tool_calls=record.max_tool_calls,
                max_runtime_ms=record.max_runtime_ms,
                max_concurrency=record.max_concurrency,
                issued_at=record.issued_at,
            ),
        )

    def get(self, budget_id: str) -> IssuedBudgetRecord | None:
        require_opaque_id(budget_id, "budget_id")
        return _fetch_one(
            self._connection,
            tables.issued_budget,
            tables.issued_budget.c.budget_id,
            budget_id,
            map_row.issued_budget_from_row,
        )


class PostgresHypothesisRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: HypothesisRecord) -> None:
        _execute_write(
            self._connection,
            tables.hypothesis.insert().values(
                hypothesis_id=record.hypothesis_id,
                research_run_id=record.research_run_id,
                claim=record.claim,
                origin_reference=record.origin_reference,
                created_at=record.created_at,
            ),
        )

    def get(self, hypothesis_id: str) -> HypothesisRecord | None:
        require_opaque_id(hypothesis_id, "hypothesis_id")
        return _fetch_one(
            self._connection,
            tables.hypothesis,
            tables.hypothesis.c.hypothesis_id,
            hypothesis_id,
            map_row.hypothesis_from_row,
        )


class PostgresExperimentRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ExperimentRecord) -> None:
        _execute_write(
            self._connection,
            tables.experiment.insert().values(
                experiment_id=record.experiment_id,
                research_run_id=record.research_run_id,
                hypothesis_id=record.hypothesis_id,
                budget_id=record.budget_id,
                execution_state=record.execution_state,
                created_at=record.created_at,
            ),
        )

    def get(self, experiment_id: str) -> ExperimentRecord | None:
        require_opaque_id(experiment_id, "experiment_id")
        return _fetch_one(
            self._connection,
            tables.experiment,
            tables.experiment.c.experiment_id,
            experiment_id,
            map_row.experiment_from_row,
        )

    def set_execution_state(self, experiment_id: str, execution_state: str) -> None:
        require_opaque_id(experiment_id, "experiment_id")
        if execution_state not in ALLOWED_EXPERIMENT_STATES:
            raise PersistenceInputError("execution_state is not a domain execution state")
        result = self._connection.execute(
            update(tables.experiment)
            .where(tables.experiment.c.experiment_id == experiment_id)
            .values(execution_state=execution_state)
        )
        if result.rowcount != 1:
            raise PersistenceError("experiment not found for execution_state update")


class PostgresExecutionAttemptRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ExecutionAttemptRecord) -> None:
        _execute_write(
            self._connection,
            tables.execution_attempt.insert().values(
                attempt_id=record.attempt_id,
                request_id=record.request_id,
                experiment_id=record.experiment_id,
                research_run_id=record.research_run_id,
                correlation_id=record.correlation_id,
                worker_capability=record.worker_capability,
                action=record.action,
                target_reference=record.target_reference,
                budget_id=record.budget_id,
                side_effect_level=record.side_effect_level,
                authorization_decision_reference=record.authorization_decision_reference,
                state=record.state,
                created_at=record.created_at,
                authorized_at=record.authorized_at,
                dispatch_started_at=record.dispatch_started_at,
                completed_at=record.completed_at,
            ),
        )

    def get(self, attempt_id: str) -> ExecutionAttemptRecord | None:
        require_opaque_id(attempt_id, "attempt_id")
        return _fetch_one(
            self._connection,
            tables.execution_attempt,
            tables.execution_attempt.c.attempt_id,
            attempt_id,
            map_row.execution_attempt_from_row,
        )

    def get_by_request_id(self, request_id: str) -> ExecutionAttemptRecord | None:
        require_opaque_id(request_id, "request_id")
        return _fetch_one(
            self._connection,
            tables.execution_attempt,
            tables.execution_attempt.c.request_id,
            request_id,
            map_row.execution_attempt_from_row,
        )

    def list_for_experiment(self, experiment_id: str) -> list[ExecutionAttemptRecord]:
        require_opaque_id(experiment_id, "experiment_id")
        try:
            rows = self._connection.execute(
                select(tables.execution_attempt).where(
                    tables.execution_attempt.c.experiment_id == experiment_id
                )
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.execution_attempt_from_row(row) for row in rows]

    def set_state(
        self,
        attempt_id: str,
        state: str,
        *,
        dispatch_started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        require_opaque_id(attempt_id, "attempt_id")
        if state not in ALLOWED_EXECUTION_ATTEMPT_STATES:
            raise PersistenceInputError("state is not an ExecutionAttempt state")
        values: dict[str, object] = {"state": state}
        if dispatch_started_at is not None:
            values["dispatch_started_at"] = dispatch_started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        try:
            result = self._connection.execute(
                update(tables.execution_attempt)
                .where(tables.execution_attempt.c.attempt_id == attempt_id)
                .values(**values)
            )
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence write failed") from exc
        if result.rowcount != 1:
            raise PersistenceError("execution_attempt not found for state update")


class PostgresWorkerResultRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: WorkerResultRecord) -> None:
        _execute_write(
            self._connection,
            tables.worker_result.insert().values(
                worker_result_id=record.worker_result_id,
                experiment_id=record.experiment_id,
                research_run_id=record.research_run_id,
                request_id=record.request_id,
                correlation_id=record.correlation_id,
                parent_request_id=record.parent_request_id,
                worker_capability=record.worker_capability,
                action=record.action,
                authorization_decision_reference=record.authorization_decision_reference,
                budget_id=record.budget_id,
                side_effect_level=record.side_effect_level,
                contract_version=record.contract_version,
                worker_id=record.worker_id,
                status=record.status,
                started_at=record.started_at,
                completed_at=record.completed_at,
                received_at=record.received_at,
                raw_result=record.raw_result,
                raw_artifact_descriptors=record.raw_artifact_descriptors,
                diagnostics=record.diagnostics,
                control_signal=record.control_signal,
            ),
        )

    def get(self, worker_result_id: str) -> WorkerResultRecord | None:
        require_opaque_id(worker_result_id, "worker_result_id")
        return _fetch_one(
            self._connection,
            tables.worker_result,
            tables.worker_result.c.worker_result_id,
            worker_result_id,
            map_row.worker_result_from_row,
        )

    def get_by_request_id(self, request_id: str) -> WorkerResultRecord | None:
        require_opaque_id(request_id, "request_id")
        return _fetch_one(
            self._connection,
            tables.worker_result,
            tables.worker_result.c.request_id,
            request_id,
            map_row.worker_result_from_row,
        )


class PostgresObservationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ObservationRecord) -> None:
        _execute_write(
            self._connection,
            tables.observation.insert().values(
                observation_id=record.observation_id,
                worker_result_id=record.worker_result_id,
                observation_kind=record.observation_kind,
                payload=dict(record.payload),
                normalization_version=record.normalization_version,
                observed_at=record.observed_at,
                created_at=record.created_at,
            ),
        )

    def get(self, observation_id: str) -> ObservationRecord | None:
        require_opaque_id(observation_id, "observation_id")
        return _fetch_one(
            self._connection,
            tables.observation,
            tables.observation.c.observation_id,
            observation_id,
            map_row.observation_from_row,
        )

    def list_for_worker_result(self, worker_result_id: str) -> list[ObservationRecord]:
        require_opaque_id(worker_result_id, "worker_result_id")
        try:
            rows = self._connection.execute(
                select(tables.observation).where(
                    tables.observation.c.worker_result_id == worker_result_id
                )
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.observation_from_row(row) for row in rows]


class PostgresAuditEventRepository:
    """Insert-only. Updates and deletes are rejected by PostgreSQL triggers."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: AuditEventRecord) -> None:
        _execute_write(
            self._connection,
            tables.audit_event.insert().values(
                audit_event_id=record.audit_event_id,
                occurred_at=record.occurred_at,
                actor_id=record.actor_id,
                actor_type=record.actor_type,
                event_type=record.event_type,
                subject_type=record.subject_type,
                subject_id=record.subject_id,
                correlation_id=record.correlation_id,
                payload=dict(record.payload),
            ),
        )

    def get(self, audit_event_id: str) -> AuditEventRecord | None:
        require_opaque_id(audit_event_id, "audit_event_id")
        return _fetch_one(
            self._connection,
            tables.audit_event,
            tables.audit_event.c.audit_event_id,
            audit_event_id,
            map_row.audit_event_from_row,
        )
