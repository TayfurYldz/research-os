"""Move a FindingProposal into HUMAN_REVIEW. Application coordinates; Research decides."""

from __future__ import annotations

from dataclasses import dataclass

from research_os.application.errors import ApplicationError
from research_os.application.ports import UnitOfWorkFactory
from research_os.research.finding_proposal import (
    FindingProposalState,
    start_finding_proposal_review,
)
from research_os.research.types import ResearchInputError


@dataclass(frozen=True)
class StartHumanReviewCommand:
    proposal_id: str


@dataclass(frozen=True)
class StartHumanReviewResult:
    proposal_id: str
    state: FindingProposalState


class StartHumanReview:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def execute(self, command: StartHumanReviewCommand) -> StartHumanReviewResult:
        with self._uow_factory.open() as uow:
            proposal = uow.finding_proposals.get(command.proposal_id)
            if proposal is None:
                raise ApplicationError("finding proposal not found")
            try:
                current = FindingProposalState(proposal.state)
                next_state = start_finding_proposal_review(current)
            except (ResearchInputError, ValueError) as exc:
                raise ApplicationError(str(exc)) from exc
            uow.finding_proposals.set_state(proposal.proposal_id, next_state.value)
            uow.commit()
        return StartHumanReviewResult(proposal_id=proposal.proposal_id, state=next_state)
