"""Slice 5 / lock MR-4: one Evidence-admission attempt per CONSISTENT assessment."""

from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.application.admit_diagnostic_evidence import (
    AdmitDiagnosticEvidence,
    AdmitDiagnosticEvidenceCommand,
)
from research_os.application.autonomous_research_controller import (
    AutonomousResearchController,
    StartAutonomousResearchCommand,
)
from research_os.application.evaluate_experiment_feedback import (
    EvaluateExperimentFeedback,
    EvaluateExperimentFeedbackCommand,
)
from research_os.application.execute_planned_experiment import (
    ExecutePlannedExperiment,
    ExecutePlannedExperimentCommand,
)
from research_os.application.promotion_pipeline import (
    PromotionOutcome,
    PromotionPipeline,
    PromoteOnAssessment,
)
from research_os.core.enums import ScopeRuleEffect
from research_os.core.scope import ScopeEvaluationInput, ScopeRuleMatch
from research_os.data.records import IssuedBudgetRecord
from research_os.research.assessment import AssessmentOutcome, ResearchFeedback
from research_os.research.orchestration import OrchestrationBounds, OrchestrationState, StopReason
from research_os.research.planning import plan_diagnostic_echo
from support.fake_model import ScriptedModelPort
from support.fake_unit_of_work import FakeUnitOfWorkFactory, _Store
from support.recording_worker import RecordingWorkerPort
from support.spine import CREATED_AT, seed_authorization_run, seed_spine


class FixedClock:
    def now(self):
        return CREATED_AT


def _allow_scope() -> ScopeEvaluationInput:
    return ScopeEvaluationInput(
        matches=(ScopeRuleMatch("rule-allow", ScopeRuleEffect.ALLOW, True, "scope-src"),),
        ambiguous=False,
    )


def _plan(message: str = "ping"):
    return plan_diagnostic_echo(
        "hyp-1",
        budget_id="budget-1",
        target_reference="target-1",
        message=message,
    )


def _feedback(**overrides) -> ResearchFeedback:
    values = dict(
        hypothesis_id="hyp-1",
        experiment_id="exp-1",
        assessment_id="assess-1",
        assessment_outcome=AssessmentOutcome.CONSISTENT_WITH_PREDICTION,
        observation_ids=("obs-1",),
        execution_usable=True,
        evaluation_strategy="diagnostic.echo.v1",
        research_run_id="run-1",
    )
    values.update(overrides)
    return ResearchFeedback(**values)


def _run_echo(store: _Store, *, handler=None) -> ResearchFeedback:
    factory = FakeUnitOfWorkFactory(store)
    worker = RecordingWorkerPort(store=store, handler=handler)
    ExecutePlannedExperiment(factory, worker, clock=FixedClock()).execute(
        ExecutePlannedExperimentCommand(
            experiment_id="exp-1",
            plan=_plan(),
            scope=_allow_scope(),
        )
    )
    return EvaluateExperimentFeedback(factory, clock=FixedClock()).execute(
        EvaluateExperimentFeedbackCommand(experiment_id="exp-1")
    )


class PromotionPipelineTests(unittest.TestCase):
    def test_consistent_assessment_admits_evidence_exactly_once(self) -> None:
        store = _Store()
        seed_spine(store)
        feedback = _run_echo(store)
        self.assertEqual(feedback.assessment_outcome, AssessmentOutcome.CONSISTENT_WITH_PREDICTION)
        self.assertEqual(len(store.evidence), 0)
        factory = FakeUnitOfWorkFactory(store)
        pipeline = PromotionPipeline(factory, clock=FixedClock())
        first = pipeline.on_assessment(feedback)
        second = pipeline.on_assessment(feedback)
        self.assertEqual(first.outcome, PromotionOutcome.ADMITTED)
        self.assertIsNotNone(first.evidence_id)
        self.assertEqual(second.outcome, PromotionOutcome.SKIPPED_ALREADY_ATTEMPTED)
        self.assertEqual(second.evidence_id, first.evidence_id)
        self.assertEqual(len(store.evidence), 1)
        self.assertEqual(len(store.evidence_admissions), 1)
        self.assertEqual(len(store.candidates), 0)
        self.assertEqual(len(store.verifications), 0)
        self.assertEqual(len(store.finding_proposals), 0)
        self.assertEqual(len(store.findings), 0)

    def test_inconclusive_does_not_admit(self) -> None:
        store = _Store()
        seed_spine(store)
        factory = FakeUnitOfWorkFactory(store)
        feedback = _feedback(
            assessment_outcome=AssessmentOutcome.INCONCLUSIVE,
            execution_usable=True,
        )
        result = PromotionPipeline(factory, clock=FixedClock()).on_assessment(feedback)
        self.assertEqual(result.outcome, PromotionOutcome.SKIPPED_NOT_EVIDENCE_ELIGIBLE)
        self.assertEqual(len(store.evidence), 0)
        self.assertEqual(len(store.evidence_admissions), 0)

    def test_contradicts_does_not_auto_admit(self) -> None:
        store = _Store()
        seed_spine(store)
        factory = FakeUnitOfWorkFactory(store)
        feedback = _feedback(assessment_outcome=AssessmentOutcome.CONTRADICTS_PREDICTION)
        result = PromotionPipeline(factory, clock=FixedClock()).on_assessment(feedback)
        self.assertEqual(result.outcome, PromotionOutcome.SKIPPED_NOT_EVIDENCE_ELIGIBLE)
        self.assertEqual(len(store.evidence), 0)
        self.assertEqual(len(store.evidence_admissions), 0)

    def test_execution_unusable_does_not_admit(self) -> None:
        store = _Store()
        seed_spine(store)
        factory = FakeUnitOfWorkFactory(store)
        feedback = _feedback(
            assessment_outcome=AssessmentOutcome.EXECUTION_UNUSABLE,
            execution_usable=False,
        )
        result = PromotionPipeline(factory, clock=FixedClock()).on_assessment(feedback)
        self.assertEqual(result.outcome, PromotionOutcome.SKIPPED_NOT_EVIDENCE_ELIGIBLE)
        self.assertEqual(len(store.evidence), 0)

    def test_unsupported_strategy_does_not_admit(self) -> None:
        store = _Store()
        seed_spine(store)
        factory = FakeUnitOfWorkFactory(store)
        feedback = _feedback(evaluation_strategy="http.transaction.v1")
        result = PromotionPipeline(factory, clock=FixedClock()).on_assessment(feedback)
        self.assertEqual(result.outcome, PromotionOutcome.SKIPPED_UNSUPPORTED_STRATEGY)
        self.assertEqual(len(store.evidence), 0)

    def test_evaluate_use_case_still_does_not_admit_on_its_own(self) -> None:
        store = _Store()
        seed_spine(store)
        _run_echo(store)
        self.assertEqual(len(store.evidence), 0)
        self.assertEqual(len(store.evidence_admissions), 0)


class ArcPromotionHookTests(unittest.TestCase):
    def test_arc_admits_evidence_for_consistent_assessment_and_stops_there(self) -> None:
        store = _Store()
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
        factory = FakeUnitOfWorkFactory(store)
        port = RecordingWorkerPort(store=store)
        controller = AutonomousResearchController(
            factory, port, ScriptedModelPort(), clock=FixedClock()
        )
        command = StartAutonomousResearchCommand(
            research_run_id="run-1",
            budget_id="budget-1",
            target_reference="target-1",
            scope=_allow_scope(),
            bounds=OrchestrationBounds(
                max_cycles=1,
                max_experiments=1,
                max_model_calls=20,
                max_worker_invocations=4,
                max_elapsed_ms=60_000,
                max_selected_opportunities=1,
                max_runtime_fallback=0,
                side_effect_ceiling=0,
                allow_repeated_control_experiments=True,
            ),
        )
        result = controller.run_bounded(command)
        self.assertEqual(result.state, OrchestrationState.COMPLETED.value)
        self.assertEqual(result.stop_reason, StopReason.MAX_CYCLES_REACHED.value)
        self.assertEqual(len(store.hypothesis_assessments), 1)
        assessment = next(iter(store.hypothesis_assessments.values()))
        self.assertEqual(assessment.assessment_outcome, "CONSISTENT_WITH_PREDICTION")
        self.assertEqual(len(store.evidence), 1)
        self.assertEqual(len(store.evidence_admissions), 1)
        self.assertEqual(len(store.candidates), 0)
        self.assertEqual(len(store.verifications), 0)
        self.assertEqual(len(store.finding_proposals), 0)
        self.assertEqual(len(store.findings), 0)
        evidence = next(iter(store.evidence.values()))
        self.assertEqual(evidence.assessment_ids, (assessment.assessment_id,))
        AdmitDiagnosticEvidence(factory, clock=FixedClock()).execute(
            AdmitDiagnosticEvidenceCommand(experiment_id=assessment.experiment_id)
        )
        self.assertEqual(len(store.evidence), 1)
        self.assertEqual(len(store.evidence_admissions), 1)


class PromoteOnAssessmentWrapperTests(unittest.TestCase):
    def test_wrapper_does_not_create_candidate(self) -> None:
        store = _Store()
        seed_spine(store)
        factory = FakeUnitOfWorkFactory(store)
        worker = RecordingWorkerPort(store=store)
        ExecutePlannedExperiment(factory, worker, clock=FixedClock()).execute(
            ExecutePlannedExperimentCommand(
                experiment_id="exp-1",
                plan=_plan(),
                scope=_allow_scope(),
            )
        )
        evaluate = EvaluateExperimentFeedback(factory, clock=FixedClock())
        wrapped = PromoteOnAssessment(evaluate, PromotionPipeline(factory, clock=FixedClock()))
        wrapped.execute(EvaluateExperimentFeedbackCommand(experiment_id="exp-1"))
        wrapped.execute(EvaluateExperimentFeedbackCommand(experiment_id="exp-1"))
        self.assertEqual(len(store.evidence), 1)
        self.assertEqual(len(store.evidence_admissions), 1)
        self.assertEqual(len(store.candidates), 0)


if __name__ == "__main__":
    unittest.main()
