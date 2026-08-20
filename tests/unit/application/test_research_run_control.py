from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.autonomous_research_controller import (
    AutonomousResearchController,
    StartAutonomousResearchCommand,
)
from research_os.application.local_run_supervisor import LocalRunSupervisorRegistry
from research_os.application.research_run_control import ResearchRunControl
from research_os.core.enums import ScopeRuleEffect
from research_os.core.scope import ScopeEvaluationInput, ScopeRuleMatch
from research_os.research.orchestration import OrchestrationBounds, OrchestrationState
from support.fake_model import ScriptedModelPort
from support.fake_unit_of_work import FakeUnitOfWorkFactory, _Store
from support.recording_worker import RecordingWorkerPort
from support.spine import CREATED_AT, seed_authorization_run
from research_os.data.records import IssuedBudgetRecord


class FixedClock:
    def now(self):
        return CREATED_AT


def _command() -> StartAutonomousResearchCommand:
    return StartAutonomousResearchCommand(
        research_run_id="run-1",
        budget_id="budget-1",
        target_reference="target-1",
        scope=ScopeEvaluationInput(
            matches=(ScopeRuleMatch("rule-allow", ScopeRuleEffect.ALLOW, True, "src"),),
            ambiguous=False,
        ),
        bounds=OrchestrationBounds(
            max_cycles=1,
            max_experiments=1,
            max_model_calls=2,
            max_worker_invocations=2,
            max_elapsed_ms=1000,
            max_selected_opportunities=1,
            max_runtime_fallback=0,
            side_effect_ceiling=0,
        ),
    )


def _store() -> _Store:
    store = _Store()
    seed_authorization_run(store)
    store.issued_budgets["budget-1"] = IssuedBudgetRecord(
        budget_id="budget-1",
        research_run_id="run-1",
        max_requests=10,
        max_tool_calls=10,
        max_runtime_ms=1000,
        max_concurrency=1,
        issued_at=CREATED_AT,
    )
    return store


class ResearchRunControlTests(unittest.TestCase):
    def test_start_start_is_idempotent_and_supervisor_is_shared(self) -> None:
        store = _store()
        factory = FakeUnitOfWorkFactory(store=store)
        controller = AutonomousResearchController(
            factory,
            RecordingWorkerPort(store=store),
            ScriptedModelPort(),
            clock=FixedClock(),
        )
        controller.start(_command())
        controller.pause("run-1")
        registry = LocalRunSupervisorRegistry()
        control = ResearchRunControl(controller, registry, factory, cadence_seconds=10)

        first = control.start(_command())
        second = control.start(_command())
        control.cancel("run-1")

        self.assertEqual(first.state, OrchestrationState.PAUSED.value)
        self.assertEqual(second.state, OrchestrationState.PAUSED.value)
        self.assertEqual(len(store.research_orchestrations), 1)

    def test_pause_and_cancel_delegate_to_controller(self) -> None:
        store = _store()
        factory = FakeUnitOfWorkFactory(store=store)
        controller = AutonomousResearchController(
            factory,
            RecordingWorkerPort(store=store),
            ScriptedModelPort(),
            clock=FixedClock(),
        )
        control = ResearchRunControl(controller, LocalRunSupervisorRegistry(), factory)
        control.start(_command())
        paused = control.pause("run-1")
        cancelled = control.cancel("run-1")

        self.assertEqual(paused.state, OrchestrationState.PAUSED.value)
        self.assertEqual(cancelled.state, OrchestrationState.COMPLETED.value)


if __name__ == "__main__":
    unittest.main()
