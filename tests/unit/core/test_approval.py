from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.core import (
    ActorType,
    ApprovalDecision,
    ApprovalView,
    ExecutionDecisionKind,
    ReasonCode,
    SideEffectLevel,
    evaluate_execution,
)
from fixtures import base_request, human_approval


class ApprovalTests(unittest.TestCase):
    def test_correct_subject_required(self) -> None:
        approval = human_approval(subject="other-action")
        decision = evaluate_execution(
            base_request(
                side_effect_level=SideEffectLevel.LEVEL_2,
                requested_subject="action-1",
                approval=approval,
            )
        )
        self.assertEqual(decision.decision, ExecutionDecisionKind.DENY)
        self.assertEqual(decision.reason_code, ReasonCode.APPROVAL_SUBJECT_MISMATCH)

    def test_recorded_required(self) -> None:
        approval = ApprovalView(
            approval_id="appr-1",
            subject_reference="action-1",
            decision=ApprovalDecision.APPROVE,
            decided_by="operator-1",
            actor_type=ActorType.HUMAN_OPERATOR,
            recorded=False,
        )
        decision = evaluate_execution(
            base_request(side_effect_level=SideEffectLevel.LEVEL_2, approval=approval)
        )
        self.assertNotEqual(decision.decision, ExecutionDecisionKind.ALLOW)
        self.assertEqual(decision.reason_code, ReasonCode.APPROVAL_NOT_RECORDED)

    def test_human_actor_required(self) -> None:
        approval = ApprovalView(
            approval_id="appr-1",
            subject_reference="action-1",
            decision=ApprovalDecision.APPROVE,
            decided_by="cp-1",
            actor_type=ActorType.CONTROL_PLANE,
            recorded=True,
        )
        decision = evaluate_execution(
            base_request(side_effect_level=SideEffectLevel.LEVEL_2, approval=approval)
        )
        self.assertEqual(decision.decision, ExecutionDecisionKind.DENY)
        self.assertEqual(decision.reason_code, ReasonCode.APPROVAL_INVALID_ACTOR)

    def test_integration_cannot_approve(self) -> None:
        approval = ApprovalView(
            approval_id="appr-1",
            subject_reference="action-1",
            decision=ApprovalDecision.APPROVE,
            decided_by="strix",
            actor_type=ActorType.INTEGRATION,
            recorded=True,
        )
        decision = evaluate_execution(
            base_request(side_effect_level=SideEffectLevel.LEVEL_2, approval=approval)
        )
        self.assertEqual(decision.decision, ExecutionDecisionKind.DENY)
        self.assertEqual(decision.reason_code, ReasonCode.APPROVAL_INVALID_ACTOR)


if __name__ == "__main__":
    unittest.main()
