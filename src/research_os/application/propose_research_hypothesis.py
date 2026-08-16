"""Propose a research Hypothesis through Generator, Falsifier, and admission.

Persists reasoning and admission provenance for every completed cycle.
Rejected proposals never become a Hypothesis. Does not execute a Worker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_os.application.errors import ApplicationError
from research_os.application.identity import new_opaque_id
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.data.records import (
    HypothesisRecord,
    ResearchAdmissionRecord,
    ResearchReasoningRecord,
)
from research_os.research.admission import AdmissionDecision, AdmissionOutcome, admit_hypothesis
from research_os.research.context import (
    ChainContextSource,
    ChangeEventContextSource,
    ContextBudget,
    DifferentialContextSource,
    ExperimentSource,
    ExternalContentSource,
    HypothesisSource,
    InferenceSource,
    InvariantContextSource,
    ObservationSource,
    OpportunityContextSource,
    ResearchContext,
    ResearchContextBuilder,
)
from research_os.research.cycle import generate_challenge, generate_proposal
from research_os.research.model_port import ModelCallResult, ModelPort, ModelPortError, ModelRole, ContentPolicyBlockedError
from research_os.research.planning import plan_admitted_hypothesis
from research_os.research.proposals import (
    HypothesisChallenge,
    HypothesisProposal,
    ProposalAuthorityError,
)
from research_os.research.types import ExperimentPlan, ResearchInputError


@dataclass(frozen=True)
class ProposeResearchHypothesisCommand:
    research_run_id: str
    research_question: str
    budget_id: str
    target_reference: str
    correlation_id: str
    untrusted_external: tuple[ExternalContentSource, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    echo_message: str = "ping"
    context_budget: ContextBudget | None = None
    differential_id: str | None = None
    invariant_id: str | None = None
    chain_id: str | None = None
    opportunity_id: str | None = None
    change_event_id: str | None = None


@dataclass(frozen=True)
class ProposeResearchHypothesisResult:
    admission: AdmissionDecision
    context: ResearchContext
    experiment_plan: ExperimentPlan | None
    hypothesis_id: str | None
    generator_reasoning_id: str | None
    falsifier_reasoning_id: str | None
    admission_record_id: str | None
    generator_calls: int
    falsifier_calls: int

    @property
    def outcome(self) -> AdmissionOutcome:
        return self.admission.outcome


class ProposeResearchHypothesis:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        model: ModelPort,
        *,
        clock: Clock | None = None,
        context_builder: ResearchContextBuilder | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._model = model
        self._clock = clock or SystemClock()
        self._builder = context_builder or ResearchContextBuilder()

    def execute(
        self, command: ProposeResearchHypothesisCommand
    ) -> ProposeResearchHypothesisResult:
        with self._uow_factory.open() as uow:
            run = uow.research_runs.get(command.research_run_id)
            if run is None:
                raise ApplicationError("research run not found")
            budget = uow.issued_budgets.get(command.budget_id)
            if budget is None or budget.research_run_id != command.research_run_id:
                raise ApplicationError("issued budget not found for research run")
            observation_sources = tuple(
                ObservationSource(
                    observation_id=record.observation_id,
                    observation_kind=record.observation_kind,
                    payload=dict(record.payload),
                )
                for record in uow.observations.list_for_research_run(command.research_run_id)
            )
            hypothesis_sources = tuple(
                HypothesisSource(hypothesis_id=record.hypothesis_id, claim=record.claim)
                for record in uow.hypotheses.list_for_research_run(command.research_run_id)
            )
            experiment_sources = tuple(
                ExperimentSource(
                    experiment_id=record.experiment_id,
                    hypothesis_id=record.hypothesis_id,
                    execution_state=record.execution_state,
                )
                for record in uow.experiments.list_for_research_run(command.research_run_id)
            )
            inference_sources = tuple(
                InferenceSource(
                    inference_id=record.inference_id,
                    statement=record.statement,
                    source_references=record.source_refs,
                )
                for record in uow.target_inferences.list_for_research_run(
                    command.research_run_id
                )
            )
            differential_sources: tuple[DifferentialContextSource, ...] = ()
            if command.differential_id is not None:
                differential = uow.differential_observations.get(command.differential_id)
                if differential is None:
                    raise ApplicationError("differential observation not found")
                if differential.research_run_id != command.research_run_id:
                    raise ApplicationError("differential observation is cross-run")
                differential_sources = (
                    DifferentialContextSource(
                        differential_id=differential.differential_id,
                        statement=(
                            "Diagnostic differential comparison. Difference is not a "
                            "vulnerability and not Evidence."
                        ),
                        source_references=differential.source_refs,
                        interpretation=differential.interpretation,
                        payload={
                            "changed_dimensions": list(differential.changed_dimensions),
                            "common_dimensions": list(differential.common_dimensions),
                            "observed_differences": dict(differential.observed_differences),
                            "observed_similarities": dict(
                                differential.observed_similarities
                            ),
                        },
                    ),
                )
            invariant_sources: tuple[InvariantContextSource, ...] = ()
            if command.invariant_id is not None:
                invariant = uow.invariant_hypotheses.get(command.invariant_id)
                if invariant is None:
                    raise ApplicationError("invariant hypothesis not found")
                if invariant.research_run_id != command.research_run_id:
                    raise ApplicationError("invariant hypothesis is cross-run")
                invariant_sources = (
                    InvariantContextSource(
                        invariant_id=invariant.invariant_id,
                        statement=invariant.expected_behavior,
                        source_references=invariant.source_refs,
                        payload={
                            "status": invariant.status,
                            "kind": invariant.invariant_kind,
                            "counterexample_refs": list(invariant.counterexample_refs),
                        },
                    ),
                )
            chain_sources: tuple[ChainContextSource, ...] = ()
            if command.chain_id is not None:
                chain = uow.chain_hypotheses.get(command.chain_id)
                if chain is None:
                    raise ApplicationError("chain hypothesis not found")
                if chain.research_run_id != command.research_run_id:
                    raise ApplicationError("chain hypothesis is cross-run")
                chain_sources = (
                    ChainContextSource(
                        chain_id=chain.chain_id,
                        statement=(
                            "Diagnostic chain hypothesis. Sequence is not causality "
                            "and not an exploit."
                        ),
                        source_references=chain.source_refs,
                        payload={
                            "depth": len(chain.steps) - 1,
                            "structural_identity": chain.structural_identity,
                            "descriptive_features": dict(chain.descriptive_features),
                        },
                    ),
                )
            opportunity_sources: tuple[OpportunityContextSource, ...] = ()
            if command.opportunity_id is not None:
                opportunity = uow.research_opportunities.get(command.opportunity_id)
                if opportunity is None:
                    raise ApplicationError("research opportunity not found")
                if opportunity.research_run_id != command.research_run_id:
                    raise ApplicationError("research opportunity is cross-run")
                opportunity_sources = (
                    OpportunityContextSource(
                        opportunity_id=opportunity.opportunity_id,
                        statement=(
                            "Selected diagnostic research opportunity. Selection is not "
                            "Hypothesis truth and not Core authorization."
                        ),
                        source_references=opportunity.source_refs,
                        payload={
                            "opportunity_kind": opportunity.opportunity_kind,
                            "mode": opportunity.mode,
                            "structural_identity": opportunity.structural_identity,
                        },
                    ),
                )
            change_sources: tuple[ChangeEventContextSource, ...] = ()
            if command.change_event_id is not None:
                change = uow.change_events.get(command.change_event_id)
                if change is None:
                    raise ApplicationError("change event not found")
                if change.research_run_id != command.research_run_id:
                    raise ApplicationError("change event is cross-run")
                change_sources = (
                    ChangeEventContextSource(
                        change_event_id=change.change_event_id,
                        statement=change.statement,
                        source_references=change.source_refs,
                        payload={
                            "category": change.category,
                            "baseline_snapshot_id": change.baseline_snapshot_id,
                            "variant_snapshot_id": change.variant_snapshot_id,
                        },
                    ),
                )
            uow.commit()

        context = self._builder.build(
            research_run_id=command.research_run_id,
            research_question=command.research_question,
            observations=observation_sources,
            prior_hypotheses=hypothesis_sources,
            experiments=experiment_sources,
            untrusted_external=command.untrusted_external,
            inferences=inference_sources,
            differentials=differential_sources,
            invariant_hypotheses=invariant_sources,
            chain_hypotheses=chain_sources,
            research_opportunities=opportunity_sources,
            change_events=change_sources,
            unresolved_questions=command.unresolved_questions,
            budget=command.context_budget,
        )

        proposal: HypothesisProposal | None = None
        challenge: HypothesisChallenge | None = None
        generator_result: ModelCallResult | None = None
        falsifier_result: ModelCallResult | None = None
        generator_calls = 0
        falsifier_calls = 0

        try:
            generated = generate_proposal(
                context, self._model, correlation_id=command.correlation_id
            )
            generator_calls = 1
            generator_result = generated.model_result
            proposal = generated.proposal
        except ContentPolicyBlockedError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.MODEL_INVOCATION_FAILED,
                reason=str(exc),
                reason_code="CONTENT_POLICY_BLOCKED",
                proposal=None,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )
        except ModelPortError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.MODEL_INVOCATION_FAILED,
                reason=str(exc),
                reason_code="MODEL_INVOCATION_FAILED",
                proposal=None,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )
        except ProposalAuthorityError as exc:
            generator_result = getattr(exc, "model_result", None)
            generator_calls = 1 if generator_result is not None else generator_calls
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_POLICY_CONFLICT,
                reason=str(exc),
                reason_code="POLICY_CONFLICT",
                proposal=None,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                generator_result=generator_result,
                generator_structured=_structured_or_raw(generator_result),
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )
        except ResearchInputError as exc:
            generator_result = getattr(exc, "model_result", None)
            generator_calls = 1 if generator_result is not None else generator_calls
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_UNTESTABLE,
                reason=str(exc),
                reason_code="INVALID_STRUCTURED_OUTPUT",
                proposal=None,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                generator_result=generator_result,
                generator_structured=_structured_or_raw(generator_result),
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )

        try:
            challenged = generate_challenge(
                context,
                proposal,
                self._model,
                correlation_id=command.correlation_id,
            )
            falsifier_calls = 1
            falsifier_result = challenged.model_result
            challenge = challenged.challenge
        except ContentPolicyBlockedError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.MODEL_INVOCATION_FAILED,
                reason=str(exc),
                reason_code="CONTENT_POLICY_BLOCKED",
                proposal=proposal,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                proposal=proposal,
                generator_result=generator_result,
                generator_structured=proposal.to_mapping(),
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )
        except ModelPortError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.MODEL_INVOCATION_FAILED,
                reason=str(exc),
                reason_code="MODEL_INVOCATION_FAILED",
                proposal=proposal,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                proposal=proposal,
                generator_result=generator_result,
                generator_structured=proposal.to_mapping(),
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )
        except ProposalAuthorityError as exc:
            falsifier_result = getattr(exc, "model_result", None)
            falsifier_calls = 1 if falsifier_result is not None else falsifier_calls
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_POLICY_CONFLICT,
                reason=str(exc),
                reason_code="POLICY_CONFLICT",
                proposal=proposal,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                proposal=proposal,
                generator_result=generator_result,
                generator_structured=proposal.to_mapping(),
                falsifier_result=falsifier_result,
                falsifier_structured=_structured_or_raw(falsifier_result),
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )
        except ResearchInputError as exc:
            falsifier_result = getattr(exc, "model_result", None)
            falsifier_calls = 1 if falsifier_result is not None else falsifier_calls
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_UNTESTABLE,
                reason=str(exc),
                reason_code="INVALID_STRUCTURED_OUTPUT",
                proposal=proposal,
                challenge=None,
            )
            return self._persist_cycle(
                command,
                context,
                admission,
                proposal=proposal,
                generator_result=generator_result,
                generator_structured=proposal.to_mapping(),
                falsifier_result=falsifier_result,
                falsifier_structured=_structured_or_raw(falsifier_result),
                generator_calls=generator_calls,
                falsifier_calls=falsifier_calls,
            )

        admission = admit_hypothesis(context, proposal, challenge)
        return self._persist_cycle(
            command,
            context,
            admission,
            proposal=proposal,
            challenge=challenge,
            generator_result=generator_result,
            generator_structured=proposal.to_mapping(),
            falsifier_result=falsifier_result,
            falsifier_structured=challenge.to_mapping() if challenge is not None else None,
            generator_calls=generator_calls,
            falsifier_calls=falsifier_calls,
        )

    def _persist_cycle(
        self,
        command: ProposeResearchHypothesisCommand,
        context: ResearchContext,
        admission: AdmissionDecision,
        *,
        proposal: HypothesisProposal | None = None,
        challenge: HypothesisChallenge | None = None,
        generator_result: ModelCallResult | None = None,
        generator_structured: Mapping[str, Any] | None = None,
        falsifier_result: ModelCallResult | None = None,
        falsifier_structured: Mapping[str, Any] | None = None,
        generator_calls: int,
        falsifier_calls: int,
    ) -> ProposeResearchHypothesisResult:
        now = self._clock.now()
        admitted = admission.admitted
        hypothesis_id = new_opaque_id() if admitted else None
        generator_reasoning_id = new_opaque_id() if generator_result is not None else None
        falsifier_reasoning_id = new_opaque_id() if falsifier_result is not None else None
        admission_record_id = new_opaque_id()
        plan = None
        if admitted and proposal is not None and challenge is not None and hypothesis_id is not None:
            plan = plan_admitted_hypothesis(
                hypothesis_id,
                proposal,
                challenge,
                budget_id=command.budget_id,
                target_reference=command.target_reference,
                message=command.echo_message,
            )
        with self._uow_factory.open() as uow:
            if hypothesis_id is not None and proposal is not None:
                uow.hypotheses.insert(
                    HypothesisRecord(
                        hypothesis_id=hypothesis_id,
                        research_run_id=command.research_run_id,
                        claim=proposal.proposed_claim,
                        created_at=now,
                        origin_reference=generator_reasoning_id,
                    )
                )
            if generator_reasoning_id is not None and generator_result is not None:
                uow.research_reasoning.insert(
                    self._reasoning_record(
                        reasoning_record_id=generator_reasoning_id,
                        research_run_id=command.research_run_id,
                        hypothesis_id=hypothesis_id,
                        role=ModelRole.GENERATOR,
                        generated=generator_result,
                        structured_output=dict(generator_structured or generator_result.structured_output),
                        fingerprint=context.fingerprint,
                        correlation_id=command.correlation_id,
                        created_at=now,
                    )
                )
            if falsifier_reasoning_id is not None and falsifier_result is not None:
                uow.research_reasoning.insert(
                    self._reasoning_record(
                        reasoning_record_id=falsifier_reasoning_id,
                        research_run_id=command.research_run_id,
                        hypothesis_id=hypothesis_id,
                        role=ModelRole.FALSIFIER,
                        generated=falsifier_result,
                        structured_output=dict(
                            falsifier_structured or falsifier_result.structured_output
                        ),
                        fingerprint=context.fingerprint,
                        correlation_id=command.correlation_id,
                        created_at=now,
                    )
                )
            uow.research_admissions.insert(
                ResearchAdmissionRecord(
                    admission_record_id=admission_record_id,
                    research_run_id=command.research_run_id,
                    outcome=admission.outcome.value,
                    reason=admission.reason,
                    reason_code=admission.reason_code,
                    context_fingerprint=context.fingerprint,
                    created_at=now,
                    generator_reasoning_record_id=generator_reasoning_id,
                    falsifier_reasoning_record_id=falsifier_reasoning_id,
                    admitted_hypothesis_id=hypothesis_id,
                )
            )
            uow.commit()
        return ProposeResearchHypothesisResult(
            admission=admission,
            context=context,
            experiment_plan=plan,
            hypothesis_id=hypothesis_id,
            generator_reasoning_id=generator_reasoning_id,
            falsifier_reasoning_id=falsifier_reasoning_id,
            admission_record_id=admission_record_id,
            generator_calls=generator_calls,
            falsifier_calls=falsifier_calls,
        )

    def _reasoning_record(
        self,
        *,
        reasoning_record_id: str,
        research_run_id: str,
        hypothesis_id: str | None,
        role: ModelRole,
        generated: ModelCallResult,
        structured_output: dict[str, object],
        fingerprint: str,
        correlation_id: str,
        created_at,
    ) -> ResearchReasoningRecord:
        return ResearchReasoningRecord(
            reasoning_record_id=reasoning_record_id,
            research_run_id=research_run_id,
            hypothesis_id=hypothesis_id,
            role=role.value,
            adapter_identity=generated.adapter_identity,
            provider_adapter_identity=generated.provider_adapter_identity,
            correlation_id=correlation_id,
            context_fingerprint=fingerprint,
            structured_output=structured_output,
            created_at=created_at,
            model_id=generated.model_id,
            model_version=generated.model_version,
        )


def _structured_or_raw(result: ModelCallResult | None) -> Mapping[str, Any] | None:
    if result is None:
        return None
    return dict(result.structured_output)
