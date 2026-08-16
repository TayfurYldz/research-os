"""Unit-of-Work protocol. Core does not manage database transactions."""

from __future__ import annotations

from typing import Protocol

from research_os.data.ports import (
    AuditEventRepository,
    AuthorizationSourceRepository,
    ExecutionAttemptRepository,
    ExperimentPlanRepository,
    ExperimentRepository,
    HypothesisAssessmentRepository,
    HypothesisRepository,
    IssuedBudgetRepository,
    ObservationRepository,
    ProgramRepository,
    ResearchAdmissionRepository,
    ResearchReasoningRepository,
    ResearchRunRepository,
    WorkerResultRepository,
)


class UnitOfWork(Protocol):
    """One explicit transaction. Commit is required; otherwise rollback."""

    programs: ProgramRepository
    authorization_sources: AuthorizationSourceRepository
    research_runs: ResearchRunRepository
    issued_budgets: IssuedBudgetRepository
    hypotheses: HypothesisRepository
    experiments: ExperimentRepository
    execution_attempts: ExecutionAttemptRepository
    worker_results: WorkerResultRepository
    observations: ObservationRepository
    research_reasoning: ResearchReasoningRepository
    research_admissions: ResearchAdmissionRepository
    experiment_plans: ExperimentPlanRepository
    hypothesis_assessments: HypothesisAssessmentRepository
    audit_events: AuditEventRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, exc_type, exc, tb) -> bool: ...
