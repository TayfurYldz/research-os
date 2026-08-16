"""In-memory Unit of Work for Application tests. Not a PostgreSQL substitute."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from research_os.data.errors import (
    PersistenceConflictError,
    PersistenceError,
    PersistenceInputError,
)
from research_os.data.records import (
    ALLOWED_CANDIDATE_STATES,
    ALLOWED_EXECUTION_ATTEMPT_STATES,
    ALLOWED_EXPERIMENT_STATES,
    ALLOWED_FINDING_PROPOSAL_STATES,
    ALLOWED_INVARIANT_STATUSES,
    ApprovalRecord,
    AuditEventRecord,
    AuthorizationSourceRecord,
    CandidateAdmissionRecord,
    CandidateRecord,
    ChainHypothesisRecord,
    DifferentialObservationRecord,
    EvidenceAdmissionRecord,
    EvidenceRecord,
    ExecutionAttemptRecord,
    ExperimentPlanRecord,
    ExperimentRecord,
    FindingProposalRecord,
    FindingRecord,
    HypothesisAssessmentRecord,
    HypothesisRecord,
    HumanReviewRecord,
    InvariantCounterexampleRefRecord,
    InvariantHypothesisRecord,
    IssuedBudgetRecord,
    ObservationRecord,
    ProgramRecord,
    ResearchAdmissionRecord,
    ResearchOpportunityRecord,
    ResearchReasoningRecord,
    ResearchRunRecord,
    ResearchSelectionRecord,
    SnapshotMemberRecord,
    SnapshotRecord,
    TargetInferenceRecord,
    ChangeEventRecord,
    ProgramRecord,
    ResearchAdmissionRecord,
    ResearchReasoningRecord,
    ResearchRunRecord,
    TargetInferenceRecord,
    VerificationRecord,
    WorkerResultRecord,
)


class _Store:
    def __init__(self) -> None:
        self.programs: dict[str, ProgramRecord] = {}
        self.authorization_sources: dict[str, AuthorizationSourceRecord] = {}
        self.research_runs: dict[str, ResearchRunRecord] = {}
        self.issued_budgets: dict[str, IssuedBudgetRecord] = {}
        self.hypotheses: dict[str, HypothesisRecord] = {}
        self.experiments: dict[str, ExperimentRecord] = {}
        self.execution_attempts: dict[str, ExecutionAttemptRecord] = {}
        self.execution_attempts_by_request: dict[str, str] = {}
        self.worker_results: dict[str, WorkerResultRecord] = {}
        self.worker_results_by_request: dict[str, str] = {}
        self.observations: dict[str, ObservationRecord] = {}
        self.research_reasoning: dict[str, ResearchReasoningRecord] = {}
        self.research_admissions: dict[str, ResearchAdmissionRecord] = {}
        self.experiment_plans: dict[str, ExperimentPlanRecord] = {}
        self.hypothesis_assessments: dict[str, HypothesisAssessmentRecord] = {}
        self.evidence: dict[str, EvidenceRecord] = {}
        self.evidence_admissions: dict[str, EvidenceAdmissionRecord] = {}
        self.candidates: dict[str, CandidateRecord] = {}
        self.candidate_admissions: dict[str, CandidateAdmissionRecord] = {}
        self.verifications: dict[str, VerificationRecord] = {}
        self.finding_proposals: dict[str, FindingProposalRecord] = {}
        self.human_reviews: dict[str, HumanReviewRecord] = {}
        self.approvals: dict[str, ApprovalRecord] = {}
        self.findings: dict[str, FindingRecord] = {}
        self.target_inferences: dict[str, TargetInferenceRecord] = {}
        self.differential_observations: dict[str, DifferentialObservationRecord] = {}
        self.invariant_hypotheses: dict[str, InvariantHypothesisRecord] = {}
        self.invariant_counterexamples: dict[str, InvariantCounterexampleRefRecord] = {}
        self.chain_hypotheses: dict[str, ChainHypothesisRecord] = {}
        self.research_opportunities: dict[str, ResearchOpportunityRecord] = {}
        self.research_selections: dict[str, ResearchSelectionRecord] = {}
        self.snapshots: dict[str, SnapshotRecord] = {}
        self.snapshot_members: dict[str, SnapshotMemberRecord] = {}
        self.change_events: dict[str, ChangeEventRecord] = {}
        self.audit_events: dict[str, AuditEventRecord] = {}
        self.open_transactions = 0
        self.set_state_calls = 0


class _Repo:
    def __init__(self, store: dict[str, Any], fail_on_insert: bool = False) -> None:
        self._store = store
        self._fail_on_insert = fail_on_insert

    def insert(self, record: Any) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        key = _id_of(record)
        if key in self._store:
            raise PersistenceConflictError("duplicate id")
        self._store[key] = record

    def get(self, record_id: str) -> Any | None:
        return self._store.get(record_id)


def _id_of(record: Any) -> str:
    if isinstance(record, ProgramRecord):
        return record.program_id
    if isinstance(record, AuthorizationSourceRecord):
        return record.authorization_source_id
    if isinstance(record, ResearchRunRecord):
        return record.research_run_id
    if isinstance(record, IssuedBudgetRecord):
        return record.budget_id
    if isinstance(record, HypothesisRecord):
        return record.hypothesis_id
    if isinstance(record, ExperimentRecord):
        return record.experiment_id
    if isinstance(record, ExecutionAttemptRecord):
        return record.attempt_id
    if isinstance(record, WorkerResultRecord):
        return record.worker_result_id
    if isinstance(record, ObservationRecord):
        return record.observation_id
    if isinstance(record, ResearchReasoningRecord):
        return record.reasoning_record_id
    if isinstance(record, ResearchAdmissionRecord):
        return record.admission_record_id
    if isinstance(record, ExperimentPlanRecord):
        return record.experiment_id
    if isinstance(record, HypothesisAssessmentRecord):
        return record.assessment_id
    if isinstance(record, EvidenceRecord):
        return record.evidence_id
    if isinstance(record, EvidenceAdmissionRecord):
        return record.admission_record_id
    if isinstance(record, CandidateRecord):
        return record.candidate_id
    if isinstance(record, CandidateAdmissionRecord):
        return record.admission_record_id
    if isinstance(record, VerificationRecord):
        return record.verification_id
    if isinstance(record, FindingProposalRecord):
        return record.proposal_id
    if isinstance(record, HumanReviewRecord):
        return record.review_id
    if isinstance(record, ApprovalRecord):
        return record.approval_id
    if isinstance(record, FindingRecord):
        return record.finding_id
    if isinstance(record, TargetInferenceRecord):
        return record.inference_id
    if isinstance(record, DifferentialObservationRecord):
        return record.differential_id
    if isinstance(record, InvariantHypothesisRecord):
        return record.invariant_id
    if isinstance(record, InvariantCounterexampleRefRecord):
        return record.counterexample_id
    if isinstance(record, ChainHypothesisRecord):
        return record.chain_id
    if isinstance(record, ResearchOpportunityRecord):
        return record.opportunity_id
    if isinstance(record, ResearchSelectionRecord):
        return record.selection_id
    if isinstance(record, SnapshotRecord):
        return record.snapshot_id
    if isinstance(record, SnapshotMemberRecord):
        return f"{record.snapshot_id}:{record.observation_id}"
    if isinstance(record, ChangeEventRecord):
        return record.change_event_id
    if isinstance(record, AuditEventRecord):
        return record.audit_event_id
    raise PersistenceError("unknown record identity")


class _HypothesisRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.hypotheses, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[HypothesisRecord]:
        return sorted(
            [
                record
                for record in self._root.hypotheses.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.hypothesis_id,
        )


class _ExperimentRepo(_Repo):
    def set_execution_state(self, experiment_id: str, execution_state: str) -> None:
        if execution_state not in ALLOWED_EXPERIMENT_STATES:
            raise PersistenceInputError("execution_state is not a domain execution state")
        current = self.get(experiment_id)
        if current is None:
            raise PersistenceError("experiment not found for execution_state update")
        self._store[experiment_id] = ExperimentRecord(
            experiment_id=current.experiment_id,
            research_run_id=current.research_run_id,
            hypothesis_id=current.hypothesis_id,
            budget_id=current.budget_id,
            execution_state=execution_state,
            created_at=current.created_at,
        )

    def list_for_research_run(self, research_run_id: str) -> list[ExperimentRecord]:
        return sorted(
            [
                record
                for record in self._store.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.experiment_id,
        )


class _ExecutionAttemptRepo(_Repo):
    def __init__(
        self,
        store: _Store,
        fail_on_insert: bool = False,
        fail_on_set_state: bool = False,
    ) -> None:
        super().__init__(store.execution_attempts, fail_on_insert=fail_on_insert)
        self._root = store
        self._fail_on_set_state = fail_on_set_state

    def insert(self, record: ExecutionAttemptRecord) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        if record.request_id in self._root.execution_attempts_by_request:
            raise PersistenceConflictError("duplicate request_id")
        super().insert(record)
        self._root.execution_attempts_by_request[record.request_id] = record.attempt_id

    def get_by_request_id(self, request_id: str) -> ExecutionAttemptRecord | None:
        attempt_id = self._root.execution_attempts_by_request.get(request_id)
        if attempt_id is None:
            return None
        return self._root.execution_attempts.get(attempt_id)

    def list_for_experiment(self, experiment_id: str) -> list[ExecutionAttemptRecord]:
        return [
            record
            for record in self._root.execution_attempts.values()
            if record.experiment_id == experiment_id
        ]

    def set_state(
        self,
        attempt_id: str,
        state: str,
        *,
        dispatch_started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        if self._fail_on_set_state:
            self._root.set_state_calls += 1
            if self._root.set_state_calls >= 2:
                raise PersistenceError("injected persistence failure")
        if state not in ALLOWED_EXECUTION_ATTEMPT_STATES:
            raise PersistenceInputError("state is not an ExecutionAttempt state")
        current = self.get(attempt_id)
        if current is None:
            raise PersistenceError("execution_attempt not found for state update")
        self._store[attempt_id] = ExecutionAttemptRecord(
            attempt_id=current.attempt_id,
            request_id=current.request_id,
            experiment_id=current.experiment_id,
            research_run_id=current.research_run_id,
            correlation_id=current.correlation_id,
            worker_capability=current.worker_capability,
            action=current.action,
            target_reference=current.target_reference,
            budget_id=current.budget_id,
            side_effect_level=current.side_effect_level,
            authorization_decision_reference=current.authorization_decision_reference,
            state=state,
            created_at=current.created_at,
            authorized_at=current.authorized_at,
            dispatch_started_at=(
                dispatch_started_at
                if dispatch_started_at is not None
                else current.dispatch_started_at
            ),
            completed_at=completed_at if completed_at is not None else current.completed_at,
        )


class _WorkerResultRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.worker_results, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: WorkerResultRecord) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        if record.request_id in self._root.worker_results_by_request:
            raise PersistenceConflictError("duplicate request_id")
        super().insert(record)
        self._root.worker_results_by_request[record.request_id] = record.worker_result_id

    def get_by_request_id(self, request_id: str) -> WorkerResultRecord | None:
        worker_result_id = self._root.worker_results_by_request.get(request_id)
        if worker_result_id is None:
            return None
        return self._root.worker_results.get(worker_result_id)

    def list_for_research_run(self, research_run_id: str) -> list[WorkerResultRecord]:
        return sorted(
            [
                record
                for record in self._root.worker_results.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.worker_result_id,
        )

    def list_for_experiment(self, experiment_id: str) -> list[WorkerResultRecord]:
        return sorted(
            [
                record
                for record in self._root.worker_results.values()
                if record.experiment_id == experiment_id
            ],
            key=lambda record: record.worker_result_id,
        )


class _ObservationRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.observations, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_worker_result(self, worker_result_id: str) -> list[ObservationRecord]:
        return [
            record
            for record in self._root.observations.values()
            if record.worker_result_id == worker_result_id
        ]

    def list_for_research_run(self, research_run_id: str) -> list[ObservationRecord]:
        result_ids = {
            record.worker_result_id
            for record in self._root.worker_results.values()
            if record.research_run_id == research_run_id
        }
        return sorted(
            [
                record
                for record in self._root.observations.values()
                if record.worker_result_id in result_ids
            ],
            key=lambda record: record.observation_id,
        )

    def list_for_experiment(self, experiment_id: str) -> list[ObservationRecord]:
        result_ids = {
            record.worker_result_id
            for record in self._root.worker_results.values()
            if record.experiment_id == experiment_id
        }
        return sorted(
            [
                record
                for record in self._root.observations.values()
                if record.worker_result_id in result_ids
            ],
            key=lambda record: record.observation_id,
        )


class _ResearchReasoningRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.research_reasoning, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[ResearchReasoningRecord]:
        return sorted(
            [
                record
                for record in self._root.research_reasoning.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.reasoning_record_id,
        )

    def list_for_hypothesis(self, hypothesis_id: str) -> list[ResearchReasoningRecord]:
        return sorted(
            [
                record
                for record in self._root.research_reasoning.values()
                if record.hypothesis_id == hypothesis_id
            ],
            key=lambda record: record.reasoning_record_id,
        )


class _ResearchAdmissionRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.research_admissions, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[ResearchAdmissionRecord]:
        return sorted(
            [
                record
                for record in self._root.research_admissions.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.admission_record_id,
        )


class _HypothesisAssessmentRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.hypothesis_assessments, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_experiment(
        self, experiment_id: str
    ) -> list[HypothesisAssessmentRecord]:
        return sorted(
            [
                record
                for record in self._root.hypothesis_assessments.values()
                if record.experiment_id == experiment_id
            ],
            key=lambda record: record.assessment_id,
        )

    def list_for_hypothesis(
        self, hypothesis_id: str
    ) -> list[HypothesisAssessmentRecord]:
        return sorted(
            [
                record
                for record in self._root.hypothesis_assessments.values()
                if record.hypothesis_id == hypothesis_id
            ],
            key=lambda record: record.assessment_id,
        )

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[HypothesisAssessmentRecord]:
        return sorted(
            [
                record
                for record in self._root.hypothesis_assessments.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.assessment_id,
        )


class _EvidenceRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.evidence, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[EvidenceRecord]:
        return sorted(
            [
                record
                for record in self._root.evidence.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.evidence_id,
        )

    def list_for_hypothesis(self, hypothesis_id: str) -> list[EvidenceRecord]:
        return sorted(
            [
                record
                for record in self._root.evidence.values()
                if record.hypothesis_id == hypothesis_id
            ],
            key=lambda record: record.evidence_id,
        )

    def list_for_experiment(self, experiment_id: str) -> list[EvidenceRecord]:
        return sorted(
            [
                record
                for record in self._root.evidence.values()
                if record.experiment_id == experiment_id
            ],
            key=lambda record: record.evidence_id,
        )


class _EvidenceAdmissionRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.evidence_admissions, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[EvidenceAdmissionRecord]:
        return sorted(
            [
                record
                for record in self._root.evidence_admissions.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.admission_record_id,
        )


class _CandidateRepo(_Repo):
    def __init__(
        self,
        store: _Store,
        fail_on_insert: bool = False,
        fail_on_set_state: bool = False,
    ) -> None:
        super().__init__(store.candidates, fail_on_insert=fail_on_insert)
        self._root = store
        self._fail_on_set_state = fail_on_set_state

    def list_for_research_run(self, research_run_id: str) -> list[CandidateRecord]:
        return sorted(
            [
                record
                for record in self._root.candidates.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.candidate_id,
        )

    def set_state(self, candidate_id: str, state: str) -> None:
        if self._fail_on_set_state:
            raise PersistenceError("injected persistence failure")
        if state not in ALLOWED_CANDIDATE_STATES:
            raise PersistenceInputError("state is not a Candidate lifecycle state")
        current = self.get(candidate_id)
        if current is None:
            raise PersistenceError("candidate not found for state update")
        self._store[candidate_id] = CandidateRecord(
            candidate_id=current.candidate_id,
            research_run_id=current.research_run_id,
            hypothesis_id=current.hypothesis_id,
            claim=current.claim,
            classification=current.classification,
            state=state,
            evidence_ids=current.evidence_ids,
            created_at=current.created_at,
            admission_record_id=current.admission_record_id,
        )


class _CandidateAdmissionRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.candidate_admissions, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[CandidateAdmissionRecord]:
        return sorted(
            [
                record
                for record in self._root.candidate_admissions.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.admission_record_id,
        )


class _VerificationRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.verifications, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_candidate(self, candidate_id: str) -> list[VerificationRecord]:
        return sorted(
            [
                record
                for record in self._root.verifications.values()
                if record.candidate_id == candidate_id
            ],
            key=lambda record: record.verification_id,
        )

    def list_for_research_run(self, research_run_id: str) -> list[VerificationRecord]:
        return sorted(
            [
                record
                for record in self._root.verifications.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.verification_id,
        )


class _FindingProposalRepo(_Repo):
    def __init__(
        self,
        store: _Store,
        fail_on_insert: bool = False,
        fail_on_set_state: bool = False,
    ) -> None:
        super().__init__(store.finding_proposals, fail_on_insert=fail_on_insert)
        self._root = store
        self._fail_on_set_state = fail_on_set_state

    def list_for_candidate(self, candidate_id: str) -> list[FindingProposalRecord]:
        return sorted(
            [
                record
                for record in self._root.finding_proposals.values()
                if record.candidate_id == candidate_id
            ],
            key=lambda record: record.proposal_id,
        )

    def list_for_research_run(self, research_run_id: str) -> list[FindingProposalRecord]:
        return sorted(
            [
                record
                for record in self._root.finding_proposals.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.proposal_id,
        )

    def set_state(self, proposal_id: str, state: str) -> None:
        if self._fail_on_set_state:
            raise PersistenceError("injected persistence failure")
        if state not in ALLOWED_FINDING_PROPOSAL_STATES:
            raise PersistenceInputError("state is not a FindingProposal lifecycle state")
        current = self.get(proposal_id)
        if current is None:
            raise PersistenceError("finding_proposal not found for state update")
        self._store[proposal_id] = FindingProposalRecord(
            proposal_id=current.proposal_id,
            candidate_id=current.candidate_id,
            research_run_id=current.research_run_id,
            title=current.title,
            claim=current.claim,
            classification=current.classification,
            state=state,
            evidence_ids=current.evidence_ids,
            verification_ids=current.verification_ids,
            content_fingerprint=current.content_fingerprint,
            created_at=current.created_at,
        )


class _HumanReviewRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.human_reviews, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: HumanReviewRecord) -> None:
        for existing in self._root.human_reviews.values():
            if (
                existing.proposal_id == record.proposal_id
                and existing.content_fingerprint == record.content_fingerprint
            ):
                raise PersistenceConflictError("duplicate human review")
        super().insert(record)

    def get_for_proposal(self, proposal_id: str) -> HumanReviewRecord | None:
        matches = [
            record
            for record in self._root.human_reviews.values()
            if record.proposal_id == proposal_id
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda record: record.review_id)[0]


class _ApprovalRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.approvals, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: ApprovalRecord) -> None:
        for existing in self._root.approvals.values():
            if existing.subject_reference == record.subject_reference:
                raise PersistenceConflictError("duplicate approval subject")
        super().insert(record)

    def get_by_subject(self, subject_reference: str) -> ApprovalRecord | None:
        for record in self._root.approvals.values():
            if record.subject_reference == subject_reference:
                return record
        return None


class _FindingRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.findings, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: FindingRecord) -> None:
        for existing in self._root.findings.values():
            if existing.finding_proposal_id == record.finding_proposal_id:
                raise PersistenceConflictError("duplicate finding for proposal")
        super().insert(record)

    def get_by_proposal(self, finding_proposal_id: str) -> FindingRecord | None:
        for record in self._root.findings.values():
            if record.finding_proposal_id == finding_proposal_id:
                return record
        return None

    def list_for_research_run(self, research_run_id: str) -> list[FindingRecord]:
        return sorted(
            [
                record
                for record in self._root.findings.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.finding_id,
        )


class _TargetInferenceRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.target_inferences, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[TargetInferenceRecord]:
        return sorted(
            [
                record
                for record in self._root.target_inferences.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.inference_id,
        )


class _DifferentialObservationRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.differential_observations, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(
        self, research_run_id: str
    ) -> list[DifferentialObservationRecord]:
        return sorted(
            [
                record
                for record in self._root.differential_observations.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.differential_id,
        )


class _InvariantHypothesisRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.invariant_hypotheses, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[InvariantHypothesisRecord]:
        return sorted(
            [
                record
                for record in self._root.invariant_hypotheses.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.invariant_id,
        )

    def set_state(self, invariant_id: str, state: str) -> None:
        if state not in ALLOWED_INVARIANT_STATUSES:
            raise PersistenceInputError("status is not an invariant hypothesis status")
        current = self.get(invariant_id)
        if current is None:
            raise PersistenceError("invariant hypothesis not found for state update")
        self._store[invariant_id] = InvariantHypothesisRecord(
            invariant_id=current.invariant_id,
            research_run_id=current.research_run_id,
            invariant_kind=current.invariant_kind,
            status=state,
            subject_refs=current.subject_refs,
            expected_behavior=current.expected_behavior,
            source_refs=current.source_refs,
            applicability_context=current.applicability_context,
            assumptions=current.assumptions,
            counterexample_refs=current.counterexample_refs,
            falsification_direction=current.falsification_direction,
            proposer_provenance=current.proposer_provenance,
            strategy_version=current.strategy_version,
            created_at=current.created_at,
        )

    def add_counterexample(self, record: InvariantCounterexampleRefRecord) -> None:
        current = self.get(record.invariant_id)
        if current is None:
            raise PersistenceError("invariant hypothesis not found for counterexample")
        if record.counterexample_id in self._root.invariant_counterexamples:
            raise PersistenceConflictError("duplicate id")
        self._root.invariant_counterexamples[record.counterexample_id] = record
        refs = current.counterexample_refs
        if record.source_ref not in refs:
            refs = refs + (record.source_ref,)
        self._store[record.invariant_id] = InvariantHypothesisRecord(
            invariant_id=current.invariant_id,
            research_run_id=current.research_run_id,
            invariant_kind=current.invariant_kind,
            status="CHALLENGED",
            subject_refs=current.subject_refs,
            expected_behavior=current.expected_behavior,
            source_refs=current.source_refs,
            applicability_context=current.applicability_context,
            assumptions=current.assumptions,
            counterexample_refs=refs,
            falsification_direction=current.falsification_direction,
            proposer_provenance=current.proposer_provenance,
            strategy_version=current.strategy_version,
            created_at=current.created_at,
        )


class _ChainHypothesisRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.chain_hypotheses, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: ChainHypothesisRecord) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        for existing in self._root.chain_hypotheses.values():
            if (
                existing.research_run_id == record.research_run_id
                and existing.structural_identity == record.structural_identity
            ):
                raise PersistenceConflictError("duplicate chain structural identity")
        super().insert(record)

    def list_for_research_run(self, research_run_id: str) -> list[ChainHypothesisRecord]:
        return sorted(
            [
                record
                for record in self._root.chain_hypotheses.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.chain_id,
        )


class _ResearchOpportunityRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.research_opportunities, fail_on_insert=fail_on_insert)
        self._root = store

    def insert(self, record: ResearchOpportunityRecord) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        for existing in self._root.research_opportunities.values():
            if (
                existing.research_run_id == record.research_run_id
                and existing.structural_identity == record.structural_identity
            ):
                raise PersistenceConflictError("duplicate opportunity structural identity")
        super().insert(record)

    def list_for_research_run(self, research_run_id: str) -> list[ResearchOpportunityRecord]:
        return sorted(
            [
                record
                for record in self._root.research_opportunities.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.opportunity_id,
        )


class _ResearchSelectionRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.research_selections, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[ResearchSelectionRecord]:
        return sorted(
            [
                record
                for record in self._root.research_selections.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.selection_id,
        )


class _SnapshotRepo:
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        self._root = store
        self._fail_on_insert = fail_on_insert

    def insert(self, record: SnapshotRecord, members: tuple[SnapshotMemberRecord, ...]) -> None:
        if self._fail_on_insert:
            raise PersistenceError("injected persistence failure")
        if record.snapshot_id in self._root.snapshots:
            raise PersistenceConflictError("duplicate id")
        self._root.snapshots[record.snapshot_id] = record
        for member in members:
            self._root.snapshot_members[f"{member.snapshot_id}:{member.observation_id}"] = member

    def get(self, snapshot_id: str) -> SnapshotRecord | None:
        return self._root.snapshots.get(snapshot_id)

    def list_members(self, snapshot_id: str) -> list[SnapshotMemberRecord]:
        return sorted(
            [
                record
                for record in self._root.snapshot_members.values()
                if record.snapshot_id == snapshot_id
            ],
            key=lambda record: record.observation_id,
        )

    def list_for_research_run(self, research_run_id: str) -> list[SnapshotRecord]:
        return sorted(
            [
                record
                for record in self._root.snapshots.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.snapshot_id,
        )


class _ChangeEventRepo(_Repo):
    def __init__(self, store: _Store, fail_on_insert: bool = False) -> None:
        super().__init__(store.change_events, fail_on_insert=fail_on_insert)
        self._root = store

    def list_for_research_run(self, research_run_id: str) -> list[ChangeEventRecord]:
        return sorted(
            [
                record
                for record in self._root.change_events.values()
                if record.research_run_id == research_run_id
            ],
            key=lambda record: record.change_event_id,
        )


class FakeUnitOfWork:
    def __init__(self, store: _Store | None = None, fail_on: str | None = None) -> None:
        self._store = store or _Store()
        self._fail_on = fail_on
        self._committed = False
        self._snapshot: _Store | None = None
        self.programs = _Repo(self._store.programs)
        self.authorization_sources = _Repo(self._store.authorization_sources)
        self.research_runs = _Repo(self._store.research_runs)
        self.issued_budgets = _Repo(self._store.issued_budgets)
        self.hypotheses = _HypothesisRepo(
            self._store, fail_on_insert=fail_on == "hypotheses"
        )
        self.experiments = _ExperimentRepo(self._store.experiments)
        self.execution_attempts = _ExecutionAttemptRepo(
            self._store,
            fail_on_insert=fail_on == "execution_attempts",
            fail_on_set_state=fail_on == "attempt_outcome",
        )
        self.worker_results = _WorkerResultRepo(
            self._store, fail_on_insert=fail_on == "worker_results"
        )
        self.observations = _ObservationRepo(
            self._store, fail_on_insert=fail_on == "observations"
        )
        self.research_reasoning = _ResearchReasoningRepo(
            self._store, fail_on_insert=fail_on == "research_reasoning"
        )
        self.research_admissions = _ResearchAdmissionRepo(
            self._store, fail_on_insert=fail_on == "research_admissions"
        )
        self.experiment_plans = _Repo(
            self._store.experiment_plans, fail_on_insert=fail_on == "experiment_plans"
        )
        self.hypothesis_assessments = _HypothesisAssessmentRepo(
            self._store, fail_on_insert=fail_on == "hypothesis_assessments"
        )
        self.evidence = _EvidenceRepo(self._store, fail_on_insert=fail_on == "evidence")
        self.evidence_admissions = _EvidenceAdmissionRepo(
            self._store, fail_on_insert=fail_on == "evidence_admissions"
        )
        self.candidates = _CandidateRepo(
            self._store,
            fail_on_insert=fail_on == "candidates",
            fail_on_set_state=fail_on == "candidate_state",
        )
        self.candidate_admissions = _CandidateAdmissionRepo(
            self._store, fail_on_insert=fail_on == "candidate_admissions"
        )
        self.verifications = _VerificationRepo(
            self._store, fail_on_insert=fail_on == "verifications"
        )
        self.finding_proposals = _FindingProposalRepo(
            self._store,
            fail_on_insert=fail_on == "finding_proposals",
            fail_on_set_state=fail_on == "finding_proposal_state",
        )
        self.human_reviews = _HumanReviewRepo(
            self._store, fail_on_insert=fail_on == "human_reviews"
        )
        self.approvals = _ApprovalRepo(
            self._store, fail_on_insert=fail_on == "approvals"
        )
        self.findings = _FindingRepo(self._store, fail_on_insert=fail_on == "findings")
        self.target_inferences = _TargetInferenceRepo(
            self._store, fail_on_insert=fail_on == "target_inferences"
        )
        self.differential_observations = _DifferentialObservationRepo(
            self._store, fail_on_insert=fail_on == "differential_observations"
        )
        self.invariant_hypotheses = _InvariantHypothesisRepo(
            self._store, fail_on_insert=fail_on == "invariant_hypotheses"
        )
        self.chain_hypotheses = _ChainHypothesisRepo(
            self._store, fail_on_insert=fail_on == "chain_hypotheses"
        )
        self.research_opportunities = _ResearchOpportunityRepo(
            self._store, fail_on_insert=fail_on == "research_opportunities"
        )
        self.research_selections = _ResearchSelectionRepo(
            self._store, fail_on_insert=fail_on == "research_selections"
        )
        self.snapshots = _SnapshotRepo(
            self._store, fail_on_insert=fail_on == "snapshots"
        )
        self.change_events = _ChangeEventRepo(
            self._store, fail_on_insert=fail_on == "change_events"
        )
        self.audit_events = _Repo(
            self._store.audit_events, fail_on_insert=fail_on == "audit_events"
        )

    def __enter__(self) -> FakeUnitOfWork:
        self._store.open_transactions += 1
        self._snapshot = deepcopy(self._store)
        self._committed = False
        return self

    def commit(self) -> None:
        self._committed = True
        self._snapshot = None

    def rollback(self) -> None:
        if self._snapshot is not None:
            self._restore(self._snapshot)
        self._committed = False

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc_type is not None or not self._committed:
                self.rollback()
        finally:
            self._store.open_transactions = max(0, self._store.open_transactions - 1)
        return False

    def _restore(self, snapshot: _Store) -> None:
        self._store.programs.clear()
        self._store.programs.update(snapshot.programs)
        self._store.authorization_sources.clear()
        self._store.authorization_sources.update(snapshot.authorization_sources)
        self._store.research_runs.clear()
        self._store.research_runs.update(snapshot.research_runs)
        self._store.issued_budgets.clear()
        self._store.issued_budgets.update(snapshot.issued_budgets)
        self._store.hypotheses.clear()
        self._store.hypotheses.update(snapshot.hypotheses)
        self._store.experiments.clear()
        self._store.experiments.update(snapshot.experiments)
        self._store.execution_attempts.clear()
        self._store.execution_attempts.update(snapshot.execution_attempts)
        self._store.execution_attempts_by_request.clear()
        self._store.execution_attempts_by_request.update(
            snapshot.execution_attempts_by_request
        )
        self._store.worker_results.clear()
        self._store.worker_results.update(snapshot.worker_results)
        self._store.worker_results_by_request.clear()
        self._store.worker_results_by_request.update(snapshot.worker_results_by_request)
        self._store.observations.clear()
        self._store.observations.update(snapshot.observations)
        self._store.research_reasoning.clear()
        self._store.research_reasoning.update(snapshot.research_reasoning)
        self._store.research_admissions.clear()
        self._store.research_admissions.update(snapshot.research_admissions)
        self._store.experiment_plans.clear()
        self._store.experiment_plans.update(snapshot.experiment_plans)
        self._store.hypothesis_assessments.clear()
        self._store.hypothesis_assessments.update(snapshot.hypothesis_assessments)
        self._store.evidence.clear()
        self._store.evidence.update(snapshot.evidence)
        self._store.evidence_admissions.clear()
        self._store.evidence_admissions.update(snapshot.evidence_admissions)
        self._store.candidates.clear()
        self._store.candidates.update(snapshot.candidates)
        self._store.candidate_admissions.clear()
        self._store.candidate_admissions.update(snapshot.candidate_admissions)
        self._store.verifications.clear()
        self._store.verifications.update(snapshot.verifications)
        self._store.finding_proposals.clear()
        self._store.finding_proposals.update(snapshot.finding_proposals)
        self._store.human_reviews.clear()
        self._store.human_reviews.update(snapshot.human_reviews)
        self._store.approvals.clear()
        self._store.approvals.update(snapshot.approvals)
        self._store.findings.clear()
        self._store.findings.update(snapshot.findings)
        self._store.target_inferences.clear()
        self._store.target_inferences.update(snapshot.target_inferences)
        self._store.differential_observations.clear()
        self._store.differential_observations.update(snapshot.differential_observations)
        self._store.invariant_hypotheses.clear()
        self._store.invariant_hypotheses.update(snapshot.invariant_hypotheses)
        self._store.invariant_counterexamples.clear()
        self._store.invariant_counterexamples.update(snapshot.invariant_counterexamples)
        self._store.chain_hypotheses.clear()
        self._store.chain_hypotheses.update(snapshot.chain_hypotheses)
        self._store.research_opportunities.clear()
        self._store.research_opportunities.update(snapshot.research_opportunities)
        self._store.research_selections.clear()
        self._store.research_selections.update(snapshot.research_selections)
        self._store.snapshots.clear()
        self._store.snapshots.update(snapshot.snapshots)
        self._store.snapshot_members.clear()
        self._store.snapshot_members.update(snapshot.snapshot_members)
        self._store.change_events.clear()
        self._store.change_events.update(snapshot.change_events)
        self._store.audit_events.clear()
        self._store.audit_events.update(snapshot.audit_events)


class FakeUnitOfWorkFactory:
    def __init__(self, store: _Store | None = None, fail_on: str | None = None) -> None:
        self.store = store or _Store()
        self.fail_on = fail_on

    def open(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self.store, fail_on=self.fail_on)
