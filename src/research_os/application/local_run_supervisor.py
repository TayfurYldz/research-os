"""Small local runner around the existing AutonomousResearchController.

The supervisor owns no research policy. It only schedules bounded controller
ticks and treats the persisted orchestration record as authoritative.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from research_os.application.autonomous_research_controller import (
    AutonomousResearchController,
    OrchestrationTickResult,
    StartAutonomousResearchCommand,
)
from research_os.application.errors import ApplicationError
from research_os.application.ports import UnitOfWorkFactory
from research_os.research.orchestration import (
    CycleOutcome,
    OrchestrationState,
)

_NON_RUNNABLE_STATES = frozenset(
    {
        OrchestrationState.PAUSED.value,
        OrchestrationState.WAITING_HUMAN.value,
        OrchestrationState.BLOCKED.value,
        OrchestrationState.BUDGET_EXHAUSTED.value,
        OrchestrationState.FAILED_OPERATIONAL.value,
    }
)
_TERMINAL_STATES = frozenset(
    {
        OrchestrationState.COMPLETED.value,
        OrchestrationState.BUDGET_EXHAUSTED.value,
        OrchestrationState.FAILED_OPERATIONAL.value,
    }
)


def _result_from_persisted(record) -> OrchestrationTickResult:
    return OrchestrationTickResult(
        research_run_id=record.research_run_id,
        state=record.state,
        cycle_number=record.cycle_number,
        outcome=CycleOutcome.CONTINUE.value,
        stop_reason=record.stop_reason,
        last_phase=record.last_phase,
        hypothesis_id=record.last_hypothesis_id,
        experiment_id=record.last_experiment_id,
    )


@dataclass
class LocalRunSupervisor:
    """One bounded cadence loop for one already-started ResearchRun."""

    research_run_id: str
    controller: AutonomousResearchController
    command: StartAutonomousResearchCommand
    uow_factory: UnitOfWorkFactory
    cadence_seconds: float = 0.25

    def __post_init__(self) -> None:
        if self.cadence_seconds <= 0:
            raise ValueError("cadence_seconds must be positive")
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_result: OrchestrationTickResult | None = None

    def tick(self) -> OrchestrationTickResult | None:
        """Run at most one controller step after reloading durable state."""

        with self.uow_factory.open() as uow:
            record = uow.research_orchestrations.get(self.research_run_id)
            uow.rollback()
        if record is None:
            raise ApplicationError("orchestration not found")
        if record.state in _NON_RUNNABLE_STATES:
            result = _result_from_persisted(record)
        elif record.state in {
            OrchestrationState.READY.value,
            OrchestrationState.RUNNING.value,
        }:
            result = self.controller.step(self.command)
        else:
            result = _result_from_persisted(record)
        self._last_result = result
        if result.state in _TERMINAL_STATES:
            self._stop_event.set()
        return result

    def start(self) -> "LocalRunSupervisor":
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run,
                name=f"research-run-{self.research_run_id}",
                daemon=True,
            )
            self._thread.start()
        return self

    def request_stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    @property
    def last_result(self) -> OrchestrationTickResult | None:
        return self._last_result

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            if not self._stop_event.wait(self.cadence_seconds):
                continue


class LocalRunSupervisorRegistry:
    """Process-local duplicate-start guard for local supervisors."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._supervisors: dict[str, LocalRunSupervisor] = {}

    def start(
        self,
        *,
        research_run_id: str,
        controller: AutonomousResearchController,
        command: StartAutonomousResearchCommand,
        uow_factory: UnitOfWorkFactory,
        cadence_seconds: float = 0.25,
    ) -> LocalRunSupervisor:
        with self._lock:
            existing = self._supervisors.get(research_run_id)
            if existing is not None and existing.is_running:
                return existing
            supervisor = LocalRunSupervisor(
                research_run_id,
                controller,
                command,
                uow_factory,
                cadence_seconds,
            )
            self._supervisors[research_run_id] = supervisor
            supervisor.start()
            return supervisor

    def stop(self, research_run_id: str) -> None:
        with self._lock:
            supervisor = self._supervisors.get(research_run_id)
        if supervisor is not None:
            supervisor.request_stop()
