"""Attempt Evidence admission after an evidence-eligible assessment.

This is the missing Assessment → Evidence hop. It does not create Candidate,
Verification, FindingProposal, or Finding. It does not authorize, dispatch, or
invoke a model.

The reconnection audit's "SUPPORTED" assessment does not exist as an enum in
this repository. The evidence-eligible outcome that maps to that language is
`CONSISTENT_WITH_PREDICTION`. `INCONCLUSIVE`, `EXECUTION_UNUSABLE`,
`NEEDS_MORE_CONTEXT`, and `CONTRADICTS_PREDICTION` do not auto-trigger;
`AdmitDiagnosticEvidence` remains callable for those cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from research_os.application.admit_diagnostic_evidence import (
    AdmitDiagnosticEvidence,
    AdmitDiagnosticEvidenceCommand,
    AdmitDiagnosticEvidenceResult,
)
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.data.records import EvidenceAdmissionRecord
from research_os.research.assessment import AssessmentOutcome, ResearchFeedback
from research_os.research.evidence import EvidenceAdmissionOutcome, SUPPORTED_EVIDENCE_STRATEGIES


class PromotionOutcome(Enum):
    ADMITTED = "ADMITTED"
    ADMISSION_REJECTED = "ADMISSION_REJECTED"
    SKIPPED_NOT_EVIDENCE_ELIGIBLE = "SKIPPED_NOT_EVIDENCE_ELIGIBLE"
    SKIPPED_UNSUPPORTED_STRATEGY = "SKIPPED_UNSUPPORTED_STRATEGY"
    SKIPPED_ALREADY_ATTEMPTED = "SKIPPED_ALREADY_ATTEMPTED"
    SKIPPED_MISSING_ASSESSMENT = "SKIPPED_MISSING_ASSESSMENT"


EVIDENCE_ELIGIBLE_ASSESSMENT_OUTCOMES = frozenset({AssessmentOutcome.CONSISTENT_WITH_PREDICTION})


@dataclass(frozen=True)
class PromotionResult:
    outcome: PromotionOutcome
    assessment_id: str | None
    experiment_id: str
    admission_record_id: str | None = None
    evidence_id: str | None = None
    reason_codes: tuple[str, ...] = ()


class PromotionPipeline:
    """One Evidence-admission attempt per CONSISTENT_WITH_PREDICTION assessment."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        *,
        clock: Clock | None = None,
        admit: AdmitDiagnosticEvidence | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._admit = admit or AdmitDiagnosticEvidence(uow_factory, clock=clock or SystemClock())

    def on_assessment(self, feedback: ResearchFeedback) -> PromotionResult:
        if not feedback.assessment_id:
            return PromotionResult(
                outcome=PromotionOutcome.SKIPPED_MISSING_ASSESSMENT,
                assessment_id=None,
                experiment_id=feedback.experiment_id,
            )
        if feedback.assessment_outcome not in EVIDENCE_ELIGIBLE_ASSESSMENT_OUTCOMES:
            return PromotionResult(
                outcome=PromotionOutcome.SKIPPED_NOT_EVIDENCE_ELIGIBLE,
                assessment_id=feedback.assessment_id,
                experiment_id=feedback.experiment_id,
            )
        if feedback.evaluation_strategy not in SUPPORTED_EVIDENCE_STRATEGIES:
            return PromotionResult(
                outcome=PromotionOutcome.SKIPPED_UNSUPPORTED_STRATEGY,
                assessment_id=feedback.assessment_id,
                experiment_id=feedback.experiment_id,
            )
        existing = self._existing_attempt(feedback.research_run_id, feedback.assessment_id)
        if existing is not None:
            return PromotionResult(
                outcome=PromotionOutcome.SKIPPED_ALREADY_ATTEMPTED,
                assessment_id=feedback.assessment_id,
                experiment_id=feedback.experiment_id,
                admission_record_id=existing.admission_record_id,
                evidence_id=existing.admitted_evidence_id,
                reason_codes=existing.reason_codes,
            )
        admitted = self._admit.execute(
            AdmitDiagnosticEvidenceCommand(
                experiment_id=feedback.experiment_id,
                assessment_id=feedback.assessment_id,
            )
        )
        return _from_admission(feedback, admitted)

    def _existing_attempt(
        self, research_run_id: str, assessment_id: str
    ) -> EvidenceAdmissionRecord | None:
        with self._uow_factory.open() as uow:
            records = uow.evidence_admissions.list_for_research_run(research_run_id)
            uow.rollback()
        matches = [
            record for record in records if assessment_id in record.assessment_ids
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.created_at)[0]


class PromoteOnAssessment:
    """ARC evaluate wrapper. EvaluateExperimentFeedback itself still creates no Evidence."""

    def __init__(
        self,
        evaluate: object,
        promotion: PromotionPipeline,
    ) -> None:
        self._evaluate = evaluate
        self._promotion = promotion

    def execute(self, command):
        feedback = self._evaluate.execute(command)
        self._promotion.on_assessment(feedback)
        return feedback


def _from_admission(
    feedback: ResearchFeedback, admitted: AdmitDiagnosticEvidenceResult
) -> PromotionResult:
    if admitted.outcome is EvidenceAdmissionOutcome.ADMITTED:
        outcome = PromotionOutcome.ADMITTED
    else:
        outcome = PromotionOutcome.ADMISSION_REJECTED
    return PromotionResult(
        outcome=outcome,
        assessment_id=feedback.assessment_id,
        experiment_id=feedback.experiment_id,
        admission_record_id=admitted.admission_record_id,
        evidence_id=admitted.evidence_id,
        reason_codes=admitted.reason_codes,
    )
