"""Propose a research Hypothesis through Generator, Falsifier, and admission.

Does not execute a Worker. Does not create Evidence or Finding.
Core still owns later execution authorization.
"""

from __future__ import annotations

from dataclasses import dataclass

from research_os.application.errors import ApplicationError
from research_os.application.identity import new_opaque_id
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.data.records import HypothesisRecord, ResearchReasoningRecord
from research_os.research.admission import AdmissionDecision, AdmissionOutcome, admit_hypothesis
from research_os.research.context import (
    ContextBudget,
    ExperimentSource,
    ExternalContentSource,
    HypothesisSource,
    ObservationSource,
    ResearchContext,
    ResearchContextBuilder,
)
from research_os.research.cycle import generate_challenge, generate_proposal
from research_os.research.model_port import ModelPort, ModelRole
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


@dataclass(frozen=True)
class ProposeResearchHypothesisResult:
    admission: AdmissionDecision
    context: ResearchContext
    experiment_plan: ExperimentPlan | None
    hypothesis_id: str | None
    generator_reasoning_id: str | None
    falsifier_reasoning_id: str | None
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
            uow.commit()

        context = self._builder.build(
            research_run_id=command.research_run_id,
            research_question=command.research_question,
            observations=observation_sources,
            prior_hypotheses=hypothesis_sources,
            experiments=experiment_sources,
            untrusted_external=command.untrusted_external,
            unresolved_questions=command.unresolved_questions,
            budget=command.context_budget,
        )

        proposal: HypothesisProposal | None
        challenge: HypothesisChallenge | None = None
        generator_calls = 0
        falsifier_calls = 0
        generated = None
        challenged = None
        try:
            generated = generate_proposal(
                context, self._model, correlation_id=command.correlation_id
            )
            generator_calls = 1
            proposal = generated.proposal
        except ProposalAuthorityError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_POLICY_CONFLICT,
                reason=str(exc),
                proposal=None,
                challenge=None,
            )
            return self._empty_result(admission, context, generator_calls, 0)
        except ResearchInputError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_UNTESTABLE,
                reason=str(exc),
                proposal=None,
                challenge=None,
            )
            return self._empty_result(admission, context, generator_calls, 0)

        try:
            challenged = generate_challenge(
                context,
                proposal,
                self._model,
                correlation_id=command.correlation_id,
            )
            falsifier_calls = 1
            challenge = challenged.challenge
        except ProposalAuthorityError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_POLICY_CONFLICT,
                reason=str(exc),
                proposal=proposal,
                challenge=None,
            )
            return self._empty_result(admission, context, generator_calls, falsifier_calls)
        except ResearchInputError as exc:
            admission = AdmissionDecision(
                outcome=AdmissionOutcome.REJECTED_UNTESTABLE,
                reason=str(exc),
                proposal=proposal,
                challenge=None,
            )
            return self._empty_result(admission, context, generator_calls, falsifier_calls)

        admission = admit_hypothesis(context, proposal, challenge)
        if not admission.admitted:
            return self._empty_result(
                admission, context, generator_calls, falsifier_calls
            )

        hypothesis_id = new_opaque_id()
        generator_reasoning_id = new_opaque_id()
        falsifier_reasoning_id = new_opaque_id()
        now = self._clock.now()
        assert generated is not None
        assert challenged is not None
        plan = plan_admitted_hypothesis(
            hypothesis_id,
            proposal,
            challenge,
            budget_id=command.budget_id,
            target_reference=command.target_reference,
            message=command.echo_message,
        )
        with self._uow_factory.open() as uow:
            uow.hypotheses.insert(
                HypothesisRecord(
                    hypothesis_id=hypothesis_id,
                    research_run_id=command.research_run_id,
                    claim=proposal.proposed_claim,
                    created_at=now,
                    origin_reference=generator_reasoning_id,
                )
            )
            uow.research_reasoning.insert(
                self._reasoning_record(
                    reasoning_record_id=generator_reasoning_id,
                    research_run_id=command.research_run_id,
                    hypothesis_id=hypothesis_id,
                    role=ModelRole.GENERATOR,
                    generated=generated.model_result,
                    structured_output=proposal.to_mapping(),
                    fingerprint=context.fingerprint,
                    correlation_id=command.correlation_id,
                    created_at=now,
                )
            )
            uow.research_reasoning.insert(
                self._reasoning_record(
                    reasoning_record_id=falsifier_reasoning_id,
                    research_run_id=command.research_run_id,
                    hypothesis_id=hypothesis_id,
                    role=ModelRole.FALSIFIER,
                    generated=challenged.model_result,
                    structured_output=challenge.to_mapping(),
                    fingerprint=context.fingerprint,
                    correlation_id=command.correlation_id,
                    created_at=now,
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
            generator_calls=generator_calls,
            falsifier_calls=falsifier_calls,
        )

    def _empty_result(
        self,
        admission: AdmissionDecision,
        context: ResearchContext,
        generator_calls: int,
        falsifier_calls: int,
    ) -> ProposeResearchHypothesisResult:
        return ProposeResearchHypothesisResult(
            admission=admission,
            context=context,
            experiment_plan=None,
            hypothesis_id=None,
            generator_reasoning_id=None,
            falsifier_reasoning_id=None,
            generator_calls=generator_calls,
            falsifier_calls=falsifier_calls,
        )

    def _reasoning_record(
        self,
        *,
        reasoning_record_id: str,
        research_run_id: str,
        hypothesis_id: str,
        role: ModelRole,
        generated,
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
