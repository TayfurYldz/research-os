"""Human-seeded planning helpers. No model. No Worker. No persistence."""

from __future__ import annotations

from research_os.research.types import ExperimentPlan, HypothesisDraft
from research_os.tools.capabilities import DIAGNOSTIC_ECHO_ACTION, DIAGNOSTIC_ECHO_CAPABILITY

HUMAN_ORIGIN = "human"
DIAGNOSTIC_LOOP_STATEMENT = "diagnostic runtime returns the provided echo value"


def human_seeded_hypothesis(
    statement: str,
    *,
    origin: str = HUMAN_ORIGIN,
) -> HypothesisDraft:
    """Explicit caller seed. Not autonomous generation and not a security hypothesis."""
    return HypothesisDraft(statement=statement, origin=origin)


def plan_diagnostic_echo(
    hypothesis_id: str,
    *,
    budget_id: str,
    target_reference: str,
    message: str,
) -> ExperimentPlan:
    """Level-0 diagnostic plan used to prove the control-loop plumbing."""
    if not isinstance(message, str):
        raise TypeError("message must be a string")
    return ExperimentPlan(
        hypothesis_id=hypothesis_id,
        required_capability=DIAGNOSTIC_ECHO_CAPABILITY,
        action=DIAGNOSTIC_ECHO_ACTION,
        target_reference=target_reference,
        side_effect_level=0,
        arguments={"message": message},
        requested_budget_id=budget_id,
    )
