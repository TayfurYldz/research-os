"""SQLAlchemy Core repositories. Not imported by Core, Research, or Workers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import select, update
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from research_os.data.errors import (
    BudgetOverspendError,
    PersistenceConflictError,
    PersistenceError,
    PersistenceInputError,
)
from research_os.data.postgres import mapping as map_row
from research_os.data.postgres import tables
from research_os.data.records import (
    ALLOWED_CANDIDATE_STATES,
    ALLOWED_EXECUTION_ATTEMPT_STATES,
    ALLOWED_EXPERIMENT_STATES,
    ALLOWED_FINDING_PROPOSAL_STATES,
    ALLOWED_INVARIANT_STATUSES,
    ALLOWED_SESSION_STATES,
    ApprovalRecord,
    AuditEventRecord,
    AuthorizationSourceRecord,
    BudgetConsumptionRecord,
    CandidateAdmissionRecord,
    CandidateRecord,
    ChainHypothesisRecord,
    DifferentialObservationRecord,
    EvidenceAdmissionRecord,
    EvidenceRecord,
    ExecutionAttemptRecord,
    ExperimentPlanRecord,
    ExperimentRecord,
    FindingProposalRecord,
    FindingRecord,
    HypothesisAssessmentRecord,
    HypothesisRecord,
    HumanReviewRecord,
    InvariantCounterexampleRefRecord,
    InvariantHypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchAdmissionRecord,
    ResearchCycleRecord,
    ResearchOrchestrationRecord,
    ResearchReasoningRecord,
    ResearchRunRecord,
    TargetInferenceRecord,
    VerificationRecord,
    WorkerResultRecord,
    require_opaque_id,
    ResearchOpportunityRecord,
    ResearchSelectionRecord,
    SnapshotRecord,
    SnapshotMemberRecord,
    ChangeEventRecord,
    SessionContextRecord,
)
from research_os.data.budget_ledger import assert_within_allowance


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

    def list_for_research_run(self, research_run_id: str) -> list[IssuedBudgetRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.issued_budget)
                .where(tables.issued_budget.c.research_run_id == research_run_id)
                .order_by(tables.issued_budget.c.budget_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.issued_budget_from_row(row) for row in rows]


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

    def list_for_research_run(self, research_run_id: str) -> list[HypothesisRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.hypothesis)
                .where(tables.hypothesis.c.research_run_id == research_run_id)
                .order_by(tables.hypothesis.c.hypothesis_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.hypothesis_from_row(row) for row in rows]


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

    def list_for_research_run(self, research_run_id: str) -> list[ExperimentRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.experiment)
                .where(tables.experiment.c.research_run_id == research_run_id)
                .order_by(tables.experiment.c.experiment_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.experiment_from_row(row) for row in rows]

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

    def list_for_research_run(self, research_run_id: str) -> list[ExecutionAttemptRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.execution_attempt)
                .where(tables.execution_attempt.c.research_run_id == research_run_id)
                .order_by(tables.execution_attempt.c.attempt_id)
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

    def list_for_research_run(self, research_run_id: str) -> list[WorkerResultRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.worker_result)
                .where(tables.worker_result.c.research_run_id == research_run_id)
                .order_by(tables.worker_result.c.worker_result_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.worker_result_from_row(row) for row in rows]

    def list_for_experiment(self, experiment_id: str) -> list[WorkerResultRecord]:
        require_opaque_id(experiment_id, "experiment_id")
        try:
            rows = self._connection.execute(
                select(tables.worker_result)
                .where(tables.worker_result.c.experiment_id == experiment_id)
                .order_by(tables.worker_result.c.worker_result_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.worker_result_from_row(row) for row in rows]


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

    def list_for_research_run(self, research_run_id: str) -> list[ObservationRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.observation)
                .join(
                    tables.worker_result,
                    tables.observation.c.worker_result_id
                    == tables.worker_result.c.worker_result_id,
                )
                .where(tables.worker_result.c.research_run_id == research_run_id)
                .order_by(tables.observation.c.observation_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.observation_from_row(row) for row in rows]

    def list_for_experiment(self, experiment_id: str) -> list[ObservationRecord]:
        require_opaque_id(experiment_id, "experiment_id")
        try:
            rows = self._connection.execute(
                select(tables.observation)
                .join(
                    tables.worker_result,
                    tables.observation.c.worker_result_id
                    == tables.worker_result.c.worker_result_id,
                )
                .where(tables.worker_result.c.experiment_id == experiment_id)
                .order_by(tables.observation.c.observation_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.observation_from_row(row) for row in rows]


class PostgresResearchReasoningRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchReasoningRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_reasoning.insert().values(
                reasoning_record_id=record.reasoning_record_id,
                research_run_id=record.research_run_id,
                hypothesis_id=record.hypothesis_id,
                role=record.role,
                adapter_identity=record.adapter_identity,
                provider_adapter_identity=record.provider_adapter_identity,
                correlation_id=record.correlation_id,
                context_fingerprint=record.context_fingerprint,
                structured_output=dict(record.structured_output),
                created_at=record.created_at,
                model_id=record.model_id,
                model_version=record.model_version,
            ),
        )

    def get(self, reasoning_record_id: str) -> ResearchReasoningRecord | None:
        require_opaque_id(reasoning_record_id, "reasoning_record_id")
        return _fetch_one(
            self._connection,
            tables.research_reasoning,
            tables.research_reasoning.c.reasoning_record_id,
            reasoning_record_id,
            map_row.research_reasoning_from_row,
        )

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[ResearchReasoningRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.research_reasoning)
                .where(tables.research_reasoning.c.research_run_id == research_run_id)
                .order_by(tables.research_reasoning.c.reasoning_record_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.research_reasoning_from_row(row) for row in rows]

    def list_for_hypothesis(self, hypothesis_id: str) -> list[ResearchReasoningRecord]:
        require_opaque_id(hypothesis_id, "hypothesis_id")
        try:
            rows = self._connection.execute(
                select(tables.research_reasoning)
                .where(tables.research_reasoning.c.hypothesis_id == hypothesis_id)
                .order_by(tables.research_reasoning.c.reasoning_record_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.research_reasoning_from_row(row) for row in rows]


class PostgresResearchAdmissionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchAdmissionRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_admission.insert().values(
                admission_record_id=record.admission_record_id,
                research_run_id=record.research_run_id,
                generator_reasoning_record_id=record.generator_reasoning_record_id,
                falsifier_reasoning_record_id=record.falsifier_reasoning_record_id,
                outcome=record.outcome,
                admitted_hypothesis_id=record.admitted_hypothesis_id,
                reason=record.reason,
                reason_code=record.reason_code,
                context_fingerprint=record.context_fingerprint,
                created_at=record.created_at,
            ),
        )

    def get(self, admission_record_id: str) -> ResearchAdmissionRecord | None:
        require_opaque_id(admission_record_id, "admission_record_id")
        return _fetch_one(
            self._connection,
            tables.research_admission,
            tables.research_admission.c.admission_record_id,
            admission_record_id,
            map_row.research_admission_from_row,
        )

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[ResearchAdmissionRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.research_admission)
                .where(tables.research_admission.c.research_run_id == research_run_id)
                .order_by(tables.research_admission.c.admission_record_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.research_admission_from_row(row) for row in rows]


class PostgresExperimentPlanRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ExperimentPlanRecord) -> None:
        _execute_write(
            self._connection,
            tables.experiment_plan.insert().values(
                experiment_id=record.experiment_id,
                research_run_id=record.research_run_id,
                hypothesis_id=record.hypothesis_id,
                required_capability=record.required_capability,
                action=record.action,
                target_reference=record.target_reference,
                side_effect_level=record.side_effect_level,
                arguments=dict(record.arguments),
                requested_budget_id=record.requested_budget_id,
                expected_observation=record.expected_observation,
                disconfirming_observation=record.disconfirming_observation,
                evaluation_strategy=record.evaluation_strategy,
                capability_version=record.capability_version,
                capability_definition_fingerprint=record.capability_definition_fingerprint,
                created_at=record.created_at,
            ),
        )

    def get(self, experiment_id: str) -> ExperimentPlanRecord | None:
        require_opaque_id(experiment_id, "experiment_id")
        return _fetch_one(
            self._connection,
            tables.experiment_plan,
            tables.experiment_plan.c.experiment_id,
            experiment_id,
            map_row.experiment_plan_from_row,
        )


class PostgresHypothesisAssessmentRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: HypothesisAssessmentRecord) -> None:
        _execute_write(
            self._connection,
            tables.hypothesis_assessment.insert().values(
                assessment_id=record.assessment_id,
                hypothesis_id=record.hypothesis_id,
                experiment_id=record.experiment_id,
                research_run_id=record.research_run_id,
                assessment_outcome=record.assessment_outcome,
                observation_ids=list(record.observation_ids),
                evaluator_kind=record.evaluator_kind,
                evaluator_version=record.evaluator_version,
                rationale=dict(record.rationale),
                evaluation_strategy=record.evaluation_strategy,
                created_at=record.created_at,
            ),
        )

    def get(self, assessment_id: str) -> HypothesisAssessmentRecord | None:
        require_opaque_id(assessment_id, "assessment_id")
        return _fetch_one(
            self._connection,
            tables.hypothesis_assessment,
            tables.hypothesis_assessment.c.assessment_id,
            assessment_id,
            map_row.hypothesis_assessment_from_row,
        )

    def list_for_experiment(
        self, experiment_id: str
    ) -> list[HypothesisAssessmentRecord]:
        require_opaque_id(experiment_id, "experiment_id")
        try:
            rows = self._connection.execute(
                select(tables.hypothesis_assessment)
                .where(tables.hypothesis_assessment.c.experiment_id == experiment_id)
                .order_by(tables.hypothesis_assessment.c.assessment_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.hypothesis_assessment_from_row(row) for row in rows]

    def list_for_hypothesis(
        self, hypothesis_id: str
    ) -> list[HypothesisAssessmentRecord]:
        require_opaque_id(hypothesis_id, "hypothesis_id")
        try:
            rows = self._connection.execute(
                select(tables.hypothesis_assessment)
                .where(tables.hypothesis_assessment.c.hypothesis_id == hypothesis_id)
                .order_by(tables.hypothesis_assessment.c.assessment_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.hypothesis_assessment_from_row(row) for row in rows]

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[HypothesisAssessmentRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.hypothesis_assessment)
                .where(tables.hypothesis_assessment.c.research_run_id == research_run_id)
                .order_by(tables.hypothesis_assessment.c.assessment_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.hypothesis_assessment_from_row(row) for row in rows]


class PostgresEvidenceRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: EvidenceRecord) -> None:
        _execute_write(
            self._connection,
            tables.evidence.insert().values(
                evidence_id=record.evidence_id,
                research_run_id=record.research_run_id,
                hypothesis_id=record.hypothesis_id,
                experiment_id=record.experiment_id,
                admission_record_id=record.admission_record_id,
                polarity=record.polarity,
                claim_scope=record.claim_scope,
                observation_ids=list(record.observation_ids),
                assessment_ids=list(record.assessment_ids),
                created_at=record.created_at,
            ),
        )
        for observation_id in record.observation_ids:
            _execute_write(
                self._connection,
                tables.evidence_observation.insert().values(
                    evidence_id=record.evidence_id,
                    observation_id=observation_id,
                ),
            )

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        require_opaque_id(evidence_id, "evidence_id")
        return _fetch_one(
            self._connection,
            tables.evidence,
            tables.evidence.c.evidence_id,
            evidence_id,
            map_row.evidence_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[EvidenceRecord]:
        return self._list(tables.evidence.c.research_run_id, research_run_id, "research_run_id")

    def list_for_hypothesis(self, hypothesis_id: str) -> list[EvidenceRecord]:
        return self._list(tables.evidence.c.hypothesis_id, hypothesis_id, "hypothesis_id")

    def list_for_experiment(self, experiment_id: str) -> list[EvidenceRecord]:
        return self._list(tables.evidence.c.experiment_id, experiment_id, "experiment_id")

    def _list(self, column, value: str, field_name: str) -> list[EvidenceRecord]:
        require_opaque_id(value, field_name)
        try:
            rows = self._connection.execute(
                select(tables.evidence)
                .where(column == value)
                .order_by(tables.evidence.c.evidence_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.evidence_from_row(row) for row in rows]


class PostgresEvidenceAdmissionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: EvidenceAdmissionRecord) -> None:
        _execute_write(
            self._connection,
            tables.evidence_admission.insert().values(
                admission_record_id=record.admission_record_id,
                proposal_id=record.proposal_id,
                research_run_id=record.research_run_id,
                outcome=record.outcome,
                reason_codes=list(record.reason_codes),
                observation_ids=list(record.observation_ids),
                assessment_ids=list(record.assessment_ids),
                admission_policy_version=record.admission_policy_version,
                evaluator_version=record.evaluator_version,
                created_at=record.created_at,
                admitted_evidence_id=record.admitted_evidence_id,
                claim_scope=record.claim_scope,
                polarity=record.polarity,
            ),
        )

    def get(self, admission_record_id: str) -> EvidenceAdmissionRecord | None:
        require_opaque_id(admission_record_id, "admission_record_id")
        return _fetch_one(
            self._connection,
            tables.evidence_admission,
            tables.evidence_admission.c.admission_record_id,
            admission_record_id,
            map_row.evidence_admission_from_row,
        )

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[EvidenceAdmissionRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.evidence_admission)
                .where(tables.evidence_admission.c.research_run_id == research_run_id)
                .order_by(tables.evidence_admission.c.admission_record_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.evidence_admission_from_row(row) for row in rows]


class PostgresCandidateRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: CandidateRecord) -> None:
        _execute_write(
            self._connection,
            tables.candidate.insert().values(
                candidate_id=record.candidate_id,
                research_run_id=record.research_run_id,
                hypothesis_id=record.hypothesis_id,
                claim=record.claim,
                classification=record.classification,
                state=record.state,
                evidence_ids=list(record.evidence_ids),
                admission_record_id=record.admission_record_id,
                created_at=record.created_at,
            ),
        )
        for evidence_id in record.evidence_ids:
            _execute_write(
                self._connection,
                tables.candidate_evidence.insert().values(
                    candidate_id=record.candidate_id,
                    evidence_id=evidence_id,
                ),
            )

    def get(self, candidate_id: str) -> CandidateRecord | None:
        require_opaque_id(candidate_id, "candidate_id")
        return _fetch_one(
            self._connection,
            tables.candidate,
            tables.candidate.c.candidate_id,
            candidate_id,
            map_row.candidate_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[CandidateRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.candidate)
                .where(tables.candidate.c.research_run_id == research_run_id)
                .order_by(tables.candidate.c.candidate_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.candidate_from_row(row) for row in rows]

    def set_state(self, candidate_id: str, state: str) -> None:
        require_opaque_id(candidate_id, "candidate_id")
        if state not in ALLOWED_CANDIDATE_STATES:
            raise PersistenceInputError("state is not a Candidate lifecycle state")
        result = self._connection.execute(
            update(tables.candidate)
            .where(tables.candidate.c.candidate_id == candidate_id)
            .values(state=state)
        )
        if result.rowcount != 1:
            raise PersistenceError("candidate not found for state update")


class PostgresCandidateAdmissionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: CandidateAdmissionRecord) -> None:
        _execute_write(
            self._connection,
            tables.candidate_admission.insert().values(
                admission_record_id=record.admission_record_id,
                proposal_id=record.proposal_id,
                research_run_id=record.research_run_id,
                outcome=record.outcome,
                reason_codes=list(record.reason_codes),
                evidence_ids=list(record.evidence_ids),
                admission_policy_version=record.admission_policy_version,
                created_at=record.created_at,
                admitted_candidate_id=record.admitted_candidate_id,
                claim=record.claim,
                classification=record.classification,
            ),
        )

    def get(self, admission_record_id: str) -> CandidateAdmissionRecord | None:
        require_opaque_id(admission_record_id, "admission_record_id")
        return _fetch_one(
            self._connection,
            tables.candidate_admission,
            tables.candidate_admission.c.admission_record_id,
            admission_record_id,
            map_row.candidate_admission_from_row,
        )

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[CandidateAdmissionRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.candidate_admission)
                .where(tables.candidate_admission.c.research_run_id == research_run_id)
                .order_by(tables.candidate_admission.c.admission_record_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.candidate_admission_from_row(row) for row in rows]


class PostgresVerificationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: VerificationRecord) -> None:
        _execute_write(
            self._connection,
            tables.verification.insert().values(
                verification_id=record.verification_id,
                candidate_id=record.candidate_id,
                research_run_id=record.research_run_id,
                strategy=record.strategy,
                outcome=record.outcome,
                proposed_candidate_state=record.proposed_candidate_state,
                original_evidence_ids=list(record.original_evidence_ids),
                reproduction_evidence_ids=list(record.reproduction_evidence_ids),
                negative_control_evidence_ids=list(record.negative_control_evidence_ids),
                alternative_explanation_checks=dict(record.alternative_explanation_checks),
                verifier_kind=record.verifier_kind,
                verifier_identity=record.verifier_identity,
                created_at=record.created_at,
            ),
        )

    def get(self, verification_id: str) -> VerificationRecord | None:
        require_opaque_id(verification_id, "verification_id")
        return _fetch_one(
            self._connection,
            tables.verification,
            tables.verification.c.verification_id,
            verification_id,
            map_row.verification_from_row,
        )

    def list_for_candidate(self, candidate_id: str) -> list[VerificationRecord]:
        require_opaque_id(candidate_id, "candidate_id")
        try:
            rows = self._connection.execute(
                select(tables.verification)
                .where(tables.verification.c.candidate_id == candidate_id)
                .order_by(tables.verification.c.verification_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.verification_from_row(row) for row in rows]

    def list_for_research_run(self, research_run_id: str) -> list[VerificationRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.verification)
                .where(tables.verification.c.research_run_id == research_run_id)
                .order_by(tables.verification.c.verification_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.verification_from_row(row) for row in rows]


class PostgresFindingProposalRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: FindingProposalRecord) -> None:
        _execute_write(
            self._connection,
            tables.finding_proposal.insert().values(
                proposal_id=record.proposal_id,
                candidate_id=record.candidate_id,
                research_run_id=record.research_run_id,
                title=record.title,
                claim=record.claim,
                classification=record.classification,
                state=record.state,
                evidence_ids=list(record.evidence_ids),
                verification_ids=list(record.verification_ids),
                content_fingerprint=record.content_fingerprint,
                created_at=record.created_at,
            ),
        )

    def get(self, proposal_id: str) -> FindingProposalRecord | None:
        require_opaque_id(proposal_id, "proposal_id")
        return _fetch_one(
            self._connection,
            tables.finding_proposal,
            tables.finding_proposal.c.proposal_id,
            proposal_id,
            map_row.finding_proposal_from_row,
        )

    def list_for_candidate(self, candidate_id: str) -> list[FindingProposalRecord]:
        require_opaque_id(candidate_id, "candidate_id")
        try:
            rows = self._connection.execute(
                select(tables.finding_proposal)
                .where(tables.finding_proposal.c.candidate_id == candidate_id)
                .order_by(tables.finding_proposal.c.proposal_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.finding_proposal_from_row(row) for row in rows]

    def list_for_research_run(self, research_run_id: str) -> list[FindingProposalRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.finding_proposal)
                .where(tables.finding_proposal.c.research_run_id == research_run_id)
                .order_by(tables.finding_proposal.c.proposal_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.finding_proposal_from_row(row) for row in rows]

    def set_state(self, proposal_id: str, state: str) -> None:
        require_opaque_id(proposal_id, "proposal_id")
        if state not in ALLOWED_FINDING_PROPOSAL_STATES:
            raise PersistenceInputError("state is not a FindingProposal lifecycle state")
        result = self._connection.execute(
            update(tables.finding_proposal)
            .where(tables.finding_proposal.c.proposal_id == proposal_id)
            .values(state=state)
        )
        if result.rowcount != 1:
            raise PersistenceError("finding_proposal not found for state update")


class PostgresHumanReviewRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: HumanReviewRecord) -> None:
        _execute_write(
            self._connection,
            tables.human_review.insert().values(
                review_id=record.review_id,
                proposal_id=record.proposal_id,
                content_fingerprint=record.content_fingerprint,
                decision=record.decision,
                reviewer_id=record.reviewer_id,
                actor_type=record.actor_type,
                reason_codes=list(record.reason_codes),
                created_at=record.created_at,
                note=record.note,
            ),
        )

    def get(self, review_id: str) -> HumanReviewRecord | None:
        require_opaque_id(review_id, "review_id")
        return _fetch_one(
            self._connection,
            tables.human_review,
            tables.human_review.c.review_id,
            review_id,
            map_row.human_review_from_row,
        )

    def get_for_proposal(self, proposal_id: str) -> HumanReviewRecord | None:
        require_opaque_id(proposal_id, "proposal_id")
        try:
            row = self._connection.execute(
                select(tables.human_review).where(
                    tables.human_review.c.proposal_id == proposal_id
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        if row is None:
            return None
        return map_row.human_review_from_row(row)


class PostgresApprovalRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ApprovalRecord) -> None:
        _execute_write(
            self._connection,
            tables.approval.insert().values(
                approval_id=record.approval_id,
                subject_reference=record.subject_reference,
                decision=record.decision,
                decided_by=record.decided_by,
                actor_type=record.actor_type,
                recorded=record.recorded,
                created_at=record.created_at,
                research_run_id=record.research_run_id,
                proposal_id=record.proposal_id,
                human_review_id=record.human_review_id,
            ),
        )

    def get(self, approval_id: str) -> ApprovalRecord | None:
        require_opaque_id(approval_id, "approval_id")
        return _fetch_one(
            self._connection,
            tables.approval,
            tables.approval.c.approval_id,
            approval_id,
            map_row.approval_from_row,
        )

    def get_by_subject(self, subject_reference: str) -> ApprovalRecord | None:
        require_opaque_id(subject_reference, "subject_reference")
        try:
            row = self._connection.execute(
                select(tables.approval).where(
                    tables.approval.c.subject_reference == subject_reference
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        if row is None:
            return None
        return map_row.approval_from_row(row)


class PostgresFindingRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: FindingRecord) -> None:
        _execute_write(
            self._connection,
            tables.finding.insert().values(
                finding_id=record.finding_id,
                finding_proposal_id=record.finding_proposal_id,
                candidate_id=record.candidate_id,
                research_run_id=record.research_run_id,
                approval_id=record.approval_id,
                human_review_id=record.human_review_id,
                title=record.title,
                claim=record.claim,
                classification=record.classification,
                evidence_ids=list(record.evidence_ids),
                verification_ids=list(record.verification_ids),
                created_at=record.created_at,
            ),
        )

    def get(self, finding_id: str) -> FindingRecord | None:
        require_opaque_id(finding_id, "finding_id")
        return _fetch_one(
            self._connection,
            tables.finding,
            tables.finding.c.finding_id,
            finding_id,
            map_row.finding_from_row,
        )

    def get_by_proposal(self, finding_proposal_id: str) -> FindingRecord | None:
        require_opaque_id(finding_proposal_id, "finding_proposal_id")
        try:
            row = self._connection.execute(
                select(tables.finding).where(
                    tables.finding.c.finding_proposal_id == finding_proposal_id
                )
            ).mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        if row is None:
            return None
        return map_row.finding_from_row(row)

    def list_for_research_run(self, research_run_id: str) -> list[FindingRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.finding)
                .where(tables.finding.c.research_run_id == research_run_id)
                .order_by(tables.finding.c.finding_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.finding_from_row(row) for row in rows]


class PostgresTargetInferenceRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: TargetInferenceRecord) -> None:
        _execute_write(
            self._connection,
            tables.target_inference.insert().values(
                inference_id=record.inference_id,
                research_run_id=record.research_run_id,
                kind=record.kind,
                epistemic_status=record.epistemic_status,
                opaque_ref=record.opaque_ref,
                statement=record.statement,
                source_refs=list(record.source_refs),
                attributes=dict(record.attributes),
                strategy_version=record.strategy_version,
                created_at=record.created_at,
            ),
        )

    def get(self, inference_id: str) -> TargetInferenceRecord | None:
        require_opaque_id(inference_id, "inference_id")
        return _fetch_one(
            self._connection,
            tables.target_inference,
            tables.target_inference.c.inference_id,
            inference_id,
            map_row.target_inference_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[TargetInferenceRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.target_inference)
                .where(tables.target_inference.c.research_run_id == research_run_id)
                .order_by(tables.target_inference.c.inference_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.target_inference_from_row(row) for row in rows]


class PostgresDifferentialObservationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: DifferentialObservationRecord) -> None:
        _execute_write(
            self._connection,
            tables.differential_observation.insert().values(
                differential_id=record.differential_id,
                research_run_id=record.research_run_id,
                case_id=record.case_id,
                baseline_observation_ids=list(record.baseline_observation_ids),
                variant_observation_ids=list(record.variant_observation_ids),
                changed_dimensions=list(record.changed_dimensions),
                common_dimensions=list(record.common_dimensions),
                observed_differences=dict(record.observed_differences),
                observed_similarities=dict(record.observed_similarities),
                interpretation=record.interpretation,
                source_refs=list(record.source_refs),
                strategy_version=record.strategy_version,
                alternative_explanation_slots=list(record.alternative_explanation_slots),
                created_at=record.created_at,
            ),
        )

    def get(self, differential_id: str) -> DifferentialObservationRecord | None:
        require_opaque_id(differential_id, "differential_id")
        return _fetch_one(
            self._connection,
            tables.differential_observation,
            tables.differential_observation.c.differential_id,
            differential_id,
            map_row.differential_observation_from_row,
        )

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[DifferentialObservationRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.differential_observation)
                .where(tables.differential_observation.c.research_run_id == research_run_id)
                .order_by(tables.differential_observation.c.differential_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.differential_observation_from_row(row) for row in rows]


class PostgresInvariantHypothesisRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: InvariantHypothesisRecord) -> None:
        _execute_write(
            self._connection,
            tables.invariant_hypothesis.insert().values(
                invariant_id=record.invariant_id,
                research_run_id=record.research_run_id,
                invariant_kind=record.invariant_kind,
                status=record.status,
                subject_refs=list(record.subject_refs),
                expected_behavior=record.expected_behavior,
                source_refs=list(record.source_refs),
                applicability_context=dict(record.applicability_context),
                assumptions=list(record.assumptions),
                counterexample_refs=list(record.counterexample_refs),
                falsification_direction=record.falsification_direction,
                proposer_provenance=record.proposer_provenance,
                strategy_version=record.strategy_version,
                created_at=record.created_at,
            ),
        )
        for source_ref in record.source_refs:
            _execute_write(
                self._connection,
                tables.invariant_source_ref.insert().values(
                    invariant_id=record.invariant_id,
                    source_ref=source_ref,
                    created_at=record.created_at,
                ),
            )

    def get(self, invariant_id: str) -> InvariantHypothesisRecord | None:
        require_opaque_id(invariant_id, "invariant_id")
        return _fetch_one(
            self._connection,
            tables.invariant_hypothesis,
            tables.invariant_hypothesis.c.invariant_id,
            invariant_id,
            map_row.invariant_hypothesis_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[InvariantHypothesisRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.invariant_hypothesis)
                .where(tables.invariant_hypothesis.c.research_run_id == research_run_id)
                .order_by(tables.invariant_hypothesis.c.invariant_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.invariant_hypothesis_from_row(row) for row in rows]

    def set_state(self, invariant_id: str, state: str) -> None:
        require_opaque_id(invariant_id, "invariant_id")
        if state not in ALLOWED_INVARIANT_STATUSES:
            raise PersistenceInputError("status is not an invariant hypothesis status")
        result = self._connection.execute(
            update(tables.invariant_hypothesis)
            .where(tables.invariant_hypothesis.c.invariant_id == invariant_id)
            .values(status=state)
        )
        if result.rowcount != 1:
            raise PersistenceError("invariant hypothesis not found for state update")

    def add_counterexample(self, record: InvariantCounterexampleRefRecord) -> None:
        current = self.get(record.invariant_id)
        if current is None:
            raise PersistenceError("invariant hypothesis not found for counterexample")
        refs = current.counterexample_refs
        if record.source_ref not in refs:
            refs = refs + (record.source_ref,)
        _execute_write(
            self._connection,
            tables.invariant_counterexample_ref.insert().values(
                counterexample_id=record.counterexample_id,
                invariant_id=record.invariant_id,
                source_ref=record.source_ref,
                applicability_context=dict(record.applicability_context),
                created_at=record.created_at,
            ),
        )
        result = self._connection.execute(
            update(tables.invariant_hypothesis)
            .where(tables.invariant_hypothesis.c.invariant_id == record.invariant_id)
            .values(status="CHALLENGED", counterexample_refs=list(refs))
        )
        if result.rowcount != 1:
            raise PersistenceError("invariant hypothesis not found for counterexample")


class PostgresChainHypothesisRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ChainHypothesisRecord) -> None:
        _execute_write(
            self._connection,
            tables.chain_hypothesis.insert().values(
                chain_id=record.chain_id,
                research_run_id=record.research_run_id,
                structural_identity=record.structural_identity,
                steps=[dict(step) for step in record.steps],
                source_refs=list(record.source_refs),
                preconditions=list(record.preconditions),
                expected_resulting_capability=record.expected_resulting_capability,
                unresolved_assumptions=list(record.unresolved_assumptions),
                falsification_points=list(record.falsification_points),
                descriptive_features=dict(record.descriptive_features),
                strategy_version=record.strategy_version,
                created_at=record.created_at,
            ),
        )

    def get(self, chain_id: str) -> ChainHypothesisRecord | None:
        require_opaque_id(chain_id, "chain_id")
        return _fetch_one(
            self._connection,
            tables.chain_hypothesis,
            tables.chain_hypothesis.c.chain_id,
            chain_id,
            map_row.chain_hypothesis_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[ChainHypothesisRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.chain_hypothesis)
                .where(tables.chain_hypothesis.c.research_run_id == research_run_id)
                .order_by(tables.chain_hypothesis.c.chain_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.chain_hypothesis_from_row(row) for row in rows]


class PostgresResearchOpportunityRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchOpportunityRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_opportunity.insert().values(
                opportunity_id=record.opportunity_id,
                research_run_id=record.research_run_id,
                opportunity_kind=record.opportunity_kind,
                mode=record.mode,
                source_refs=list(record.source_refs),
                proposed_direction=record.proposed_direction,
                unresolved_question=record.unresolved_question,
                expected_information_value_description=record.expected_information_value_description,
                assumptions=list(record.assumptions),
                dimensions=dict(record.dimensions),
                context_signature=record.context_signature,
                novelty_composition_marker=record.novelty_composition_marker,
                prior_attempt_refs=list(record.prior_attempt_refs),
                structural_identity=record.structural_identity,
                strategy_version=record.strategy_version,
                created_at=record.created_at,
            ),
        )

    def get(self, opportunity_id: str) -> ResearchOpportunityRecord | None:
        require_opaque_id(opportunity_id, "opportunity_id")
        return _fetch_one(
            self._connection,
            tables.research_opportunity,
            tables.research_opportunity.c.opportunity_id,
            opportunity_id,
            map_row.research_opportunity_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[ResearchOpportunityRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.research_opportunity)
                .where(tables.research_opportunity.c.research_run_id == research_run_id)
                .order_by(tables.research_opportunity.c.opportunity_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.research_opportunity_from_row(row) for row in rows]


class PostgresResearchSelectionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchSelectionRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_selection.insert().values(
                selection_id=record.selection_id,
                research_run_id=record.research_run_id,
                opportunity_id=record.opportunity_id,
                outcome=record.outcome,
                reason_codes=list(record.reason_codes),
                structural_identity=record.structural_identity,
                created_at=record.created_at,
            ),
        )

    def list_for_research_run(self, research_run_id: str) -> list[ResearchSelectionRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.research_selection)
                .where(tables.research_selection.c.research_run_id == research_run_id)
                .order_by(tables.research_selection.c.selection_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.research_selection_from_row(row) for row in rows]


class PostgresSnapshotRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: SnapshotRecord, members: tuple[SnapshotMemberRecord, ...]) -> None:
        _execute_write(
            self._connection,
            tables.snapshot.insert().values(
                snapshot_id=record.snapshot_id,
                research_run_id=record.research_run_id,
                program_id=record.program_id,
                target_identity=record.target_identity,
                captured_at=record.captured_at,
                strategy_version=record.strategy_version,
                created_at=record.created_at,
            ),
        )
        for member in members:
            _execute_write(
                self._connection,
                tables.snapshot_member.insert().values(
                    snapshot_id=member.snapshot_id,
                    observation_id=member.observation_id,
                    created_at=member.created_at,
                ),
            )

    def get(self, snapshot_id: str) -> SnapshotRecord | None:
        require_opaque_id(snapshot_id, "snapshot_id")
        return _fetch_one(
            self._connection,
            tables.snapshot,
            tables.snapshot.c.snapshot_id,
            snapshot_id,
            map_row.snapshot_from_row,
        )

    def list_members(self, snapshot_id: str) -> list[SnapshotMemberRecord]:
        require_opaque_id(snapshot_id, "snapshot_id")
        try:
            rows = self._connection.execute(
                select(tables.snapshot_member)
                .where(tables.snapshot_member.c.snapshot_id == snapshot_id)
                .order_by(tables.snapshot_member.c.observation_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.snapshot_member_from_row(row) for row in rows]

    def list_for_research_run(self, research_run_id: str) -> list[SnapshotRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.snapshot)
                .where(tables.snapshot.c.research_run_id == research_run_id)
                .order_by(tables.snapshot.c.captured_at, tables.snapshot.c.snapshot_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.snapshot_from_row(row) for row in rows]


class PostgresChangeEventRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ChangeEventRecord) -> None:
        _execute_write(
            self._connection,
            tables.change_event.insert().values(
                change_event_id=record.change_event_id,
                research_run_id=record.research_run_id,
                baseline_snapshot_id=record.baseline_snapshot_id,
                variant_snapshot_id=record.variant_snapshot_id,
                category=record.category,
                statement=record.statement,
                source_refs=list(record.source_refs),
                strategy_version=record.strategy_version,
                created_at=record.created_at,
            ),
        )

    def get(self, change_event_id: str) -> ChangeEventRecord | None:
        require_opaque_id(change_event_id, "change_event_id")
        return _fetch_one(
            self._connection,
            tables.change_event,
            tables.change_event.c.change_event_id,
            change_event_id,
            map_row.change_event_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[ChangeEventRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.change_event)
                .where(tables.change_event.c.research_run_id == research_run_id)
                .order_by(tables.change_event.c.change_event_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.change_event_from_row(row) for row in rows]


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


class PostgresResearchOrchestrationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchOrchestrationRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_orchestration.insert().values(
                **_orchestration_values(record)
            ),
        )

    def get(self, research_run_id: str) -> ResearchOrchestrationRecord | None:
        require_opaque_id(research_run_id, "research_run_id")
        return _fetch_one(
            self._connection,
            tables.research_orchestration,
            tables.research_orchestration.c.research_run_id,
            research_run_id,
            map_row.research_orchestration_from_row,
        )

    def save(self, record: ResearchOrchestrationRecord) -> None:
        require_opaque_id(record.research_run_id, "research_run_id")
        values = _orchestration_values(record)
        values.pop("research_run_id")
        try:
            result = self._connection.execute(
                update(tables.research_orchestration)
                .where(
                    tables.research_orchestration.c.research_run_id
                    == record.research_run_id
                )
                .values(**values)
            )
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence write failed") from exc
        if result.rowcount != 1:
            raise PersistenceError("research_orchestration not found for checkpoint")


class PostgresResearchCycleRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: ResearchCycleRecord) -> None:
        _execute_write(
            self._connection,
            tables.research_cycle.insert().values(
                cycle_id=record.cycle_id,
                research_run_id=record.research_run_id,
                cycle_number=record.cycle_number,
                phase_completed=record.phase_completed,
                outcome=record.outcome,
                stop_reason=record.stop_reason,
                opportunity_id=record.opportunity_id,
                hypothesis_id=record.hypothesis_id,
                experiment_id=record.experiment_id,
                created_at=record.created_at,
            ),
        )

    def get(self, cycle_id: str) -> ResearchCycleRecord | None:
        require_opaque_id(cycle_id, "cycle_id")
        return _fetch_one(
            self._connection,
            tables.research_cycle,
            tables.research_cycle.c.cycle_id,
            cycle_id,
            map_row.research_cycle_from_row,
        )

    def list_for_research_run(self, research_run_id: str) -> list[ResearchCycleRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.research_cycle)
                .where(tables.research_cycle.c.research_run_id == research_run_id)
                .order_by(tables.research_cycle.c.cycle_number)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.research_cycle_from_row(row) for row in rows]


class PostgresBudgetConsumptionRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: BudgetConsumptionRecord) -> None:
        _execute_write(
            self._connection,
            tables.budget_consumption.insert().values(**_consumption_values(record)),
        )

    def insert_within_allowance(
        self,
        record: BudgetConsumptionRecord,
        issued: IssuedBudgetRecord,
    ) -> None:
        del issued
        try:
            locked = self._connection.execute(
                select(tables.issued_budget)
                .where(tables.issued_budget.c.budget_id == record.budget_id)
                .with_for_update()
            ).mappings().one_or_none()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        if locked is None:
            raise PersistenceError("issued budget not found for consumption")
        mapped_issued = map_row.issued_budget_from_row(locked)
        if mapped_issued.budget_id != record.budget_id:
            raise PersistenceError("locked budget id mismatch")
        if mapped_issued.research_run_id != record.research_run_id:
            raise PersistenceError("locked budget research_run_id mismatch")
        existing = self.list_for_budget(record.budget_id)
        if any(
            item.request_id == record.request_id
            and item.resource_type == record.resource_type
            and record.request_id is not None
            for item in existing
        ):
            return
        orchestration = None
        if record.resource_type == "MODEL_CALL":
            try:
                orch_row = self._connection.execute(
                    select(tables.research_orchestration)
                    .where(
                        tables.research_orchestration.c.research_run_id
                        == record.research_run_id
                    )
                    .with_for_update()
                ).mappings().one_or_none()
            except SQLAlchemyError as exc:
                raise PersistenceError("persistence read failed") from exc
            if orch_row is None:
                raise BudgetOverspendError("MODEL_CALL requires locked orchestration allowance")
            orchestration = map_row.research_orchestration_from_row(orch_row)
        assert_within_allowance(
            mapped_issued, existing, record, orchestration=orchestration
        )
        try:
            self.insert(record)
        except PersistenceConflictError:
            return

    def get(self, consumption_id: str) -> BudgetConsumptionRecord | None:
        require_opaque_id(consumption_id, "consumption_id")
        return _fetch_one(
            self._connection,
            tables.budget_consumption,
            tables.budget_consumption.c.consumption_id,
            consumption_id,
            map_row.budget_consumption_from_row,
        )

    def list_for_budget(self, budget_id: str) -> list[BudgetConsumptionRecord]:
        require_opaque_id(budget_id, "budget_id")
        try:
            rows = self._connection.execute(
                select(tables.budget_consumption)
                .where(tables.budget_consumption.c.budget_id == budget_id)
                .order_by(tables.budget_consumption.c.consumption_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.budget_consumption_from_row(row) for row in rows]

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[BudgetConsumptionRecord]:
        require_opaque_id(research_run_id, "research_run_id")
        try:
            rows = self._connection.execute(
                select(tables.budget_consumption)
                .where(tables.budget_consumption.c.research_run_id == research_run_id)
                .order_by(tables.budget_consumption.c.consumption_id)
            ).mappings().all()
        except SQLAlchemyError as exc:
            raise PersistenceError("persistence read failed") from exc
        return [map_row.budget_consumption_from_row(row) for row in rows]


def _orchestration_values(record: ResearchOrchestrationRecord) -> dict[str, object]:
    return {
        "research_run_id": record.research_run_id,
        "state": record.state,
        "cycle_number": record.cycle_number,
        "last_phase": record.last_phase,
        "last_opportunity_id": record.last_opportunity_id,
        "last_hypothesis_id": record.last_hypothesis_id,
        "last_experiment_id": record.last_experiment_id,
        "pause_reason": record.pause_reason,
        "stop_reason": record.stop_reason,
        "policy_version": record.policy_version,
        "max_cycles": record.max_cycles,
        "max_experiments": record.max_experiments,
        "max_model_calls": record.max_model_calls,
        "max_worker_invocations": record.max_worker_invocations,
        "max_elapsed_ms": record.max_elapsed_ms,
        "max_selected_opportunities": record.max_selected_opportunities,
        "max_runtime_fallback": record.max_runtime_fallback,
        "side_effect_ceiling": record.side_effect_ceiling,
        "allow_repeated_control_experiments": record.allow_repeated_control_experiments,
        "budget_id": record.budget_id,
        "target_reference": record.target_reference,
        "research_question": record.research_question,
        "configuration_fingerprint": record.configuration_fingerprint,
        "current_phase": record.current_phase,
        "active_cycle_id": record.active_cycle_id,
        "last_attempt_id": record.last_attempt_id,
        "last_observation_id": record.last_observation_id,
        "last_assessment_id": record.last_assessment_id,
        "last_worker_result_id": record.last_worker_result_id,
        "routing_policy_version": record.routing_policy_version,
        "scope_fingerprint": record.scope_fingerprint,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "checkpoint_at": record.checkpoint_at,
    }


def _consumption_values(record: BudgetConsumptionRecord) -> dict[str, object]:
    return {
        "consumption_id": record.consumption_id,
        "budget_id": record.budget_id,
        "research_run_id": record.research_run_id,
        "experiment_id": record.experiment_id,
        "request_id": record.request_id,
        "resource_type": record.resource_type,
        "amount": record.amount,
        "unit": record.unit,
        "occurred_at": record.occurred_at,
        "provenance": record.provenance,
    }


class PostgresSessionContextRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert(self, record: SessionContextRecord) -> None:
        _execute_write(
            self._connection,
            tables.session_context.insert().values(
                session_context_id=record.session_context_id,
                research_run_id=record.research_run_id,
                identity_id=record.identity_id,
                actor_reference=record.actor_reference,
                origin=record.origin,
                authentication_profile_reference=record.authentication_profile_reference,
                authentication_method=record.authentication_method,
                secret_scheme=record.secret_scheme,
                secret_name=record.secret_name,
                state=record.state,
                created_at=record.created_at,
                updated_at=record.updated_at,
                established_at=record.established_at,
                expires_at=record.expires_at,
                session_cookie_name=record.session_cookie_name,
            ),
        )

    def get(self, session_context_id: str) -> SessionContextRecord | None:
        require_opaque_id(session_context_id, "session_context_id")
        return _fetch_one(
            self._connection,
            tables.session_context,
            tables.session_context.c.session_context_id,
            session_context_id,
            map_row.session_context_from_row,
        )

    def set_state(
        self,
        session_context_id: str,
        state: str,
        *,
        established_at: datetime | None = None,
        expires_at: datetime | None = None,
        updated_at: datetime,
    ) -> None:
        require_opaque_id(session_context_id, "session_context_id")
        if state not in ALLOWED_SESSION_STATES:
            raise PersistenceInputError("state is not a SessionContext state")
        values: dict[str, object] = {"state": state, "updated_at": updated_at}
        if established_at is not None:
            values["established_at"] = established_at
        if expires_at is not None:
            values["expires_at"] = expires_at
        result = self._connection.execute(
            update(tables.session_context)
            .where(tables.session_context.c.session_context_id == session_context_id)
            .values(**values)
        )
        if result.rowcount != 1:
            raise PersistenceError("session_context not found for state update")

