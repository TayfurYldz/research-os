"""Research: proposals only.

A7-lite adds human-seeded HypothesisDraft and ExperimentPlan. This is not a
Research Brain. Research must not execute, authorize, or persist.
"""

from research_os.research.types import ExperimentPlan, HypothesisDraft

__all__ = ["ExperimentPlan", "HypothesisDraft"]
