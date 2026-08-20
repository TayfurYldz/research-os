"""Application use case for operator control of one autonomous run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from research_os.application.autonomous_research_controller import (
    AutonomousResearchController,
    OrchestrationTickResult,
    StartAutonomousResearchCommand,
)
from research_os.application.local_run_supervisor import LocalRunSupervisorRegistry


@dataclass
class ResearchRunControl:
    """Coordinates controller lifecycle and the local supervisor only."""

    controller: AutonomousResearchController
    supervisors: LocalRunSupervisorRegistry
    uow_factory: object
    cadence_seconds: float = 0.25
    prepare_start: Callable[[str], None] | None = None

    def start(self, command: StartAutonomousResearchCommand) -> OrchestrationTickResult:
        if self.prepare_start is not None:
            self.prepare_start(command.research_run_id)
        result = self.controller.start(command)
        if result.state == "READY":
            self.supervisors.start(
                research_run_id=command.research_run_id,
                controller=self.controller,
                command=command,
                uow_factory=self.uow_factory,
                cadence_seconds=self.cadence_seconds,
            )
        return result

    def pause(self, research_run_id: str) -> OrchestrationTickResult:
        return self.controller.pause(research_run_id)

    def resume(
        self,
        command: StartAutonomousResearchCommand,
    ) -> OrchestrationTickResult:
        result = self.controller.resume(command.research_run_id)
        if result.state == "READY":
            self.supervisors.start(
                research_run_id=command.research_run_id,
                controller=self.controller,
                command=command,
                uow_factory=self.uow_factory,
                cadence_seconds=self.cadence_seconds,
            )
        return result

    def cancel(self, research_run_id: str) -> OrchestrationTickResult:
        result = self.controller.cancel(research_run_id)
        self.supervisors.stop(research_run_id)
        return result
