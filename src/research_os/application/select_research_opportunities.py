"""Select bounded diagnostic research opportunities. Does not dispatch a Worker."""

from __future__ import annotations

from dataclasses import dataclass

from research_os.application.errors import ApplicationError
from research_os.application.identity import new_opaque_id
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.core.enums import ActorType
from research_os.data.records import (
    AuditEventRecord,
    ResearchOpportunityRecord,
    ResearchSelectionRecord,
)
from research_os.research.exploration import (
    DiagnosticOpportunitySources,
    NegativeKnowledge,
    ResearchPolicyBudget,
    ResearchSelectionDecision,
    SelectionOutcome,
    opportunity_structural_identity,
    OpportunityKind,
    propose_diagnostic_opportunities,
    select_research_opportunities,
)


@dataclass(frozen=True)
class SelectResearchOpportunitiesCommand:
    research_run_id: str
    budget: ResearchPolicyBudget | None = None


@dataclass(frozen=True)
class SelectResearchOpportunitiesResult:
    decisions: tuple[ResearchSelectionDecision, ...]

    @property
    def selected(self) -> tuple[ResearchSelectionDecision, ...]:
        return tuple(item for item in self.decisions if item.selected)


class SelectResearchOpportunities:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        *,
        clock: Clock | None = None,
        actor_id: str = "control-plane",
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock or SystemClock()
        self._actor_id = actor_id

    def execute(
        self, command: SelectResearchOpportunitiesCommand
    ) -> SelectResearchOpportunitiesResult:
        with self._uow_factory.open() as uow:
            run = uow.research_runs.get(command.research_run_id)
            if run is None:
                raise ApplicationError("research run not found")
            differentials = uow.differential_observations.list_for_research_run(
                command.research_run_id
            )
            invariants = uow.invariant_hypotheses.list_for_research_run(command.research_run_id)
            chains = uow.chain_hypotheses.list_for_research_run(command.research_run_id)
            changes = uow.change_events.list_for_research_run(command.research_run_id)
            hypotheses = uow.hypotheses.list_for_research_run(command.research_run_id)
            assessments = uow.hypothesis_assessments.list_for_research_run(
                command.research_run_id
            )
            negatives: list[NegativeKnowledge] = []
            followup_direction = (
                "Continue the existing diagnostic hypothesis with a control echo."
            )
            for assessment in assessments:
                if assessment.assessment_outcome != "CONTRADICTS_PREDICTION":
                    continue
                context = f"hypothesis:{assessment.hypothesis_id}"
                identity = opportunity_structural_identity(
                    kind=OpportunityKind.HYPOTHESIS_FOLLOWUP,
                    source_refs=(assessment.hypothesis_id,),
                    context_signature=context,
                    proposed_direction=followup_direction,
                )
                negatives.append(
                    NegativeKnowledge(
                        structural_identity=identity,
                        context_signature=context,
                        strategy_version="exploration.diagnostic.echo.v1",
                        assessment_ref=assessment.assessment_id,
                    )
                )
            previously = frozenset(
                item.structural_identity
                for item in uow.research_opportunities.list_for_research_run(
                    command.research_run_id
                )
            )
            generated = propose_diagnostic_opportunities(
                command.research_run_id,
                DiagnosticOpportunitySources(
                    differential_ids=tuple(item.differential_id for item in differentials),
                    invariant_ids=tuple(item.invariant_id for item in invariants),
                    chain_ids=tuple(item.chain_id for item in chains),
                    change_event_ids=tuple(item.change_event_id for item in changes),
                    hypothesis_ids=tuple(item.hypothesis_id for item in hypotheses),
                    negative_knowledge=tuple(negatives),
                ),
                id_prefix=new_opaque_id(),
            )
            decisions = select_research_opportunities(
                generated,
                research_run_id=command.research_run_id,
                budget=command.budget,
                negative_knowledge=tuple(negatives),
                previously_selected_identities=previously,
            )
            now = self._clock.now()
            for decision in decisions:
                opportunity = decision.opportunity
                if decision.outcome is SelectionOutcome.SELECT:
                    uow.research_opportunities.insert(
                        ResearchOpportunityRecord(
                            opportunity_id=opportunity.opportunity_id,
                            research_run_id=opportunity.research_run_id,
                            opportunity_kind=opportunity.opportunity_kind.value,
                            mode=opportunity.mode.value,
                            source_refs=opportunity.source_refs,
                            proposed_direction=opportunity.proposed_direction,
                            unresolved_question=opportunity.unresolved_question,
                            expected_information_value_description=(
                                opportunity.expected_information_value_description
                            ),
                            assumptions=opportunity.assumptions,
                            dimensions=opportunity.dimensions.to_mapping(),
                            context_signature=opportunity.context_signature,
                            novelty_composition_marker=opportunity.novelty_composition_marker,
                            prior_attempt_refs=opportunity.prior_attempt_refs,
                            structural_identity=opportunity.structural_identity,
                            strategy_version=opportunity.strategy_version,
                            created_at=now,
                        )
                    )
                uow.research_selections.insert(
                    ResearchSelectionRecord(
                        selection_id=new_opaque_id(),
                        research_run_id=command.research_run_id,
                        opportunity_id=opportunity.opportunity_id,
                        outcome=decision.outcome.value,
                        reason_codes=decision.reason_codes,
                        structural_identity=opportunity.structural_identity,
                        created_at=now,
                    )
                )
            uow.audit_events.insert(
                AuditEventRecord(
                    audit_event_id=new_opaque_id(),
                    occurred_at=now,
                    actor_id=self._actor_id,
                    actor_type=ActorType.CONTROL_PLANE.value,
                    event_type="RESEARCH_OPPORTUNITIES_SELECTED",
                    subject_type="research_run",
                    subject_id=command.research_run_id,
                    payload={
                        "selected": sum(1 for item in decisions if item.selected),
                        "not_authorization": True,
                        "not_a_vulnerability": True,
                    },
                )
            )
            uow.commit()
        return SelectResearchOpportunitiesResult(decisions=decisions)
