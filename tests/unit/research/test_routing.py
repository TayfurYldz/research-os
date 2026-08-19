"""SD-G4 routing price-class policy tests."""

from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.research.model_runtime import (
    AuthMode,
    ModelPriceClass,
    ModelRuntimeIdentity,
    RuntimeClass,
    RuntimeKind,
)
from research_os.research.model_port import ModelRole
from research_os.research.routing import (
    ROUTING_POLICY_VERSION,
    CandidateLocality,
    LocalityConstraint,
    RoutingBudget,
    RoutingOutcome,
    RoutingReasonCode,
    RoutingRequest,
    RuntimeCandidate,
    RuntimeQualityObservation,
    select_runtime,
)


def _identity(
    adapter_id: str,
    *,
    price_class: ModelPriceClass = ModelPriceClass.CHEAP,
) -> ModelRuntimeIdentity:
    return ModelRuntimeIdentity(
        runtime_kind=RuntimeKind.API,
        runtime_class=RuntimeClass.INFERENCE_RUNTIME,
        adapter_id=adapter_id,
        runtime_id=adapter_id,
        auth_mode=AuthMode.API_KEY,
        configuration_fingerprint="fp",
        price_class=price_class,
    )


def _candidate(
    adapter_id: str,
    *,
    price_class: ModelPriceClass = ModelPriceClass.CHEAP,
    available: bool = True,
) -> RuntimeCandidate:
    return RuntimeCandidate(
        identity=_identity(adapter_id, price_class=price_class),
        available=available,
        authenticated=True,
        structured_output_compatible=True,
        locality=CandidateLocality.REMOTE,
    )


def _request(
    *,
    task_class: str | None = None,
    escalation_reason: str | None = None,
    candidates: tuple[RuntimeCandidate, ...] = (),
) -> RoutingRequest:
    return RoutingRequest(
        role=ModelRole.GENERATOR,
        candidates=candidates,
        budget=RoutingBudget(max_runtime_attempts=2, max_fallback_attempts=1),
        task_class=task_class,
        escalation_reason=escalation_reason,
    )


class PriceClassRoutingTests(unittest.TestCase):
    def test_default_selects_cheap(self) -> None:
        decision = select_runtime(
            _request(
                candidates=(
                    _candidate("cheap-1"),
                    _candidate("expensive-1", price_class=ModelPriceClass.EXPENSIVE),
                )
            )
        )
        self.assertEqual(decision.outcome, RoutingOutcome.SELECT)
        self.assertEqual(decision.selected_identity.adapter_id, "cheap-1")
        self.assertIn(RoutingReasonCode.CHEAP_CLASS_SELECTED.value, decision.reason_codes)

    def test_monitoring_task_class_blocks_all_calls(self) -> None:
        decision = select_runtime(
            _request(
                task_class="monitoring",
                candidates=(_candidate("cheap-1"), _candidate("expensive-1", price_class=ModelPriceClass.EXPENSIVE)),
            )
        )
        self.assertEqual(decision.outcome, RoutingOutcome.BLOCKED_POLICY)
        self.assertIn(RoutingReasonCode.MONITORING_CLASS_DISABLED.value, decision.reason_codes)
        self.assertIsNone(decision.selected_identity)

    def test_expensive_task_class_selects_expensive(self) -> None:
        decision = select_runtime(
            _request(
                task_class="finding_proposal_qa",
                candidates=(
                    _candidate("cheap-1"),
                    _candidate("expensive-1", price_class=ModelPriceClass.EXPENSIVE),
                ),
            )
        )
        self.assertEqual(decision.outcome, RoutingOutcome.SELECT)
        self.assertEqual(decision.selected_identity.adapter_id, "expensive-1")
        self.assertIn(RoutingReasonCode.EXPENSIVE_CLASS_SELECTED.value, decision.reason_codes)

    def test_escalation_reason_selects_expensive(self) -> None:
        decision = select_runtime(
            _request(
                escalation_reason="cheap_model_returned_escalation_needed",
                candidates=(
                    _candidate("cheap-1"),
                    _candidate("expensive-1", price_class=ModelPriceClass.EXPENSIVE),
                ),
            )
        )
        self.assertEqual(decision.outcome, RoutingOutcome.SELECT)
        self.assertEqual(decision.selected_identity.adapter_id, "expensive-1")
        self.assertIn(RoutingReasonCode.ESCALATION_REQUIRED.value, decision.reason_codes)

    def test_expensive_required_but_no_expensive_candidate_blocks(self) -> None:
        decision = select_runtime(
            _request(
                task_class="finding_proposal_qa",
                candidates=(_candidate("cheap-1"),),
            )
        )
        self.assertEqual(decision.outcome, RoutingOutcome.BLOCKED_POLICY)


if __name__ == "__main__":
    unittest.main()
