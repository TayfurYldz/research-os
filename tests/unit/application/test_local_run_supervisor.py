from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.autonomous_research_controller import (
    AutonomousResearchController,
    StartAutonomousResearchCommand,
)
from research_os.application.local_run_supervisor import (
    LocalRunSupervisor,
    LocalRunSupervisorRegistry,
)
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


def _seed() -> _Store:
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


class LocalRunSupervisorTests(unittest.TestCase):
    def _supervisor(self, store: _Store) -> LocalRunSupervisor:
        factory = FakeUnitOfWorkFactory(store=store)
        controller = AutonomousResearchController(
            factory,
            RecordingWorkerPort(store=store),
            ScriptedModelPort(),
            clock=FixedClock(),
        )
        controller.start(_command())
        return LocalRunSupervisor("run-1", controller, _command(), factory)

    def test_tick_delegates_one_step_and_stops_on_terminal_state(self) -> None:
        store = _seed()
        supervisor = self._supervisor(store)

        result = supervisor.tick()

        self.assertIsNotNone(result)
        self.assertEqual(result.state, OrchestrationState.COMPLETED.value)

    def test_non_runnable_state_does_not_step(self) -> None:
        store = _seed()
        supervisor = self._supervisor(store)
        supervisor.controller.pause("run-1")

        result = supervisor.tick()

        self.assertEqual(result.state, OrchestrationState.PAUSED.value)
        self.assertEqual(len(store.experiments), 0)

    def test_registry_deduplicates_running_supervisor(self) -> None:
        store = _seed()
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

        first = registry.start(
            research_run_id="run-1",
            controller=controller,
            command=_command(),
            uow_factory=factory,
            cadence_seconds=10,
        )
        second = registry.start(
            research_run_id="run-1",
            controller=controller,
            command=_command(),
            uow_factory=factory,
            cadence_seconds=10,
        )
        first.request_stop()
        first.join(1)

        self.assertIs(first, second)


if __name__ == "__main__":
    unittest.main()
