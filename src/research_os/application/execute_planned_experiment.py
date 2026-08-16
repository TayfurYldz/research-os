"""Execute a planned Experiment through Core, durable attempt, Worker, Transition A.

This is the A7-lite control-loop skeleton. It is not a Research Brain.
It does not call a model, create Evidence, or update Hypothesis truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from research_os.application.identity import (
    attempt_id_for,
    execution_decision_audit_id,
    new_opaque_id,
)
from research_os.application.ingest_worker_invocation import (
    CONTROL_PLANE_ACTOR_ID,
    IngestCompletedWorkerInvocation,
    IngestionOutcome,
    IngestionStatus,
)
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.core.approval import ApprovalView
from research_os.core.authorization import AuthorizationSourceView
from research_os.core.budget import BudgetUsage, IssuedBudget
from research_os.core.enums import (
    ActorType,
    AuthorizationSourceState,
    ExecutionDecisionKind,
    ReasonCode,
)
from research_os.core.execution import ExecutionDecision, ExecutionRequest, evaluate_execution
from research_os.core.scope import ScopeEvaluationInput
from research_os.data.errors import PersistenceError
from research_os.data.records import (
    AuditEventRecord,
    AuthorizationSourceRecord,
    ExecutionAttemptRecord,
    ExecutionAttemptState,
    ExperimentExecutionState,
    ExperimentRecord,
    IssuedBudgetRecord,
)
from research_os.data.unit_of_work import UnitOfWork
from research_os.platform.contract_validation import ContractValidator
from research_os.platform.worker import InvocationStatus, WorkerInvocationOutcome, WorkerPort
from research_os.research.types import ExperimentPlan

WORKER_CONTRACT_VERSION = "v1"
AUDIT_EXECUTION_DECISION = "EXECUTION_DECISION"
BUDGET_CONSUMPTION_LEDGER_IMPLEMENTED = False

TERMINAL_EXPERIMENT_STATES = frozenset(
    {
        ExperimentExecutionState.EXECUTION_SUCCEEDED.value,
        ExperimentExecutionState.EXECUTION_FAILED.value,
        ExperimentExecutionState.BLOCKED.value,
        ExperimentExecutionState.CANCELLED.value,
        ExperimentExecutionState.BUDGET_EXHAUSTED.value,
    }
)

FAILED_INVOCATION_STATUSES = frozenset(
    {
        InvocationStatus.START_FAILED,
        InvocationStatus.PROCESS_FAILED,
        InvocationStatus.PROTOCOL_ERROR,
        InvocationStatus.CONTRACT_INVALID,
    }
)


class ResearchLoopStatus(Enum):
    """Control-loop outcome. Not a vulnerability verdict. Not Hypothesis belief."""

    OBSERVATION_PRODUCED = "OBSERVATION_PRODUCED"
    NO_OBSERVATION = "NO_OBSERVATION"
    DISPATCH_DENIED = "DISPATCH_DENIED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    INVOCATION_FAILED = "INVOCATION_FAILED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    AUTHORIZED_NOT_DISPATCHED = "AUTHORIZED_NOT_DISPATCHED"
    ALREADY_TERMINAL = "ALREADY_TERMINAL"
    INPUT_REJECTED = "INPUT_REJECTED"


@dataclass(frozen=True)
class ExecutePlannedExperimentCommand:
    experiment_id: str
    plan: ExperimentPlan
    scope: ScopeEvaluationInput
    approval: ApprovalView | None = None
    budget_usage: BudgetUsage | None = None


@dataclass(frozen=True)
class AuthorizedDispatch:
    """In-process handle after TX1 AUTHORIZED intent. Not a WorkerResult."""

    experiment_id: str
    hypothesis_id: str
    request_id: str
    attempt_id: str
    correlation_id: str
    authorization_decision_reference: str
    worker_request: Mapping[str, Any]
    timeout_ms: int
    core_decision: ExecutionDecisionKind
    core_reason_code: ReasonCode


@dataclass(frozen=True)
class ResearchLoopOutcome:
    status: ResearchLoopStatus
    hypothesis_id: str
    experiment_id: str
    experiment_execution_state: str
    core_decision: ExecutionDecisionKind | None = None
    core_reason_code: ReasonCode | None = None
    authorization_decision_reference: str | None = None
    request_id: str | None = None
    attempt_id: str | None = None
    attempt_state: str | None = None
    invocation_status: InvocationStatus | None = None
    worker_result_id: str | None = None
    observation_ids: tuple[str, ...] = ()
    ingestion_status: IngestionStatus | None = None
    hypothesis_claim_unchanged: bool = True


class ExecutePlannedExperiment:
    """Hypothesis/Experiment → Core → durable attempt → WorkerPort → Transition A."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        worker: WorkerPort,
        *,
        ingest: IngestCompletedWorkerInvocation | None = None,
        clock: Clock | None = None,
        validator: ContractValidator | None = None,
        actor_id: str = CONTROL_PLANE_ACTOR_ID,
    ) -> None:
        self._uow_factory = uow_factory
        self._worker = worker
        self._clock = clock or SystemClock()
        self._validator = validator or ContractValidator()
        self._actor_id = actor_id
        self._ingest = ingest or IngestCompletedWorkerInvocation(
            uow_factory, validator=self._validator, clock=self._clock, actor_id=actor_id
        )

    def execute(self, command: ExecutePlannedExperimentCommand) -> ResearchLoopOutcome:
        existing = self._fail_closed_existing(command.experiment_id)
        if existing is not None:
            return existing
        authorized = self.authorize(command)
        if isinstance(authorized, ResearchLoopOutcome):
            return authorized
        return self.dispatch(authorized)

    def authorize(
        self, command: ExecutePlannedExperimentCommand
    ) -> AuthorizedDispatch | ResearchLoopOutcome:
        request_id = new_opaque_id()
        correlation_id = new_opaque_id()
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            loaded = self._load_context(uow, command)
            if isinstance(loaded, ResearchLoopOutcome):
                return loaded
            experiment, hypothesis_id, source, issued = loaded
            existing_attempts = uow.execution_attempts.list_for_experiment(
                experiment.experiment_id
            )
            if existing_attempts:
                uow.rollback()
                return self._outcome_for_existing(experiment, hypothesis_id, existing_attempts[0])
            uow.experiments.set_execution_state(
                experiment.experiment_id,
                ExperimentExecutionState.AUTHORIZATION_CHECK.value,
            )
            decision = evaluate_execution(
                ExecutionRequest(
                    authorization_source=source,
                    scope=command.scope,
                    issued_budget=_issued_budget_from_record(issued),
                    budget_usage=command.budget_usage or BudgetUsage(0, 0, 0, 0),
                    requested_budget_id=command.plan.requested_budget_id,
                    side_effect_level=command.plan.side_effect_level,
                    requested_subject=command.plan.target_reference,
                    approval=command.approval,
                )
            )
            audit_id = execution_decision_audit_id(request_id)
            uow.audit_events.insert(
                _execution_decision_audit(
                    audit_id=audit_id,
                    occurred_at=now,
                    actor_id=self._actor_id,
                    experiment_id=experiment.experiment_id,
                    correlation_id=correlation_id,
                    request_id=request_id,
                    decision=decision,
                )
            )
            if decision.decision is ExecutionDecisionKind.DENY:
                terminal = _deny_experiment_state(decision.reason_code)
                uow.experiments.set_execution_state(experiment.experiment_id, terminal)
                uow.commit()
                return ResearchLoopOutcome(
                    status=ResearchLoopStatus.DISPATCH_DENIED,
                    hypothesis_id=hypothesis_id,
                    experiment_id=experiment.experiment_id,
                    experiment_execution_state=terminal,
                    core_decision=decision.decision,
                    core_reason_code=decision.reason_code,
                    authorization_decision_reference=audit_id,
                    request_id=None,
                    attempt_id=None,
                    attempt_state=None,
                )
            if decision.decision is ExecutionDecisionKind.REQUIRE_HUMAN_REVIEW:
                uow.commit()
                return ResearchLoopOutcome(
                    status=ResearchLoopStatus.HUMAN_REVIEW_REQUIRED,
                    hypothesis_id=hypothesis_id,
                    experiment_id=experiment.experiment_id,
                    experiment_execution_state=ExperimentExecutionState.AUTHORIZATION_CHECK.value,
                    core_decision=decision.decision,
                    core_reason_code=decision.reason_code,
                    authorization_decision_reference=audit_id,
                    request_id=None,
                    attempt_id=None,
                    attempt_state=None,
                )
            worker_request = _build_worker_request(
                experiment=experiment,
                plan=command.plan,
                issued=issued,
                request_id=request_id,
                correlation_id=correlation_id,
                authorization_decision_reference=audit_id,
            )
            self._validator.validate_worker_request(worker_request)
            attempt_id = attempt_id_for(request_id)
            uow.execution_attempts.insert(
                ExecutionAttemptRecord(
                    attempt_id=attempt_id,
                    request_id=request_id,
                    experiment_id=experiment.experiment_id,
                    research_run_id=experiment.research_run_id,
                    correlation_id=correlation_id,
                    worker_capability=command.plan.required_capability,
                    action=command.plan.action,
                    target_reference=command.plan.target_reference,
                    budget_id=issued.budget_id,
                    side_effect_level=command.plan.side_effect_level,
                    authorization_decision_reference=audit_id,
                    state=ExecutionAttemptState.AUTHORIZED.value,
                    created_at=now,
                    authorized_at=now,
                )
            )
            uow.experiments.set_execution_state(
                experiment.experiment_id,
                ExperimentExecutionState.READY.value,
            )
            uow.commit()
        return AuthorizedDispatch(
            experiment_id=experiment.experiment_id,
            hypothesis_id=hypothesis_id,
            request_id=request_id,
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            authorization_decision_reference=audit_id,
            worker_request=worker_request,
            timeout_ms=issued.max_runtime_ms,
            core_decision=decision.decision,
            core_reason_code=decision.reason_code,
        )

    def dispatch(self, authorized: AuthorizedDispatch) -> ResearchLoopOutcome:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            attempt = uow.execution_attempts.get(authorized.attempt_id)
            experiment = uow.experiments.get(authorized.experiment_id)
            if attempt is None or experiment is None:
                return ResearchLoopOutcome(
                    status=ResearchLoopStatus.INPUT_REJECTED,
                    hypothesis_id=authorized.hypothesis_id,
                    experiment_id=authorized.experiment_id,
                    experiment_execution_state=(
                        experiment.execution_state if experiment is not None else "MISSING"
                    ),
                    request_id=authorized.request_id,
                    attempt_id=authorized.attempt_id,
                )
            if attempt.state != ExecutionAttemptState.AUTHORIZED.value:
                if attempt.state == ExecutionAttemptState.DISPATCHING.value:
                    return self._mark_unknown(uow, experiment, attempt, authorized.hypothesis_id)
                return self._outcome_for_existing(experiment, authorized.hypothesis_id, attempt)
            uow.execution_attempts.set_state(
                attempt.attempt_id,
                ExecutionAttemptState.DISPATCHING.value,
                dispatch_started_at=now,
            )
            uow.experiments.set_execution_state(
                experiment.experiment_id,
                ExperimentExecutionState.RUNNING.value,
            )
            uow.commit()
        invocation = self._worker.invoke(
            authorized.worker_request,
            timeout_ms=authorized.timeout_ms,
        )
        return self._record_outcome(authorized, invocation)

    def _fail_closed_existing(self, experiment_id: str) -> ResearchLoopOutcome | None:
        with self._uow_factory.open() as uow:
            experiment = uow.experiments.get(experiment_id)
            if experiment is None:
                return ResearchLoopOutcome(
                    status=ResearchLoopStatus.INPUT_REJECTED,
                    hypothesis_id="",
                    experiment_id=experiment_id,
                    experiment_execution_state="MISSING",
                )
            attempts = uow.execution_attempts.list_for_experiment(experiment_id)
            if not attempts:
                if experiment.execution_state in TERMINAL_EXPERIMENT_STATES:
                    return ResearchLoopOutcome(
                        status=ResearchLoopStatus.ALREADY_TERMINAL,
                        hypothesis_id=experiment.hypothesis_id,
                        experiment_id=experiment.experiment_id,
                        experiment_execution_state=experiment.execution_state,
                    )
                return None
            attempt = attempts[0]
            if attempt.state == ExecutionAttemptState.DISPATCHING.value:
                return self._mark_unknown(uow, experiment, attempt, experiment.hypothesis_id)
            return self._outcome_for_existing(experiment, experiment.hypothesis_id, attempt)

    def _mark_unknown(
        self,
        uow: UnitOfWork,
        experiment: ExperimentRecord,
        attempt: ExecutionAttemptRecord,
        hypothesis_id: str,
    ) -> ResearchLoopOutcome:
        now = self._clock.now()
        uow.execution_attempts.set_state(
            attempt.attempt_id,
            ExecutionAttemptState.UNKNOWN_OUTCOME.value,
            completed_at=now,
        )
        uow.commit()
        return ResearchLoopOutcome(
            status=ResearchLoopStatus.UNKNOWN_OUTCOME,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment.experiment_id,
            experiment_execution_state=experiment.execution_state,
            authorization_decision_reference=attempt.authorization_decision_reference,
            request_id=attempt.request_id,
            attempt_id=attempt.attempt_id,
            attempt_state=ExecutionAttemptState.UNKNOWN_OUTCOME.value,
        )

    def _record_outcome(
        self,
        authorized: AuthorizedDispatch,
        invocation: WorkerInvocationOutcome,
    ) -> ResearchLoopOutcome:
        now = self._clock.now()
        attempt_state, experiment_state, loop_status = _classify_invocation(invocation)
        ingestion: IngestionOutcome | None = None
        persist_failed = False
        try:
            with self._uow_factory.open() as uow:
                uow.execution_attempts.set_state(
                    authorized.attempt_id,
                    attempt_state,
                    completed_at=now,
                )
                uow.experiments.set_execution_state(
                    authorized.experiment_id,
                    experiment_state,
                )
                uow.commit()
        except PersistenceError:
            persist_failed = True
            loop_status = ResearchLoopStatus.INVOCATION_FAILED
            experiment_state = ExperimentExecutionState.RUNNING.value
            attempt_state = ExecutionAttemptState.DISPATCHING.value
        if (
            not persist_failed
            and invocation.invocation_status is InvocationStatus.COMPLETED
            and invocation.worker_result is not None
        ):
            ingestion = self._ingest.execute(authorized.worker_request, invocation)
            if ingestion.status is IngestionStatus.REJECTED_INVALID_INVOCATION:
                loop_status = ResearchLoopStatus.INVOCATION_FAILED
                experiment_state = ExperimentExecutionState.EXECUTION_FAILED.value
                attempt_state = ExecutionAttemptState.FAILED.value
                with self._uow_factory.open() as uow:
                    uow.execution_attempts.set_state(
                        authorized.attempt_id,
                        attempt_state,
                        completed_at=now,
                    )
                    uow.experiments.set_execution_state(
                        authorized.experiment_id,
                        experiment_state,
                    )
                    uow.commit()
            elif ingestion.status is IngestionStatus.NO_OBSERVATION:
                loop_status = ResearchLoopStatus.NO_OBSERVATION
            elif ingestion.status in {
                IngestionStatus.INGESTED,
                IngestionStatus.ALREADY_INGESTED,
            }:
                loop_status = ResearchLoopStatus.OBSERVATION_PRODUCED
        return ResearchLoopOutcome(
            status=loop_status,
            hypothesis_id=authorized.hypothesis_id,
            experiment_id=authorized.experiment_id,
            experiment_execution_state=experiment_state,
            core_decision=authorized.core_decision,
            core_reason_code=authorized.core_reason_code,
            authorization_decision_reference=authorized.authorization_decision_reference,
            request_id=authorized.request_id,
            attempt_id=authorized.attempt_id,
            attempt_state=attempt_state,
            invocation_status=invocation.invocation_status,
            worker_result_id=None if ingestion is None else ingestion.worker_result_id,
            observation_ids=() if ingestion is None else ingestion.observation_ids,
            ingestion_status=None if ingestion is None else ingestion.status,
        )

    def _load_context(
        self,
        uow: UnitOfWork,
        command: ExecutePlannedExperimentCommand,
    ) -> (
        tuple[
            ExperimentRecord,
            str,
            AuthorizationSourceView | None,
            IssuedBudgetRecord,
        ]
        | ResearchLoopOutcome
    ):
        experiment = uow.experiments.get(command.experiment_id)
        if experiment is None:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.INPUT_REJECTED,
                hypothesis_id=command.plan.hypothesis_id,
                experiment_id=command.experiment_id,
                experiment_execution_state="MISSING",
            )
        if experiment.execution_state in TERMINAL_EXPERIMENT_STATES:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.ALREADY_TERMINAL,
                hypothesis_id=experiment.hypothesis_id,
                experiment_id=experiment.experiment_id,
                experiment_execution_state=experiment.execution_state,
            )
        if experiment.hypothesis_id != command.plan.hypothesis_id:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.INPUT_REJECTED,
                hypothesis_id=experiment.hypothesis_id,
                experiment_id=experiment.experiment_id,
                experiment_execution_state=experiment.execution_state,
            )
        if experiment.budget_id != command.plan.requested_budget_id:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.INPUT_REJECTED,
                hypothesis_id=experiment.hypothesis_id,
                experiment_id=experiment.experiment_id,
                experiment_execution_state=experiment.execution_state,
            )
        hypothesis = uow.hypotheses.get(experiment.hypothesis_id)
        if hypothesis is None:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.INPUT_REJECTED,
                hypothesis_id=experiment.hypothesis_id,
                experiment_id=experiment.experiment_id,
                experiment_execution_state=experiment.execution_state,
            )
        run = uow.research_runs.get(experiment.research_run_id)
        if run is None:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.INPUT_REJECTED,
                hypothesis_id=experiment.hypothesis_id,
                experiment_id=experiment.experiment_id,
                experiment_execution_state=experiment.execution_state,
            )
        issued = uow.issued_budgets.get(experiment.budget_id)
        if issued is None:
            return ResearchLoopOutcome(
                status=ResearchLoopStatus.INPUT_REJECTED,
                hypothesis_id=experiment.hypothesis_id,
                experiment_id=experiment.experiment_id,
                experiment_execution_state=experiment.execution_state,
            )
        source_record = uow.authorization_sources.get(run.authorization_source_id)
        return (
            experiment,
            hypothesis.hypothesis_id,
            _authorization_view(source_record),
            issued,
        )

    def _outcome_for_existing(
        self,
        experiment: ExperimentRecord,
        hypothesis_id: str,
        attempt: ExecutionAttemptRecord,
    ) -> ResearchLoopOutcome:
        if attempt.state == ExecutionAttemptState.AUTHORIZED.value:
            status = ResearchLoopStatus.AUTHORIZED_NOT_DISPATCHED
        elif attempt.state == ExecutionAttemptState.UNKNOWN_OUTCOME.value:
            status = ResearchLoopStatus.UNKNOWN_OUTCOME
        elif experiment.execution_state in TERMINAL_EXPERIMENT_STATES:
            status = ResearchLoopStatus.ALREADY_TERMINAL
        else:
            status = ResearchLoopStatus.ALREADY_TERMINAL
        return ResearchLoopOutcome(
            status=status,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment.experiment_id,
            experiment_execution_state=experiment.execution_state,
            authorization_decision_reference=attempt.authorization_decision_reference,
            request_id=attempt.request_id,
            attempt_id=attempt.attempt_id,
            attempt_state=attempt.state,
        )


def _authorization_view(
    record: AuthorizationSourceRecord | None,
) -> AuthorizationSourceView | None:
    if record is None:
        return None
    return AuthorizationSourceView(
        record.authorization_source_id,
        record.program_id,
        AuthorizationSourceState(record.state),
    )


def _issued_budget_from_record(record: IssuedBudgetRecord) -> IssuedBudget:
    return IssuedBudget(
        record.budget_id,
        record.max_requests,
        record.max_tool_calls,
        record.max_runtime_ms,
        record.max_concurrency,
    )


def _deny_experiment_state(reason: ReasonCode) -> str:
    if reason is ReasonCode.BUDGET_EXHAUSTED:
        return ExperimentExecutionState.BUDGET_EXHAUSTED.value
    return ExperimentExecutionState.BLOCKED.value


def _execution_decision_audit(
    *,
    audit_id: str,
    occurred_at,
    actor_id: str,
    experiment_id: str,
    correlation_id: str,
    request_id: str,
    decision: ExecutionDecision,
) -> AuditEventRecord:
    return AuditEventRecord(
        audit_event_id=audit_id,
        occurred_at=occurred_at,
        actor_id=actor_id,
        actor_type=ActorType.CONTROL_PLANE.value,
        event_type=AUDIT_EXECUTION_DECISION,
        subject_type="experiment",
        subject_id=experiment_id,
        payload={
            "decision": decision.decision.value,
            "reason_code": decision.reason_code.value,
            "authorization_source_id": decision.authorization_source_id,
            "matched_scope_rule_ids": list(decision.matched_scope_rule_ids),
            "budget_id": decision.budget_id,
            "side_effect_level": int(decision.side_effect_level),
            "approval_id": decision.approval_id,
            "request_id": request_id,
            "dispatched": decision.decision is ExecutionDecisionKind.ALLOW,
        },
        correlation_id=correlation_id,
    )


def _build_worker_request(
    *,
    experiment: ExperimentRecord,
    plan: ExperimentPlan,
    issued: IssuedBudgetRecord,
    request_id: str,
    correlation_id: str,
    authorization_decision_reference: str,
) -> dict[str, Any]:
    return {
        "contract_version": WORKER_CONTRACT_VERSION,
        "correlation": {
            "correlation_id": correlation_id,
            "research_run_id": experiment.research_run_id,
            "experiment_id": experiment.experiment_id,
            "request_id": request_id,
        },
        "worker_capability": plan.required_capability,
        "action": plan.action,
        "target_reference": plan.target_reference,
        "authorization_decision_reference": authorization_decision_reference,
        "execution_budget": {
            "budget_id": issued.budget_id,
            "max_requests": issued.max_requests,
            "max_tool_calls": issued.max_tool_calls,
            "max_runtime_ms": issued.max_runtime_ms,
            "max_concurrency": issued.max_concurrency,
        },
        "side_effect_level": plan.side_effect_level,
        "secret_references": [],
        "arguments": dict(plan.arguments),
    }


def _classify_invocation(
    invocation: WorkerInvocationOutcome,
) -> tuple[str, str, ResearchLoopStatus]:
    if invocation.invocation_status is InvocationStatus.COMPLETED:
        return (
            ExecutionAttemptState.COMPLETED.value,
            ExperimentExecutionState.EXECUTION_SUCCEEDED.value,
            ResearchLoopStatus.NO_OBSERVATION,
        )
    if invocation.invocation_status is InvocationStatus.TIMED_OUT:
        return (
            ExecutionAttemptState.TIMED_OUT.value,
            ExperimentExecutionState.EXECUTION_FAILED.value,
            ResearchLoopStatus.INVOCATION_FAILED,
        )
    if invocation.invocation_status is InvocationStatus.CANCELLED:
        return (
            ExecutionAttemptState.CANCELLED.value,
            ExperimentExecutionState.CANCELLED.value,
            ResearchLoopStatus.INVOCATION_FAILED,
        )
    if invocation.invocation_status in FAILED_INVOCATION_STATUSES:
        return (
            ExecutionAttemptState.FAILED.value,
            ExperimentExecutionState.EXECUTION_FAILED.value,
            ResearchLoopStatus.INVOCATION_FAILED,
        )
    return (
        ExecutionAttemptState.UNKNOWN_OUTCOME.value,
        ExperimentExecutionState.RUNNING.value,
        ResearchLoopStatus.UNKNOWN_OUTCOME,
    )
