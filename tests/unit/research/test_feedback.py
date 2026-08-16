from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.research.feedback import ExperimentFeedback
from research_os.research.types import ResearchInputError


class ExperimentFeedbackTests(unittest.TestCase):
    def test_feedback_has_no_vulnerability_verdict(self) -> None:
        feedback = ExperimentFeedback(
            hypothesis_id="hyp-1",
            experiment_id="exp-1",
            execution_outcome="OBSERVATION_PRODUCED",
            observation_ids=("obs-1",),
            research_run_id="run-1",
            context_fingerprint="abc",
        )
        self.assertFalse(hasattr(feedback, "severity"))
        self.assertFalse(hasattr(feedback, "finding"))
        self.assertFalse(hasattr(feedback, "evidence"))
        self.assertFalse(hasattr(feedback, "vulnerability"))

    def test_empty_hypothesis_rejected(self) -> None:
        with self.assertRaises(ResearchInputError):
            ExperimentFeedback(
                hypothesis_id=" ",
                experiment_id="exp-1",
                execution_outcome="NO_OBSERVATION",
                observation_ids=(),
                research_run_id="run-1",
            )


if __name__ == "__main__":
    unittest.main()
