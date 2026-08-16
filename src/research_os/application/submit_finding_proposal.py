"""Submit a FindingProposal from a VALIDATED Candidate. Application coordinates.

Does not create Finding, Approval, or Human Review. Does not auto-approve.
"""

from __future__ import annotations

from dataclasses import dataclass

from research_os.application.errors import ApplicationError
from research_os.application.identity import new_opaque_id
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.core.enums import ActorType
from research_os.data.records import AuditEventRecord, FindingProposalRecord
from research_os.research.candidate import CandidateState
from research_os.research.finding_proposal import (
    FindingProposalAdmissionContext,
    FindingProposalAdmissionOutcome,
    FindingProposalDraft,
    FindingProposalState,
    admit_finding_proposal,
    propose_diagnostic_finding_proposal,
)


@dataclass(frozen=True)
class SubmitFindingProposalCommand:
    candidate_id: str
    draft: FindingProposalDraft | None = None


@dataclass(frozen=True)
class SubmitFindingProposalResult:
    outcome: FindingProposalAdmissionOutcome
    proposal_id: str | None
    state: FindingProposalState | None
    reason_codes: tuple[str, ...]


class SubmitFindingProposal:
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

    def execute(self, command: SubmitFindingProposalCommand) -> SubmitFindingProposalResult:
        with self._uow_factory.open() as uow:
            candidate = uow.candidates.get(command.candidate_id)
            if candidate is None:
                raise ApplicationError("candidate not found")
            try:
                state = CandidateState(candidate.state)
            except ValueError as exc:
                raise ApplicationError("candidate state is not a CandidateState") from exc
            verifications = uow.verifications.list_for_candidate(candidate.candidate_id)
            context = FindingProposalAdmissionContext(
                candidate_id=candidate.candidate_id,
                candidate_state=state,
                research_run_id=candidate.research_run_id,
                evidence_ids=candidate.evidence_ids,
                verification_ids=tuple(item.verification_id for item in verifications),
                classification=candidate.classification,
            )
            draft = command.draft
            if draft is None:
                draft = propose_diagnostic_finding_proposal(
                    context, proposal_id=new_opaque_id()
                )
            if draft is None:
                raise ApplicationError(
                    "no diagnostic FindingProposal can be built from this Candidate"
                )
            decision = admit_finding_proposal(draft, context)
            proposal_id = draft.proposal_id if decision.creates_proposal else None
            if proposal_id is not None:
                assert decision.initial_state is FindingProposalState.PROPOSED
                uow.finding_proposals.insert(
                    FindingProposalRecord(
                        proposal_id=proposal_id,
                        candidate_id=draft.candidate_id,
                        research_run_id=draft.research_run_id,
                        title=draft.title,
                        claim=draft.claim,
                        classification=candidate.classification,
                        state=decision.initial_state.value,
                        evidence_ids=draft.evidence_ids,
                        verification_ids=draft.verification_ids,
                        content_fingerprint=draft.content_fingerprint,
                        created_at=self._clock.now(),
                    )
                )
                uow.audit_events.insert(
                    AuditEventRecord(
                        audit_event_id=new_opaque_id(),
                        occurred_at=self._clock.now(),
                        actor_id=self._actor_id,
                        actor_type=ActorType.CONTROL_PLANE.value,
                        event_type="FINDING_PROPOSAL_CREATED",
                        subject_type="finding_proposal",
                        subject_id=proposal_id,
                        payload={
                            "candidate_id": candidate.candidate_id,
                            "not_a_vulnerability": True,
                        },
                    )
                )
            uow.commit()
        return SubmitFindingProposalResult(
            outcome=decision.outcome,
            proposal_id=proposal_id,
            state=decision.initial_state,
            reason_codes=decision.reason_codes,
        )
