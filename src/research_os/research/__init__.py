"""Research: proposals only. A7 adds a bounded reasoning cycle, not an autonomous brain.

Research must not execute, authorize, persist via PostgreSQL, or import provider SDKs.
Model output is an untrusted structured proposal until Research admission.
"""

from research_os.research.admission import AdmissionDecision, AdmissionOutcome, admit_hypothesis
from research_os.research.assessment import (
    AssessmentOutcome,
    ExperimentEvaluatorRegistry,
    HypothesisAssessment,
    ResearchFeedback,
    default_evaluator_registry,
)
from research_os.research.context import ResearchContext, ResearchContextBuilder
from research_os.research.epistemic import EpistemicClass
from research_os.research.feedback import ExperimentFeedback
from research_os.research.model_port import ModelCallRequest, ModelCallResult, ModelPort, ModelRole
from research_os.research.proposals import HypothesisChallenge, HypothesisProposal
from research_os.research.types import ExperimentPlan, HypothesisDraft

__all__ = [
    "AdmissionDecision",
    "AdmissionOutcome",
    "AssessmentOutcome",
    "EpistemicClass",
    "ExperimentEvaluatorRegistry",
    "ExperimentFeedback",
    "ExperimentPlan",
    "HypothesisAssessment",
    "HypothesisChallenge",
    "HypothesisDraft",
    "HypothesisProposal",
    "ModelCallRequest",
    "ModelCallResult",
    "ModelPort",
    "ModelRole",
    "ResearchContext",
    "ResearchContextBuilder",
    "ResearchFeedback",
    "admit_hypothesis",
    "default_evaluator_registry",
]
