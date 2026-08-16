"""Human Approval eligibility. Finding creation is not implemented in A2."""

from dataclasses import dataclass

from research_os.core.enums import ActorType, ApprovalDecision, ReasonCode
from research_os.core.errors import CoreInputError
from research_os.core.identity import require_opaque_id


@dataclass(frozen=True)
class ApprovalView:
    approval_id: str
    subject_reference: str
    decision: ApprovalDecision
    decided_by: str
    actor_type: ActorType
    recorded: bool

    def __post_init__(self) -> None:
        require_opaque_id(self.approval_id, "approval_id")
        require_opaque_id(self.subject_reference, "subject_reference")
        require_opaque_id(self.decided_by, "decided_by")
        if not isinstance(self.decision, ApprovalDecision):
            raise CoreInputError("decision must be ApprovalDecision")
        if not isinstance(self.actor_type, ActorType):
            raise CoreInputError("actor_type must be ActorType")
        if not isinstance(self.recorded, bool):
            raise CoreInputError("recorded must be bool")


@dataclass(frozen=True)
class ApprovalCheck:
    authorizes: bool
    require_human_review: bool
    reason_code: ReasonCode
    approval_id: str | None


def check_approval(
    approval: ApprovalView | None,
    requested_subject: str,
) -> ApprovalCheck:
    require_opaque_id(requested_subject, "requested_subject")
    if approval is None:
        return ApprovalCheck(False, True, ReasonCode.APPROVAL_REQUIRED, None)
    if not approval.recorded:
        return ApprovalCheck(
            False, False, ReasonCode.APPROVAL_NOT_RECORDED, approval.approval_id
        )
    if approval.actor_type is not ActorType.HUMAN_OPERATOR:
        return ApprovalCheck(
            False, False, ReasonCode.APPROVAL_INVALID_ACTOR, approval.approval_id
        )
    if approval.subject_reference != requested_subject:
        return ApprovalCheck(
            False, False, ReasonCode.APPROVAL_SUBJECT_MISMATCH, approval.approval_id
        )
    if approval.decision is ApprovalDecision.REJECT:
        return ApprovalCheck(
            False, False, ReasonCode.APPROVAL_REJECTED, approval.approval_id
        )
    return ApprovalCheck(True, False, ReasonCode.ALLOWED, approval.approval_id)
