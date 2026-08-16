"""Internal persistence ports. Not language-neutral architectural contracts."""

from __future__ import annotations

from typing import Protocol

from research_os.data.records import (
    AuditEventRecord,
    AuthorizationSourceRecord,
    ExperimentRecord,
    HypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchRunRecord,
    WorkerResultRecord,
)


class ProgramRepository(Protocol):
    def insert(self, record: ProgramRecord) -> None: ...
    def get(self, program_id: str) -> ProgramRecord | None: ...


class AuthorizationSourceRepository(Protocol):
    def insert(self, record: AuthorizationSourceRecord) -> None: ...
    def get(self, authorization_source_id: str) -> AuthorizationSourceRecord | None: ...


class ResearchRunRepository(Protocol):
    def insert(self, record: ResearchRunRecord) -> None: ...
    def get(self, research_run_id: str) -> ResearchRunRecord | None: ...


class IssuedBudgetRepository(Protocol):
    def insert(self, record: IssuedBudgetRecord) -> None: ...
    def get(self, budget_id: str) -> IssuedBudgetRecord | None: ...


class HypothesisRepository(Protocol):
    def insert(self, record: HypothesisRecord) -> None: ...
    def get(self, hypothesis_id: str) -> HypothesisRecord | None: ...


class ExperimentRepository(Protocol):
    def insert(self, record: ExperimentRecord) -> None: ...
    def get(self, experiment_id: str) -> ExperimentRecord | None: ...
    def set_execution_state(
        self, experiment_id: str, execution_state: str
    ) -> None: ...


class WorkerResultRepository(Protocol):
    def insert(self, record: WorkerResultRecord) -> None: ...
    def get(self, worker_result_id: str) -> WorkerResultRecord | None: ...


class ObservationRepository(Protocol):
    def insert(self, record: ObservationRecord) -> None: ...
    def get(self, observation_id: str) -> ObservationRecord | None: ...


class AuditEventRepository(Protocol):
    def insert(self, record: AuditEventRecord) -> None: ...
    def get(self, audit_event_id: str) -> AuditEventRecord | None: ...
