"""V1/V2/V3 validation tiers for hunt hypotheses.

Each tier decision is durable in the audit ledger. V3 is never reached unless
V1 and V2 have passed. This module does not execute active experiments; it
only enqueues them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_os.application.identity import new_opaque_id
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.core.enums import ActorType, ScopeClassification
from research_os.data.records import AuditEventRecord, HuntV3QueueRecord
from research_os.data.unit_of_work import UnitOfWork
from research_os.research.discovery.graph import AttackSurfaceGraph
from research_os.research.selection import HunterFamilyView, claim_from_template
from research_os.research.types import ResearchInputError


HUNT_VALIDATION_ACTOR_ID = "control-plane:hunt-validation"
HYPOTHESIS_TIER_V1_PASSED = "HUNT_TIER_V1_PASSED"
HYPOTHESIS_TIER_V2_PASSED = "HUNT_TIER_V2_PASSED"
HYPOTHESIS_TIER_V2_REJECTED = "HUNT_TIER_V2_REJECTED"
HYPOTHESIS_TIER_V3_QUEUED = "HUNT_TIER_V3_QUEUED"

# Mirrors the two historical authorization capabilities; new families stay V2.
V3_CAPABILITY_FOR_FAMILY = {
    "OBJECT_AUTHORIZATION": "http.authorization_differential",
    "WORKFLOW_STATE_TRANSITION": "http.state_transition_authorization",
}

V3_ACTION_FOR_CAPABILITY = {
    "http.authorization_differential": "probe",
    "http.state_transition_authorization": "probe",
}


@dataclass(frozen=True)
class ValidateHuntTiersCommand:
    research_run_id: str
    hypothesis_id: str
    family: HunterFamilyView
    node_id: str
    graph: AttackSurfaceGraph


@dataclass(frozen=True)
class ValidateHuntTiersResult:
    research_run_id: str
    hypothesis_id: str
    v1_passed: bool
    v2_passed: bool
    v3_queued: bool
    queue_id: str | None
    reason_code: str


class HuntValidationTierError(Exception):
    """Raised when tier inputs are invalid; does not indicate a rejection outcome."""


class ValidateHuntTiers:
    """Run V1 (static), V2 (passive), and V3 (active enqueue) validation for one hypothesis."""

    def __init__(self, uow_factory: UnitOfWorkFactory, *, clock: Clock | None = None) -> None:
        self._uow_factory = uow_factory
        self._clock = clock or SystemClock()

    def execute(self, command: ValidateHuntTiersCommand) -> ValidateHuntTiersResult:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            hypothesis = uow.hypotheses.get(command.hypothesis_id)
            if hypothesis is None:
                raise HuntValidationTierError("hypothesis not found")
            if hypothesis.research_run_id != command.research_run_id:
                raise HuntValidationTierError("hypothesis does not belong to run")

            node = next(
                (item for item in command.graph.nodes if item.node_id == command.node_id), None
            )
            if node is None:
                raise HuntValidationTierError("node not found in graph")

            # V1: static precondition match (already guaranteed by generation, re-verify).
            v1_passed = self._v1_static_check(node, command.family, command.graph)
            uow.audit_events.insert(
                _tier_audit(
                    audit_id=new_opaque_id(),
                    occurred_at=now,
                    research_run_id=command.research_run_id,
                    hypothesis_id=command.hypothesis_id,
                    family_id=command.family.family_id,
                    tier="V1",
                    outcome="PASSED" if v1_passed else "REJECTED",
                    reason_code="STATIC_PRECONDITIONS_MET" if v1_passed else "STATIC_PRECONDITIONS_FAILED",
                    node_canonical_key=node.canonical_key,
                )
            )
            if not v1_passed:
                uow.commit()
                return _result(command, v1_passed=False, reason_code="STATIC_PRECONDITIONS_FAILED")

            # V2: passive/semi-passive evidence check.
            v2_passed, v2_reason = self._v2_passive_check(node, command.family, command.graph)
            uow.audit_events.insert(
                _tier_audit(
                    audit_id=new_opaque_id(),
                    occurred_at=now,
                    research_run_id=command.research_run_id,
                    hypothesis_id=command.hypothesis_id,
                    family_id=command.family.family_id,
                    tier="V2",
                    outcome="PASSED" if v2_passed else "REJECTED",
                    reason_code=v2_reason,
                    node_canonical_key=node.canonical_key,
                )
            )
            if not v2_passed:
                uow.commit()
                return _result(command, v1_passed=True, v2_passed=False, reason_code=v2_reason)

            # V3: only if V1+V2 passed and family tier is V3.
            v3_queued = False
            queue_id: str | None = None
            if command.family.validation_tier == "V3":
                identity_id = hypothesis.identity_id
                queue_id = self._enqueue_v3(uow, command, node, identity_id, now)
                v3_queued = True
                uow.audit_events.insert(
                    _tier_audit(
                        audit_id=new_opaque_id(),
                        occurred_at=now,
                        research_run_id=command.research_run_id,
                        hypothesis_id=command.hypothesis_id,
                        family_id=command.family.family_id,
                        tier="V3",
                        outcome="QUEUED",
                        reason_code="AWAITING_ACTIVE_EXPERIMENT_APPROVAL",
                        node_canonical_key=node.canonical_key,
                        queue_id=queue_id,
                    )
                )

            uow.commit()
            return _result(
                command,
                v1_passed=True,
                v2_passed=True,
                v3_queued=v3_queued,
                queue_id=queue_id,
                reason_code="AWAITING_ACTIVE_EXPERIMENT_APPROVAL" if v3_queued else "V2_TIER_PASSED",
            )

    def _v1_static_check(
        self, node, family: HunterFamilyView, graph: AttackSurfaceGraph
    ) -> bool:
        from research_os.research.selection import families_for_node

        return family in families_for_node(node, graph, (family,))

    def _v2_passive_check(
        self, node, family: HunterFamilyView, graph: AttackSurfaceGraph
    ) -> tuple[bool, str]:
        requirements = family.evidence_requirements
        required_fact_kinds = requirements.get("required_fact_kinds", [])
        required_edge_kind = requirements.get("required_edge_kind")

        if required_fact_kinds:
            if node.kind.value not in required_fact_kinds:
                return False, "REQUIRED_FACT_KIND_MISSING"

        if required_edge_kind is not None:
            has_edge = any(
                edge.kind.value == required_edge_kind
                and (edge.from_node_id == node.node_id or edge.to_node_id == node.node_id)
                for edge in graph.edges
            )
            if not has_edge:
                return False, "REQUIRED_EDGE_KIND_MISSING"

        return True, "PASSIVE_EVIDENCE_SATISFIED"

    def _enqueue_v3(
        self,
        uow: UnitOfWork,
        command: ValidateHuntTiersCommand,
        node,
        identity_id: str | None,
        now,
    ) -> str:
        # G5 mühür notu: V3 aktif deney kuyruğu yalnızca IN_SCOPE node'lara açık.
        if node.scope_classification is not ScopeClassification.IN_SCOPE:
            raise HuntValidationTierError(
                f"V3 enqueue requires IN_SCOPE node, got {node.scope_classification.value}"
            )
        capability = V3_CAPABILITY_FOR_FAMILY.get(command.family.name)
        if capability is None:
            raise HuntValidationTierError(
                f"V3 family {command.family.name} has no mapped capability"
            )
        action = V3_ACTION_FOR_CAPABILITY.get(capability)
        if action is None:
            raise HuntValidationTierError(
                f"V3 capability {capability} has no mapped action"
            )
        queue_id = new_opaque_id()
        claim = claim_from_template(
            node, command.family, extra_context={"identity_id": identity_id or "ANONYMOUS"}
        )
        uow.hunt_v3_queue.insert(
            HuntV3QueueRecord(
                queue_id=queue_id,
                research_run_id=command.research_run_id,
                hypothesis_id=command.hypothesis_id,
                family_id=command.family.family_id,
                node_canonical_key=node.canonical_key,
                identity_id=identity_id,
                capability=capability,
                action=action,
                arguments={
                    "claim": claim,
                    "node_id": node.node_id,
                    "family_name": command.family.name,
                    "identity_id": identity_id or "ANONYMOUS",
                },
                side_effect_level=_side_effect_for_family(command.family.name),
                state="PENDING",
                created_at=now,
            )
        )
        return queue_id


def _side_effect_for_family(family_name: str) -> int:
    if family_name == "WORKFLOW_STATE_TRANSITION":
        return 1
    return 0


def _result(
    command: ValidateHuntTiersCommand,
    *,
    v1_passed: bool,
    v2_passed: bool = False,
    v3_queued: bool = False,
    queue_id: str | None = None,
    reason_code: str,
) -> ValidateHuntTiersResult:
    return ValidateHuntTiersResult(
        research_run_id=command.research_run_id,
        hypothesis_id=command.hypothesis_id,
        v1_passed=v1_passed,
        v2_passed=v2_passed,
        v3_queued=v3_queued,
        queue_id=queue_id,
        reason_code=reason_code,
    )


def _tier_audit(
    *,
    audit_id: str,
    occurred_at,
    research_run_id: str,
    hypothesis_id: str,
    family_id: str,
    tier: str,
    outcome: str,
    reason_code: str,
    node_canonical_key: str,
    queue_id: str | None = None,
) -> AuditEventRecord:
    payload: dict[str, Any] = {
        "research_run_id": research_run_id,
        "family_id": family_id,
        "tier": tier,
        "outcome": outcome,
        "reason_code": reason_code,
        "node_canonical_key": node_canonical_key,
    }
    if queue_id is not None:
        payload["queue_id"] = queue_id
    return AuditEventRecord(
        audit_event_id=audit_id,
        occurred_at=occurred_at,
        actor_id=HUNT_VALIDATION_ACTOR_ID,
        actor_type=ActorType.CONTROL_PLANE.value,
        event_type=_event_type_for_tier(tier, outcome),
        subject_type="hypothesis",
        subject_id=hypothesis_id,
        correlation_id=research_run_id,
        payload=payload,
    )


def _event_type_for_tier(tier: str, outcome: str) -> str:
    if tier == "V1":
        return HYPOTHESIS_TIER_V1_PASSED if outcome == "PASSED" else "HUNT_TIER_V1_REJECTED"
    if tier == "V2":
        return HYPOTHESIS_TIER_V2_PASSED if outcome == "PASSED" else HYPOTHESIS_TIER_V2_REJECTED
    if tier == "V3" and outcome == "QUEUED":
        return HYPOTHESIS_TIER_V3_QUEUED
    return "HUNT_TIER_DECISION"