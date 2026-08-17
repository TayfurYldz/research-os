"""Unit-of-Work protocol. Core does not manage database transactions."""

from __future__ import annotations

from typing import Protocol

from research_os.data.ports import (
    ApprovalRepository,
    AuditEventRepository,
    AuthorizationSourceRepository,
    BudgetConsumptionRepository,
    CandidateAdmissionRepository,
    CandidateRepository,
    ChainHypothesisRepository,
    DifferentialObservationRepository,
    EvidenceAdmissionRepository,
    EvidenceRepository,
    ExecutionAttemptRepository,
    ExperimentPlanRepository,
    ExperimentRepository,
    FindingProposalRepository,
    FindingRepository,
    HypothesisAssessmentRepository,
    HypothesisRepository,
    HumanReviewRepository,
    InvariantHypothesisRepository,
    IssuedBudgetRepository,
    ObservationRepository,
    ProgramRepository,
    ResearchAdmissionRepository,
    ResearchCycleRepository,
    ResearchOrchestrationRepository,
    ResearchReasoningRepository,
    ResearchRunRepository,
    TargetInferenceRepository,
    VerificationRepository,
    WorkerResultRepository,
    ResearchOpportunityRepository,
    ResearchSelectionRepository,
    SnapshotRepository,
    ChangeEventRepository,
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
    evidence: EvidenceRepository
    evidence_admissions: EvidenceAdmissionRepository
    candidates: CandidateRepository
    candidate_admissions: CandidateAdmissionRepository
    verifications: VerificationRepository
    finding_proposals: FindingProposalRepository
    human_reviews: HumanReviewRepository
    approvals: ApprovalRepository
    findings: FindingRepository
    target_inferences: TargetInferenceRepository
    differential_observations: DifferentialObservationRepository
    invariant_hypotheses: InvariantHypothesisRepository
    chain_hypotheses: ChainHypothesisRepository
    research_opportunities: ResearchOpportunityRepository
    research_selections: ResearchSelectionRepository
    snapshots: SnapshotRepository
    change_events: ChangeEventRepository
    research_orchestrations: ResearchOrchestrationRepository
    research_cycles: ResearchCycleRepository
    budget_consumptions: BudgetConsumptionRepository
    audit_events: AuditEventRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def __enter__(self) -> UnitOfWork: ...
    def __exit__(self, exc_type, exc, tb) -> bool: ...
