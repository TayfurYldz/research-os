from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.budget_enforced_model import BudgetEnforcedModelPort
from research_os.application.budget_consumption import BudgetConsumptionRejected
from research_os.core.enums import ScopeRuleEffect
from research_os.core.scope import ScopeEvaluationInput, ScopeRuleMatch
from research_os.data.budget_ledger import ledger_totals
from research_os.data.records import BudgetConsumptionRecord, IssuedBudgetRecord
from research_os.research.model_port import (
    ContentPolicyBlockedError,
    ModelCallRequest,
    ModelRole,
    ProviderAuthError,
    ProviderTimeoutError,
    StructuredOutputTransportError,
)
from research_os.research.orchestration import OrchestrationBounds
from support.fake_model import ScriptedModelPort
from support.fake_unit_of_work import FakeUnitOfWorkFactory, _Store
from support.spine import CREATED_AT, seed_authorization_run
from research_os.application.autonomous_research_controller import (
    AutonomousResearchController,
    StartAutonomousResearchCommand,
)
from support.recording_worker import RecordingWorkerPort


class FixedClock:
    def now(self):
        return CREATED_AT


def _request(role: ModelRole = ModelRole.GENERATOR) -> ModelCallRequest:
    return ModelCallRequest(
        role=role,
        correlation_id="c1",
        context_fingerprint="fp",
        instructions="propose",
        payload={"note": "ok"},
    )


def _seed(store: _Store, *, max_model_calls: int = 1) -> None:
    seed_authorization_run(store)
    store.issued_budgets["budget-1"] = IssuedBudgetRecord(
        budget_id="budget-1",
        research_run_id="run-1",
        max_requests=20,
        max_tool_calls=20,
        max_runtime_ms=10_000,
        max_concurrency=1,
        issued_at=CREATED_AT,
    )
    from research_os.application.autonomous_research_controller import AutonomousResearchController
    from support.recording_worker import RecordingWorkerPort

    factory = FakeUnitOfWorkFactory(store=store)
    controller = AutonomousResearchController(
        factory,
        RecordingWorkerPort(store=store),
        ScriptedModelPort(),
        clock=FixedClock(),
    )
    controller.start(
        StartAutonomousResearchCommand(
            research_run_id="run-1",
            budget_id="budget-1",
            target_reference="target-1",
            scope=ScopeEvaluationInput(
                matches=(ScopeRuleMatch("rule-allow", ScopeRuleEffect.ALLOW, True, "src"),),
                ambiguous=False,
            ),
            bounds=OrchestrationBounds(
                max_cycles=1,
                max_experiments=2,
                max_model_calls=max_model_calls,
                max_worker_invocations=4,
                max_elapsed_ms=60_000,
                max_selected_opportunities=1,
                max_runtime_fallback=0,
                side_effect_ceiling=0,
                allow_repeated_control_experiments=True,
            ),
        )
    )


class PreInvocationBudgetTests(unittest.TestCase):
    def test_generator_consumes_before_call_and_blocks_falsifier(self) -> None:
        store = _Store()
        _seed(store, max_model_calls=1)
        inner = ScriptedModelPort()
        port = BudgetEnforcedModelPort(
            inner,
            FakeUnitOfWorkFactory(store=store),
            budget_id="budget-1",
            research_run_id="run-1",
            cycle_id="cycle-1",
            clock=FixedClock(),
        )
        port.complete(_request(ModelRole.GENERATOR))
        self.assertEqual(len(inner.calls), 1)
        with self.assertRaises(BudgetConsumptionRejected):
            port.complete(_request(ModelRole.FALSIFIER))
        self.assertEqual(len(inner.calls), 1)
        totals = ledger_totals(list(store.budget_consumptions.values()))
        self.assertEqual(totals.model_calls, 1)
        self.assertEqual(totals.worker_requests, 0)

    def test_failed_calls_still_consume(self) -> None:
        cases = (
            ContentPolicyBlockedError("blocked"),
            ProviderTimeoutError("timeout"),
            ProviderAuthError("auth"),
            StructuredOutputTransportError("schema"),
        )
        for error in cases:
            with self.subTest(error=type(error).__name__):
                store = _Store()
                _seed(store, max_model_calls=1)
                inner = ScriptedModelPort(error=error)
                port = BudgetEnforcedModelPort(
                    inner,
                    FakeUnitOfWorkFactory(store=store),
                    budget_id="budget-1",
                    research_run_id="run-1",
                    cycle_id="cycle-1",
                    clock=FixedClock(),
                )
                with self.assertRaises(type(error)):
                    port.complete(_request())
                totals = ledger_totals(list(store.budget_consumptions.values()))
                self.assertEqual(totals.model_calls, 1)

    def test_replay_same_invocation_does_not_double_charge(self) -> None:
        store = _Store()
        _seed(store, max_model_calls=2)
        inner = ScriptedModelPort()
        factory = FakeUnitOfWorkFactory(store=store)
        port = BudgetEnforcedModelPort(
            inner,
            factory,
            budget_id="budget-1",
            research_run_id="run-1",
            cycle_id="cycle-1",
            clock=FixedClock(),
        )
        port.complete(_request())
        # Force the same identity by resetting attempt counter and reusing request id path
        port._attempts[ModelRole.GENERATOR] = 0
        port.complete(_request())
        totals = ledger_totals(list(store.budget_consumptions.values()))
        self.assertEqual(totals.model_calls, 1)

    def test_worker_request_does_not_increment_model_calls(self) -> None:
        store = _Store()
        _seed(store, max_model_calls=1)
        store.budget_consumptions["req-1"] = BudgetConsumptionRecord(
            consumption_id="cons-1",
            budget_id="budget-1",
            research_run_id="run-1",
            resource_type="REQUEST",
            amount=3,
            unit="count",
            occurred_at=CREATED_AT,
            provenance="worker",
            request_id="worker-req-1",
        )
        totals = ledger_totals(list(store.budget_consumptions.values()))
        self.assertEqual(totals.model_calls, 0)
        self.assertEqual(totals.worker_requests, 3)

    def test_model_call_does_not_increment_worker_requests(self) -> None:
        store = _Store()
        _seed(store, max_model_calls=1)
        inner = ScriptedModelPort()
        port = BudgetEnforcedModelPort(
            inner,
            FakeUnitOfWorkFactory(store=store),
            budget_id="budget-1",
            research_run_id="run-1",
            cycle_id="cycle-1",
            clock=FixedClock(),
        )
        port.complete(_request(ModelRole.GENERATOR))
        totals = ledger_totals(list(store.budget_consumptions.values()))
        self.assertEqual(totals.model_calls, 1)
        self.assertEqual(totals.worker_requests, 0)


if __name__ == "__main__":
    unittest.main()
