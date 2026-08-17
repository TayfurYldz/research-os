"""Bounded autonomous orchestration for one ResearchRun.

Coordinates existing use cases. Does not own Core authority, Worker execution,
or Research-domain admission semantics. Autonomous != unbounded.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from research_os.application.budget_enforced_model import BudgetEnforcedModelPort
from research_os.application.budget_consumption import (
    BudgetConsumptionRejected,
    RecordBudgetConsumption,
)
from research_os.application.errors import ApplicationError
from research_os.application.orchestration_config import (
    assert_command_matches_configuration,
    configuration_from_record,
    fingerprint_for_start,
    scope_fingerprint,
)
from research_os.application.runtime_outcomes import stop_reason_for_runtime_outcome
from research_os.application.evaluate_experiment_feedback import (
    EvaluateExperimentFeedback,
    EvaluateExperimentFeedbackCommand,
)
from research_os.application.capability_binding import (
    CapabilityBindingError,
    capability_view_for_plan,
)
from research_os.application.execute_planned_experiment import (
    AuthorizedDispatch,
    ExecutePlannedExperiment,
    ExecutePlannedExperimentCommand,
    ResearchLoopStatus,
    _build_worker_request,
)
from research_os.application.identity import new_opaque_id
from research_os.application.plan_records import experiment_plan_from_record
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.application.prepare_planned_experiment import (
    PreparePlannedExperiment,
    PreparePlannedExperimentCommand,
)
from research_os.application.propose_research_hypothesis import (
    ProposeResearchHypothesis,
    ProposeResearchHypothesisCommand,
)
from research_os.application.select_research_opportunities import (
    SelectResearchOpportunities,
    SelectResearchOpportunitiesCommand,
)
from research_os.application.select_research_runtime import (
    SelectResearchRuntime,
    SelectResearchRuntimeCommand,
)
from research_os.core.approval import ApprovalView
from research_os.core.enums import ActorType, ExecutionDecisionKind, ReasonCode
from research_os.core.scope import ScopeEvaluationInput
from research_os.data.budget_ledger import ledger_totals
from research_os.data.records import (
    AuditEventRecord,
    ExecutionAttemptState,
    ResearchCycleRecord,
    ResearchOrchestrationRecord,
)
from research_os.platform.observability import InMemoryObservability, ObservabilityPort, TelemetryEvent
from research_os.platform.worker import WorkerPort
from research_os.research.admission import AdmissionOutcome
from research_os.research.exploration import ResearchPolicyBudget
from research_os.research.model_port import ModelPort
from research_os.research.model_runtime import RuntimeOutcome
from research_os.research.orchestration import (
    ORCHESTRATION_POLICY_VERSION,
    CycleOutcome,
    OrchestrationBounds,
    OrchestrationPhase,
    OrchestrationState,
    OrchestrationUsage,
    StopReason,
    check_orchestration_bounds,
    cycle_outcome_for_stop,
    next_cycle_action,
    orchestration_state_for_stop,
    NextCycleAction,
)
from research_os.research.planning import plan_diagnostic_echo
from research_os.research.routing import ROUTING_POLICY_VERSION, RoutingOutcome, RoutingRequest


CONTROL_PLANE_ACTOR_ID = "control-plane"
DIAGNOSTIC_RESEARCH_QUESTION = (
    "Does the diagnostic capability return the submitted value?"
)


@dataclass(frozen=True)
class StartAutonomousResearchCommand:
    research_run_id: str
    budget_id: str
    target_reference: str
    scope: ScopeEvaluationInput
    bounds: OrchestrationBounds
    research_question: str = DIAGNOSTIC_RESEARCH_QUESTION
    approval: ApprovalView | None = None
    routing_request: RoutingRequest | None = None
    selection_budget: ResearchPolicyBudget | None = None


@dataclass(frozen=True)
class OrchestrationTickResult:
    research_run_id: str
    state: str
    cycle_number: int
    outcome: str
    stop_reason: str | None
    last_phase: str
    hypothesis_id: str | None = None
    experiment_id: str | None = None


class AutonomousResearchController:
    """One controller manages one ResearchRun. Research cannot become execution authority."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        worker: WorkerPort,
        model: ModelPort,
        *,
        clock: Clock | None = None,
        observability: ObservabilityPort | None = None,
        actor_id: str = CONTROL_PLANE_ACTOR_ID,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock or SystemClock()
        self._observability = observability or InMemoryObservability()
        self._actor_id = actor_id
        self._model = model
        self._execute = ExecutePlannedExperiment(
            uow_factory, worker, clock=self._clock, actor_id=actor_id
        )
        self._propose = ProposeResearchHypothesis(
            uow_factory, model, clock=self._clock
        )
        self._prepare = PreparePlannedExperiment(uow_factory, clock=self._clock)
        self._evaluate = EvaluateExperimentFeedback(uow_factory, clock=self._clock)
        self._select = SelectResearchOpportunities(
            uow_factory, clock=self._clock, actor_id=actor_id
        )
        self._route = SelectResearchRuntime(
            uow_factory, clock=self._clock, actor_id=actor_id
        )
        self._consume = RecordBudgetConsumption(uow_factory, clock=self._clock)
        self._started_at: dict[str, datetime] = {}

    def start(self, command: StartAutonomousResearchCommand) -> OrchestrationTickResult:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            run = uow.research_runs.get(command.research_run_id)
            if run is None:
                raise ApplicationError("research run not found")
            existing = uow.research_orchestrations.get(command.research_run_id)
            if existing is not None:
                uow.rollback()
                return _result_from_record(existing, CycleOutcome.CONTINUE)
            zero = command.bounds.max_cycles == 0
            scope_fp = scope_fingerprint(command.scope)
            routing_version = (
                ROUTING_POLICY_VERSION if command.routing_request is not None else None
            )
            fingerprint = fingerprint_for_start(
                research_run_id=command.research_run_id,
                budget_id=command.budget_id,
                target_reference=command.target_reference,
                research_question=command.research_question,
                policy_version=ORCHESTRATION_POLICY_VERSION,
                bounds=command.bounds,
                routing_policy_version=routing_version,
                scope_fp=scope_fp,
            )
            record = ResearchOrchestrationRecord(
                research_run_id=command.research_run_id,
                state=(
                    OrchestrationState.COMPLETED.value
                    if zero
                    else OrchestrationState.READY.value
                ),
                cycle_number=0,
                last_phase="start",
                last_opportunity_id=None,
                last_hypothesis_id=None,
                last_experiment_id=None,
                pause_reason=None,
                stop_reason=StopReason.MAX_CYCLES_REACHED.value if zero else None,
                policy_version=ORCHESTRATION_POLICY_VERSION,
                max_cycles=command.bounds.max_cycles,
                max_experiments=command.bounds.max_experiments,
                max_model_calls=command.bounds.max_model_calls,
                max_worker_invocations=command.bounds.max_worker_invocations,
                max_elapsed_ms=command.bounds.max_elapsed_ms,
                max_selected_opportunities=command.bounds.max_selected_opportunities,
                max_runtime_fallback=command.bounds.max_runtime_fallback,
                side_effect_ceiling=command.bounds.side_effect_ceiling,
                allow_repeated_control_experiments=(
                    command.bounds.allow_repeated_control_experiments
                ),
                created_at=now,
                updated_at=now,
                checkpoint_at=now,
                budget_id=command.budget_id,
                target_reference=command.target_reference,
                research_question=command.research_question,
                configuration_fingerprint=fingerprint,
                current_phase=OrchestrationPhase.CYCLE_READY.value,
                routing_policy_version=routing_version,
                scope_fingerprint=scope_fp,
            )
            uow.research_orchestrations.insert(record)
            uow.audit_events.insert(
                AuditEventRecord(
                    audit_event_id=new_opaque_id(),
                    occurred_at=now,
                    actor_id=self._actor_id,
                    actor_type=ActorType.CONTROL_PLANE.value,
                    event_type="ORCHESTRATION_STARTED",
                    subject_type="research_run",
                    subject_id=command.research_run_id,
                    payload={
                        "policy_version": ORCHESTRATION_POLICY_VERSION,
                        "max_cycles": command.bounds.max_cycles,
                        "not_unbounded": True,
                    },
                )
            )
            uow.commit()
        self._started_at[command.research_run_id] = now
        self._observability.emit(
            TelemetryEvent(
                event="orchestration.start",
                outcome=record.state,
                research_run_id=command.research_run_id,
            )
        )
        outcome = CycleOutcome.COMPLETE if zero else CycleOutcome.CONTINUE
        return _result_from_record(record, outcome)

    def pause(self, research_run_id: str) -> OrchestrationTickResult:
        return self._operator_state(
            research_run_id,
            OrchestrationState.PAUSED,
            StopReason.OPERATOR_PAUSED,
            CycleOutcome.PAUSE,
        )

    def resume(self, research_run_id: str) -> OrchestrationTickResult:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            current = uow.research_orchestrations.get(research_run_id)
            if current is None:
                raise ApplicationError("orchestration not found")
            if current.state != OrchestrationState.PAUSED.value:
                uow.rollback()
                return _result_from_record(current, CycleOutcome.CONTINUE)
            updated = replace(
                current,
                state=OrchestrationState.READY.value,
                pause_reason=None,
                stop_reason=None,
                last_phase="resume",
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(updated)
            uow.commit()
        return _result_from_record(updated, CycleOutcome.CONTINUE)

    def cancel(self, research_run_id: str) -> OrchestrationTickResult:
        return self._operator_state(
            research_run_id,
            OrchestrationState.COMPLETED,
            StopReason.OPERATOR_CANCELLED,
            CycleOutcome.COMPLETE,
        )

    def step(self, command: StartAutonomousResearchCommand) -> OrchestrationTickResult:
        current = self._reload(command.research_run_id)
        config = configuration_from_record(current)
        assert_command_matches_configuration(
            config=config,
            bounds=command.bounds,
            budget_id=command.budget_id,
            target_reference=command.target_reference,
            research_question=command.research_question,
            scope=command.scope,
        )
        bounds = config.bounds
        if current.state in {
            OrchestrationState.COMPLETED.value,
            OrchestrationState.BUDGET_EXHAUSTED.value,
            OrchestrationState.FAILED_OPERATIONAL.value,
            OrchestrationState.BLOCKED.value,
            OrchestrationState.WAITING_HUMAN.value,
            OrchestrationState.PAUSED.value,
        }:
            return _result_from_record(current, CycleOutcome.CONTINUE)

        phase = current.current_phase
        if phase == OrchestrationPhase.DISPATCHING.value or self._unknown_open(
            command.research_run_id
        ):
            return self._stop(current, StopReason.OPERATIONAL_FAILURE, "unknown_outcome")

        resumed = self._resume_authorized(command, current)
        if resumed is not None:
            return resumed

        if phase == OrchestrationPhase.HYPOTHESIS_ADMITTED.value and current.last_hypothesis_id:
            return self._resume_admitted_hypothesis(command, current, config)
        if phase == OrchestrationPhase.OPPORTUNITY_SELECTED.value:
            existing_hypothesis = current.last_hypothesis_id or self._latest_hypothesis_id(
                command.research_run_id
            )
            if existing_hypothesis:
                current = self._checkpoint(
                    current,
                    phase=OrchestrationPhase.HYPOTHESIS_ADMITTED,
                    hypothesis_id=existing_hypothesis,
                )
                return self._resume_admitted_hypothesis(command, current, config)
        if phase in {
            OrchestrationPhase.EXPERIMENT_PLANNED.value,
            OrchestrationPhase.AUTHORIZATION_REQUESTED.value,
        } and current.last_experiment_id:
            return self._resume_planned_experiment(command, current, config)
        if phase == OrchestrationPhase.ATTEMPT_AUTHORIZED.value and current.last_experiment_id:
            return self._resume_planned_experiment(command, current, config)
        if phase in {
            OrchestrationPhase.WORKER_RESULT_RECORDED.value,
            OrchestrationPhase.TRANSITION_A_COMPLETE.value,
            OrchestrationPhase.ASSESSMENT_COMPLETE.value,
            OrchestrationPhase.TRANSITION_B_COMPLETE.value,
        } and current.last_experiment_id:
            return self._resume_after_worker(current, config)

        usage = self._usage(config, current)
        bound = check_orchestration_bounds(bounds, usage)
        if not bound.allowed and bound.stop_reason is not None:
            return self._stop(current, bound.stop_reason, "bounds")

        self._mark_running(current)
        current = self._reload(command.research_run_id)
        skip_discovery = phase == OrchestrationPhase.OPPORTUNITY_SELECTED.value

        if not skip_discovery and command.routing_request is not None:
            routed = self._route.execute(
                SelectResearchRuntimeCommand(
                    research_run_id=command.research_run_id,
                    request=command.routing_request,
                )
            )
            if routed.decision.outcome is RoutingOutcome.NO_COMPATIBLE_RUNTIME:
                return self._stop(current, StopReason.NO_COMPATIBLE_RUNTIME, "routing")
            if routed.decision.outcome is RoutingOutcome.BLOCKED_POLICY:
                return self._stop(current, StopReason.CONTENT_POLICY_BLOCKED, "routing")
            if routed.decision.outcome is not RoutingOutcome.SELECT:
                return self._stop(current, StopReason.NO_COMPATIBLE_RUNTIME, "routing")

        if skip_discovery:
            opportunity_id = current.last_opportunity_id
            cycle_id = current.active_cycle_id or new_opaque_id()
        else:
            selected = self._select.execute(
                SelectResearchOpportunitiesCommand(
                    research_run_id=command.research_run_id,
                    budget=command.selection_budget,
                )
            )
            selected_ids = [item.opportunity.opportunity_id for item in selected.selected]
            if len(selected_ids) > bounds.max_selected_opportunities:
                selected_ids = selected_ids[: bounds.max_selected_opportunities]
            opportunity_id = selected_ids[0] if selected_ids else None
            action, stop = next_cycle_action(
                bounds=bounds,
                usage=self._usage(config, current),
                selected_count=len(selected_ids),
                hypothesis_count=self._hypothesis_count(command.research_run_id),
                unknown_outcome_open=False,
            )
            if action is NextCycleAction.STOP:
                reason = stop or StopReason.COMPLETED_NO_MORE_OPPORTUNITIES
                return self._stop(current, reason, "no_more_opportunities")

            cycle_id = current.active_cycle_id or new_opaque_id()
            current = self._checkpoint(
                current,
                phase=OrchestrationPhase.OPPORTUNITY_SELECTED,
                opportunity_id=opportunity_id,
                active_cycle_id=cycle_id,
            )

        bound_model = BudgetEnforcedModelPort(
            self._model,
            self._uow_factory,
            budget_id=config.budget_id,
            research_run_id=config.research_run_id,
            cycle_id=cycle_id,
            clock=self._clock,
        )
        proposer = ProposeResearchHypothesis(
            self._uow_factory, bound_model, clock=self._clock
        )
        correlation_id = new_opaque_id()

        def _persist_hypothesis(uow, *, hypothesis_id: str | None) -> None:
            nonlocal current
            if hypothesis_id is None:
                return
            now = self._clock.now()
            current = replace(
                current,
                state=OrchestrationState.RUNNING.value,
                current_phase=OrchestrationPhase.HYPOTHESIS_ADMITTED.value,
                last_phase=OrchestrationPhase.HYPOTHESIS_ADMITTED.value,
                last_opportunity_id=opportunity_id or current.last_opportunity_id,
                last_hypothesis_id=hypothesis_id,
                active_cycle_id=cycle_id,
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(current)

        try:
            proposed = proposer.execute(
                ProposeResearchHypothesisCommand(
                    research_run_id=command.research_run_id,
                    research_question=config.research_question,
                    budget_id=config.budget_id,
                    target_reference=config.target_reference,
                    correlation_id=correlation_id,
                    opportunity_id=opportunity_id,
                    echo_message=f"ping-{current.cycle_number + 1}",
                ),
                persist_hook=_persist_hypothesis,
            )
        except BudgetConsumptionRejected:
            return self._stop(current, StopReason.BUDGET_EXHAUSTED, "model_budget")
        if bound_model.reserved_invocations:
            self._observability.increment("model_calls", len(bound_model.reserved_invocations))

        if proposed.outcome is AdmissionOutcome.MODEL_INVOCATION_FAILED:
            outcome = proposed.runtime_outcome or RuntimeOutcome.PROCESS_FAILED
            return self._stop(
                current,
                stop_reason_for_runtime_outcome(outcome),
                "model_runtime_outcome",
                hypothesis_id=proposed.hypothesis_id,
            )
        if not proposed.admission.admitted or proposed.experiment_plan is None:
            return self._complete_cycle(
                current,
                CycleOutcome.CONTINUE,
                "hypothesis_not_admitted",
                opportunity_id=opportunity_id,
                current_phase=OrchestrationPhase.CYCLE_COMPLETE,
            )

        plan = proposed.experiment_plan
        if plan.side_effect_level > bounds.side_effect_ceiling:
            return self._stop(current, StopReason.CORE_BLOCKED, "side_effect_ceiling")

        experiment_id = new_opaque_id()
        with self._uow_factory.open() as uow:
            self._prepare.execute(
                PreparePlannedExperimentCommand(
                    experiment_id=experiment_id,
                    research_run_id=command.research_run_id,
                    plan=plan,
                ),
                unit_of_work=uow,
            )
            current = replace(
                current,
                current_phase=OrchestrationPhase.EXPERIMENT_PLANNED.value,
                last_phase=OrchestrationPhase.EXPERIMENT_PLANNED.value,
                last_experiment_id=experiment_id,
                last_hypothesis_id=proposed.hypothesis_id or current.last_hypothesis_id,
                updated_at=self._clock.now(),
                checkpoint_at=self._clock.now(),
            )
            uow.research_orchestrations.save(current)
            uow.commit()

        current = self._checkpoint(
            current,
            phase=OrchestrationPhase.AUTHORIZATION_REQUESTED,
            experiment_id=experiment_id,
            hypothesis_id=proposed.hypothesis_id,
        )

        def _persist_attempt(uow, *, attempt_id: str, experiment_id: str) -> None:
            nonlocal current
            now = self._clock.now()
            current = replace(
                current,
                state=OrchestrationState.RUNNING.value,
                current_phase=OrchestrationPhase.ATTEMPT_AUTHORIZED.value,
                last_phase=OrchestrationPhase.ATTEMPT_AUTHORIZED.value,
                last_experiment_id=experiment_id,
                last_attempt_id=attempt_id,
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(current)

        loop = self._execute.execute(
            ExecutePlannedExperimentCommand(
                experiment_id=experiment_id,
                plan=plan,
                scope=command.scope,
                approval=command.approval,
            ),
            persist_hook=_persist_attempt,
        )
        self._observability.increment("experiments_executed")
        if loop.status is ResearchLoopStatus.DISPATCH_DENIED:
            return self._stop(
                current,
                StopReason.CORE_BLOCKED,
                "core_deny",
                hypothesis_id=proposed.hypothesis_id,
                experiment_id=experiment_id,
            )
        if loop.status is ResearchLoopStatus.HUMAN_REVIEW_REQUIRED:
            return self._stop(
                current,
                StopReason.REQUIRE_HUMAN_REVIEW,
                "human_review",
                hypothesis_id=proposed.hypothesis_id,
                experiment_id=experiment_id,
            )
        if loop.status is ResearchLoopStatus.UNKNOWN_OUTCOME:
            return self._stop(
                current,
                StopReason.OPERATIONAL_FAILURE,
                "unknown_outcome",
                hypothesis_id=proposed.hypothesis_id,
                experiment_id=experiment_id,
                current_phase=OrchestrationPhase.DISPATCHING,
            )
        if loop.status in {
            ResearchLoopStatus.OBSERVATION_PRODUCED,
            ResearchLoopStatus.NO_OBSERVATION,
            ResearchLoopStatus.INVOCATION_FAILED,
        } and loop.experiment_id:
            current = self._checkpoint(
                current,
                phase=OrchestrationPhase.WORKER_RESULT_RECORDED,
                experiment_id=experiment_id,
                hypothesis_id=proposed.hypothesis_id,
                attempt_id=loop.attempt_id,
                worker_result_id=loop.worker_result_id,
                observation_id=loop.observation_ids[0] if loop.observation_ids else None,
            )
            current = self._checkpoint(
                current,
                phase=OrchestrationPhase.TRANSITION_A_COMPLETE,
                experiment_id=experiment_id,
                hypothesis_id=proposed.hypothesis_id,
                observation_id=loop.observation_ids[0] if loop.observation_ids else None,
            )
            feedback = self._evaluate.execute(
                EvaluateExperimentFeedbackCommand(experiment_id=loop.experiment_id)
            )
            current = self._checkpoint(
                current,
                phase=OrchestrationPhase.ASSESSMENT_COMPLETE,
                experiment_id=experiment_id,
                hypothesis_id=proposed.hypothesis_id,
                assessment_id=feedback.assessment_id,
            )
        self._observability.increment("orchestration_cycles")
        next_usage = self._usage(config, current)
        if next_usage.cycles_completed + 1 >= bounds.max_cycles:
            return self._stop(
                current,
                StopReason.MAX_CYCLES_REACHED,
                "execute",
                hypothesis_id=proposed.hypothesis_id,
                experiment_id=experiment_id,
                opportunity_id=opportunity_id,
                increment_cycle=True,
                current_phase=OrchestrationPhase.CYCLE_COMPLETE,
            )
        return self._complete_cycle(
            current,
            CycleOutcome.CONTINUE,
            "execute",
            opportunity_id=opportunity_id,
            hypothesis_id=proposed.hypothesis_id,
            experiment_id=experiment_id,
            increment_cycle=True,
            current_phase=OrchestrationPhase.CYCLE_COMPLETE,
        )

    def run_bounded(self, command: StartAutonomousResearchCommand) -> OrchestrationTickResult:
        started = self.start(command)
        if started.state != OrchestrationState.READY.value:
            return started
        last = started
        ticks = command.bounds.max_cycles if command.bounds.max_cycles > 0 else 0
        for _ in range(ticks):
            last = self.step(command)
            if last.state != OrchestrationState.RUNNING.value and last.state != OrchestrationState.READY.value:
                return last
        return last

    def _resume_authorized(
        self,
        command: StartAutonomousResearchCommand,
        current: ResearchOrchestrationRecord,
    ) -> OrchestrationTickResult | None:
        with self._uow_factory.open() as uow:
            attempts = uow.execution_attempts.list_for_research_run(command.research_run_id)
            authorized = [
                item
                for item in attempts
                if item.state == ExecutionAttemptState.AUTHORIZED.value
            ]
            dispatching = [
                item
                for item in attempts
                if item.state
                in {
                    ExecutionAttemptState.DISPATCHING.value,
                    ExecutionAttemptState.UNKNOWN_OUTCOME.value,
                }
            ]
            if dispatching:
                uow.rollback()
                return self._stop(current, StopReason.OPERATIONAL_FAILURE, "unknown_dispatch")
            if not authorized:
                uow.rollback()
                return None
            attempt = authorized[0]
            experiment = uow.experiments.get(attempt.experiment_id)
            plan_record = uow.experiment_plans.get(attempt.experiment_id)
            issued = uow.issued_budgets.get(attempt.budget_id)
            uow.rollback()
        if experiment is None or plan_record is None or issued is None:
            return self._stop(current, StopReason.OPERATIONAL_FAILURE, "resume_missing")
        plan = experiment_plan_from_record(plan_record)
        try:
            capability_view = capability_view_for_plan(plan)
        except CapabilityBindingError:
            return self._stop(current, StopReason.CORE_BLOCKED, "capability_binding")
        dispatch = AuthorizedDispatch(
            experiment_id=experiment.experiment_id,
            hypothesis_id=experiment.hypothesis_id,
            request_id=attempt.request_id,
            attempt_id=attempt.attempt_id,
            correlation_id=attempt.correlation_id,
            authorization_decision_reference=attempt.authorization_decision_reference,
            worker_request=_build_worker_request(
                experiment=experiment,
                plan=plan,
                capability_view=capability_view,
                issued=issued,
                request_id=attempt.request_id,
                correlation_id=attempt.correlation_id,
                authorization_decision_reference=attempt.authorization_decision_reference,
            ),
            timeout_ms=issued.max_runtime_ms,
            core_decision=ExecutionDecisionKind.ALLOW,
            core_reason_code=ReasonCode.ALLOWED,
        )
        loop = self._execute.dispatch(dispatch)
        if loop.status is ResearchLoopStatus.UNKNOWN_OUTCOME:
            return self._stop(
                current,
                StopReason.OPERATIONAL_FAILURE,
                "unknown_outcome",
                experiment_id=experiment.experiment_id,
            )
        return self._complete_cycle(
            current,
            CycleOutcome.CONTINUE,
            "resume_authorized",
            hypothesis_id=experiment.hypothesis_id,
            experiment_id=experiment.experiment_id,
            increment_cycle=True,
        )

    def _operator_state(
        self,
        research_run_id: str,
        state: OrchestrationState,
        reason: StopReason,
        outcome: CycleOutcome,
    ) -> OrchestrationTickResult:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            current = uow.research_orchestrations.get(research_run_id)
            if current is None:
                raise ApplicationError("orchestration not found")
            updated = replace(
                current,
                state=state.value,
                stop_reason=reason.value,
                pause_reason=reason.value if state is OrchestrationState.PAUSED else current.pause_reason,
                last_phase="operator",
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(updated)
            uow.commit()
        return _result_from_record(updated, outcome)

    def _reload(self, research_run_id: str) -> ResearchOrchestrationRecord:
        with self._uow_factory.open() as uow:
            current = uow.research_orchestrations.get(research_run_id)
            uow.rollback()
        if current is None:
            raise ApplicationError("orchestration not found")
        return current

    def _mark_running(self, current: ResearchOrchestrationRecord) -> None:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            uow.research_orchestrations.save(
                replace(
                    current,
                    state=OrchestrationState.RUNNING.value,
                    last_phase="running",
                    updated_at=now,
                    checkpoint_at=now,
                )
            )
            uow.commit()

    def _stop(
        self,
        current: ResearchOrchestrationRecord,
        reason: StopReason,
        phase: str,
        *,
        hypothesis_id: str | None = None,
        experiment_id: str | None = None,
        opportunity_id: str | None = None,
        increment_cycle: bool = False,
        current_phase: OrchestrationPhase | None = None,
    ) -> OrchestrationTickResult:
        outcome = cycle_outcome_for_stop(reason)
        state = orchestration_state_for_stop(reason)
        return self._complete_cycle(
            current,
            outcome,
            phase,
            stop_reason=reason,
            state=state,
            hypothesis_id=hypothesis_id,
            experiment_id=experiment_id,
            opportunity_id=opportunity_id,
            increment_cycle=increment_cycle,
            current_phase=current_phase,
        )

    def _complete_cycle(
        self,
        current: ResearchOrchestrationRecord,
        outcome: CycleOutcome,
        phase: str,
        *,
        stop_reason: StopReason | None = None,
        state: OrchestrationState | None = None,
        hypothesis_id: str | None = None,
        experiment_id: str | None = None,
        opportunity_id: str | None = None,
        increment_cycle: bool = False,
        current_phase: OrchestrationPhase | None = None,
    ) -> OrchestrationTickResult:
        now = self._clock.now()
        inserting = increment_cycle or outcome is not CycleOutcome.CONTINUE
        cycle_number = current.cycle_number + (1 if inserting else 0)
        next_state = (
            state.value
            if state is not None
            else (
                OrchestrationState.READY.value
                if outcome is CycleOutcome.CONTINUE
                else current.state
            )
        )
        if outcome is CycleOutcome.COMPLETE and state is None:
            next_state = OrchestrationState.COMPLETED.value
        with self._uow_factory.open() as uow:
            updated = replace(
                current,
                state=next_state,
                cycle_number=cycle_number,
                last_phase=phase,
                current_phase=(
                    current_phase.value
                    if current_phase is not None
                    else (
                        OrchestrationPhase.CYCLE_COMPLETE.value
                        if inserting
                        else current.current_phase
                    )
                ),
                last_opportunity_id=opportunity_id or current.last_opportunity_id,
                last_hypothesis_id=hypothesis_id or current.last_hypothesis_id,
                last_experiment_id=experiment_id or current.last_experiment_id,
                stop_reason=stop_reason.value if stop_reason else current.stop_reason,
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(updated)
            if inserting:
                uow.research_cycles.insert(
                    ResearchCycleRecord(
                        cycle_id=new_opaque_id(),
                        research_run_id=current.research_run_id,
                        cycle_number=cycle_number,
                        phase_completed=phase,
                        outcome=outcome.value,
                        created_at=now,
                        stop_reason=stop_reason.value if stop_reason else None,
                        opportunity_id=opportunity_id,
                        hypothesis_id=hypothesis_id,
                        experiment_id=experiment_id,
                    )
                )
            uow.commit()
        self._observability.emit(
            TelemetryEvent(
                event="orchestration.cycle",
                outcome=outcome.value,
                research_run_id=current.research_run_id,
                experiment_id=experiment_id,
                orchestration_cycle=cycle_number,
            )
        )
        return _result_from_record(updated, outcome)

    def _usage(
        self,
        config,
        current: ResearchOrchestrationRecord,
    ) -> OrchestrationUsage:
        started = self._started_at.get(config.research_run_id, current.created_at)
        elapsed = int((self._clock.now() - started).total_seconds() * 1000)
        if elapsed < 0:
            elapsed = 0
        with self._uow_factory.open() as uow:
            experiments = uow.experiments.list_for_research_run(config.research_run_id)
            opportunities = uow.research_opportunities.list_for_research_run(
                config.research_run_id
            )
            consumption = uow.budget_consumptions.list_for_budget(config.budget_id)
            uow.rollback()
        totals = ledger_totals(consumption)
        return OrchestrationUsage(
            cycles_completed=current.cycle_number,
            experiments_executed=len(experiments),
            model_calls=totals.model_calls,
            worker_invocations=totals.worker_invocations,
            elapsed_ms=elapsed,
            opportunities_selected=len(opportunities),
            runtime_fallbacks=0,
            worker_requests=totals.worker_requests,
            execution_time_ms=totals.execution_time_ms,
            artifact_bytes=totals.artifact_bytes,
        )

    def _checkpoint(
        self,
        current: ResearchOrchestrationRecord,
        *,
        phase: OrchestrationPhase,
        opportunity_id: str | None = None,
        hypothesis_id: str | None = None,
        experiment_id: str | None = None,
        active_cycle_id: str | None = None,
        attempt_id: str | None = None,
        observation_id: str | None = None,
        assessment_id: str | None = None,
        worker_result_id: str | None = None,
    ) -> ResearchOrchestrationRecord:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            updated = replace(
                current,
                state=OrchestrationState.RUNNING.value,
                current_phase=phase.value,
                last_phase=phase.value,
                last_opportunity_id=opportunity_id or current.last_opportunity_id,
                last_hypothesis_id=hypothesis_id or current.last_hypothesis_id,
                last_experiment_id=experiment_id or current.last_experiment_id,
                last_attempt_id=attempt_id or current.last_attempt_id,
                last_observation_id=observation_id or current.last_observation_id,
                last_assessment_id=assessment_id or current.last_assessment_id,
                last_worker_result_id=worker_result_id or current.last_worker_result_id,
                active_cycle_id=active_cycle_id or current.active_cycle_id,
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(updated)
            uow.commit()
        return updated

    def _resume_admitted_hypothesis(
        self,
        command: StartAutonomousResearchCommand,
        current: ResearchOrchestrationRecord,
        config,
    ) -> OrchestrationTickResult:
        hypothesis_id = current.last_hypothesis_id
        if hypothesis_id is None:
            return self._stop(current, StopReason.OPERATIONAL_FAILURE, "missing_hypothesis")
        experiment_id = current.last_experiment_id or self._existing_experiment_id(
            command.research_run_id, hypothesis_id
        )
        if experiment_id is None:
            experiment_id = new_opaque_id()
            plan = plan_diagnostic_echo(
                hypothesis_id,
                budget_id=config.budget_id,
                target_reference=config.target_reference,
                message=f"ping-{current.cycle_number + 1}",
            )
            with self._uow_factory.open() as uow:
                self._prepare.execute(
                    PreparePlannedExperimentCommand(
                        experiment_id=experiment_id,
                        research_run_id=command.research_run_id,
                        plan=plan,
                    ),
                    unit_of_work=uow,
                )
                current = replace(
                    current,
                    current_phase=OrchestrationPhase.EXPERIMENT_PLANNED.value,
                    last_phase=OrchestrationPhase.EXPERIMENT_PLANNED.value,
                    last_experiment_id=experiment_id,
                    updated_at=self._clock.now(),
                    checkpoint_at=self._clock.now(),
                )
                uow.research_orchestrations.save(current)
                uow.commit()
        elif current.current_phase != OrchestrationPhase.EXPERIMENT_PLANNED.value:
            current = self._checkpoint(
                current,
                phase=OrchestrationPhase.EXPERIMENT_PLANNED,
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
            )
        return self._resume_planned_experiment(command, current, config)

    def _resume_planned_experiment(
        self,
        command: StartAutonomousResearchCommand,
        current: ResearchOrchestrationRecord,
        config,
    ) -> OrchestrationTickResult:
        experiment_id = current.last_experiment_id
        if experiment_id is None:
            return self._stop(current, StopReason.OPERATIONAL_FAILURE, "missing_experiment")
        with self._uow_factory.open() as uow:
            plan_record = uow.experiment_plans.get(experiment_id)
            uow.rollback()
        if plan_record is None:
            return self._stop(current, StopReason.OPERATIONAL_FAILURE, "missing_plan")
        plan = experiment_plan_from_record(plan_record)

        def _persist_attempt(uow, *, attempt_id: str, experiment_id: str) -> None:
            nonlocal current
            now = self._clock.now()
            current = replace(
                current,
                state=OrchestrationState.RUNNING.value,
                current_phase=OrchestrationPhase.ATTEMPT_AUTHORIZED.value,
                last_phase=OrchestrationPhase.ATTEMPT_AUTHORIZED.value,
                last_experiment_id=experiment_id,
                last_attempt_id=attempt_id,
                updated_at=now,
                checkpoint_at=now,
            )
            uow.research_orchestrations.save(current)

        loop = self._execute.execute(
            ExecutePlannedExperimentCommand(
                experiment_id=experiment_id,
                plan=plan,
                scope=command.scope,
                approval=command.approval,
            ),
            persist_hook=_persist_attempt,
        )
        if loop.status is ResearchLoopStatus.UNKNOWN_OUTCOME:
            return self._stop(
                current,
                StopReason.OPERATIONAL_FAILURE,
                "unknown_outcome",
                experiment_id=experiment_id,
                current_phase=OrchestrationPhase.DISPATCHING,
            )
        if loop.status is ResearchLoopStatus.DISPATCH_DENIED:
            return self._stop(current, StopReason.CORE_BLOCKED, "core_deny", experiment_id=experiment_id)
        if loop.status is ResearchLoopStatus.HUMAN_REVIEW_REQUIRED:
            return self._stop(
                current, StopReason.REQUIRE_HUMAN_REVIEW, "human_review", experiment_id=experiment_id
            )
        if loop.experiment_id and loop.status is not ResearchLoopStatus.REAUTHORIZATION_REQUIRED:
            self._evaluate.execute(EvaluateExperimentFeedbackCommand(experiment_id=loop.experiment_id))
        usage = self._usage(config, current)
        if usage.cycles_completed + 1 >= config.bounds.max_cycles:
            return self._stop(
                current,
                StopReason.MAX_CYCLES_REACHED,
                "resume_planned",
                experiment_id=experiment_id,
                increment_cycle=True,
                current_phase=OrchestrationPhase.CYCLE_COMPLETE,
            )
        return self._complete_cycle(
            current,
            CycleOutcome.CONTINUE,
            "resume_planned",
            experiment_id=experiment_id,
            increment_cycle=True,
            current_phase=OrchestrationPhase.CYCLE_COMPLETE,
        )

    def _resume_after_worker(
        self,
        current: ResearchOrchestrationRecord,
        config,
    ) -> OrchestrationTickResult:
        if current.last_experiment_id and current.current_phase in {
            OrchestrationPhase.WORKER_RESULT_RECORDED.value,
            OrchestrationPhase.TRANSITION_A_COMPLETE.value,
        }:
            feedback = self._evaluate.execute(
                EvaluateExperimentFeedbackCommand(experiment_id=current.last_experiment_id)
            )
            current = self._checkpoint(
                current,
                phase=OrchestrationPhase.ASSESSMENT_COMPLETE,
                experiment_id=current.last_experiment_id,
                assessment_id=feedback.assessment_id,
            )
        usage = self._usage(config, current)
        if usage.cycles_completed + 1 >= config.bounds.max_cycles:
            return self._stop(
                current,
                StopReason.MAX_CYCLES_REACHED,
                "resume_after_worker",
                experiment_id=current.last_experiment_id,
                increment_cycle=True,
                current_phase=OrchestrationPhase.CYCLE_COMPLETE,
            )
        return self._complete_cycle(
            current,
            CycleOutcome.CONTINUE,
            "resume_after_worker",
            experiment_id=current.last_experiment_id,
            increment_cycle=True,
            current_phase=OrchestrationPhase.CYCLE_COMPLETE,
        )

    def _hypothesis_count(self, research_run_id: str) -> int:
        with self._uow_factory.open() as uow:
            count = len(uow.hypotheses.list_for_research_run(research_run_id))
            uow.rollback()
        return count

    def _latest_hypothesis_id(self, research_run_id: str) -> str | None:
        with self._uow_factory.open() as uow:
            records = uow.hypotheses.list_for_research_run(research_run_id)
            uow.rollback()
        if not records:
            return None
        return records[-1].hypothesis_id

    def _existing_experiment_id(self, research_run_id: str, hypothesis_id: str) -> str | None:
        with self._uow_factory.open() as uow:
            records = uow.experiments.list_for_research_run(research_run_id)
            uow.rollback()
        matching = [item for item in records if item.hypothesis_id == hypothesis_id]
        if not matching:
            return None
        return matching[-1].experiment_id

    def _unknown_open(self, research_run_id: str) -> bool:
        with self._uow_factory.open() as uow:
            attempts = uow.execution_attempts.list_for_research_run(research_run_id)
            uow.rollback()
        return any(
            item.state
            in {
                ExecutionAttemptState.DISPATCHING.value,
                ExecutionAttemptState.UNKNOWN_OUTCOME.value,
            }
            for item in attempts
        )


def _result_from_record(
    record: ResearchOrchestrationRecord, outcome: CycleOutcome
) -> OrchestrationTickResult:
    mapped_outcome = outcome.value
    if record.state == OrchestrationState.PAUSED.value:
        mapped_outcome = CycleOutcome.PAUSE.value
    return OrchestrationTickResult(
        research_run_id=record.research_run_id,
        state=record.state,
        cycle_number=record.cycle_number,
        outcome=mapped_outcome,
        stop_reason=record.stop_reason,
        last_phase=record.last_phase,
        hypothesis_id=record.last_hypothesis_id,
        experiment_id=record.last_experiment_id,
    )
