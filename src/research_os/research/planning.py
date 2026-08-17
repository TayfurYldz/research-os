"""Planning helpers. No Worker. No persistence. No authorization."""

from __future__ import annotations

import json

from research_os.research.assessment import (
    DIAGNOSTIC_ECHO_EVALUATION_STRATEGY,
    HTTP_AUTHORIZATION_DIFFERENTIAL_EVALUATION_STRATEGY,
)
from research_os.research.proposals import HypothesisChallenge, HypothesisProposal
from research_os.research.types import ExperimentPlan, HypothesisDraft, ResearchInputError
from research_os.tools.capabilities import (
    DIAGNOSTIC_ECHO_ACTION,
    DIAGNOSTIC_ECHO_CAPABILITY,
    HTTP_AUTHORIZATION_DIFFERENTIAL_ACTION,
    HTTP_AUTHORIZATION_DIFFERENTIAL_CAPABILITY,
)

HUMAN_ORIGIN = "human"
DIAGNOSTIC_LOOP_STATEMENT = "diagnostic runtime returns the provided echo value"
DIAGNOSTIC_CLAIM = "The diagnostic capability returns the submitted value."
DIAGNOSTIC_EXPECTED_OBSERVATION = "echoed value matches input"
DIAGNOSTIC_DISCONFIRMING_OBSERVATION = "no result or mismatched value"
HTTP_AUTHORIZATION_DIFFERENTIAL_CLAIM = (
    "Authenticated actor can read another actor's account object because object "
    "authorization is missing on the vulnerable endpoint."
)
HTTP_AUTHORIZATION_EXPECTED_OBSERVATION = (
    "authenticated actor reads own object, reads another actor's object with that "
    "object's owner proven, unauthenticated access is denied, and the secure control denies cross-object access"
)
HTTP_AUTHORIZATION_DISCONFIRMING_OBSERVATION = (
    "cross-object access is denied or the returned object is not the other actor's object"
)


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
        expected_observation=DIAGNOSTIC_EXPECTED_OBSERVATION,
        disconfirming_observation=DIAGNOSTIC_DISCONFIRMING_OBSERVATION,
        evaluation_strategy=DIAGNOSTIC_ECHO_EVALUATION_STRATEGY,
    )


def plan_authorization_differential(
    hypothesis_id: str,
    *,
    budget_id: str,
    target_reference: str,
    authorized_origin: str,
    actor: str,
    own_object: str,
    cross_object: str,
    mode: str = "vulnerable",
) -> ExperimentPlan:
    """Level-0 local lab plan. Not internet scanning and not autonomous discovery."""
    if mode not in {"vulnerable", "secure_only", "redirect"}:
        raise ResearchInputError("mode must be vulnerable, secure_only, or redirect")
    return ExperimentPlan(
        hypothesis_id=hypothesis_id,
        required_capability=HTTP_AUTHORIZATION_DIFFERENTIAL_CAPABILITY,
        action=HTTP_AUTHORIZATION_DIFFERENTIAL_ACTION,
        target_reference=target_reference,
        side_effect_level=0,
        arguments={
            "authorized_origin": authorized_origin,
            "actor": actor,
            "own_object": own_object,
            "cross_object": cross_object,
            "mode": mode,
        },
        requested_budget_id=budget_id,
        expected_observation=HTTP_AUTHORIZATION_EXPECTED_OBSERVATION,
        disconfirming_observation=HTTP_AUTHORIZATION_DISCONFIRMING_OBSERVATION,
        evaluation_strategy=HTTP_AUTHORIZATION_DIFFERENTIAL_EVALUATION_STRATEGY,
    )


def plan_admitted_hypothesis(
    hypothesis_id: str,
    proposal: HypothesisProposal,
    challenge: HypothesisChallenge,
    *,
    budget_id: str,
    target_reference: str,
    message: str = "ping",
) -> ExperimentPlan:
    """Convert an admitted Hypothesis into a testable ExperimentPlan. Does not dispatch."""
    capability = proposal.suggested_capability
    action = DIAGNOSTIC_ECHO_ACTION if capability == DIAGNOSTIC_ECHO_CAPABILITY else capability
    arguments: dict[str, str] = {}
    strategy = (
        DIAGNOSTIC_ECHO_EVALUATION_STRATEGY
        if capability == DIAGNOSTIC_ECHO_CAPABILITY
        else capability
    )
    if capability == DIAGNOSTIC_ECHO_CAPABILITY:
        arguments = {"message": message}
    return ExperimentPlan(
        hypothesis_id=hypothesis_id,
        required_capability=capability,
        action=action,
        target_reference=target_reference,
        side_effect_level=0,
        arguments=arguments,
        requested_budget_id=budget_id,
        expected_observation=DIAGNOSTIC_EXPECTED_OBSERVATION
        if capability == DIAGNOSTIC_ECHO_CAPABILITY
        else proposal.suggested_disconfirming_test,
        disconfirming_observation=challenge.proposed_disconfirming_observation,
        evaluation_strategy=strategy,
    )


def plan_canonical_identity(plan: ExperimentPlan) -> str:
    """Deterministic identity of an executed plan. Not authorization."""
    payload = {
        "hypothesis_id": plan.hypothesis_id,
        "required_capability": plan.required_capability,
        "action": plan.action,
        "target_reference": plan.target_reference,
        "side_effect_level": plan.side_effect_level,
        "arguments": plan.arguments,
        "requested_budget_id": plan.requested_budget_id,
        "expected_observation": plan.expected_observation,
        "disconfirming_observation": plan.disconfirming_observation,
        "evaluation_strategy": plan.evaluation_strategy,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def plans_equivalent(left: ExperimentPlan, right: ExperimentPlan) -> bool:
    return plan_canonical_identity(left) == plan_canonical_identity(right)
