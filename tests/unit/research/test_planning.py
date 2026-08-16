from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.research.planning import (
    DIAGNOSTIC_LOOP_STATEMENT,
    human_seeded_hypothesis,
    plan_diagnostic_echo,
)
from research_os.research.types import ExperimentPlan, ResearchInputError


class ResearchPlanningTests(unittest.TestCase):
    def test_human_seeded_hypothesis_is_not_a_security_finding(self) -> None:
        draft = human_seeded_hypothesis(DIAGNOSTIC_LOOP_STATEMENT)
        self.assertEqual(draft.origin, "human")
        self.assertEqual(draft.statement, DIAGNOSTIC_LOOP_STATEMENT)
        self.assertFalse(hasattr(draft, "confidence"))
        self.assertFalse(hasattr(draft, "severity"))
        self.assertFalse(hasattr(draft, "vulnerability_type"))

    def test_experiment_plan_has_no_judgment_fields(self) -> None:
        plan = plan_diagnostic_echo(
            "hyp-1",
            budget_id="budget-1",
            target_reference="target-1",
            message="ping",
        )
        self.assertEqual(plan.required_capability, "diagnostic.echo")
        self.assertEqual(plan.side_effect_level, 0)
        self.assertFalse(hasattr(plan, "exploitability"))
        self.assertFalse(hasattr(plan, "novelty_score"))

    def test_empty_statement_rejected(self) -> None:
        with self.assertRaises(ResearchInputError):
            human_seeded_hypothesis("  ")

    def test_invalid_side_effect_rejected(self) -> None:
        with self.assertRaises(ResearchInputError):
            ExperimentPlan(
                hypothesis_id="hyp-1",
                required_capability="diagnostic.echo",
                action="echo",
                target_reference="target-1",
                side_effect_level=9,
                arguments={},
                requested_budget_id="budget-1",
            )


if __name__ == "__main__":
    unittest.main()
