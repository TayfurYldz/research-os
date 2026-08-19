"""Deterministic hypothesis generation from AttackSurfaceGraph + HunterFamily registry.

No model call in the default path. Optional LLM enrichment is budget-gated
through the existing price-class routing policy, not implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research_os.application.identity import new_opaque_id
from research_os.application.ports import Clock, SystemClock, UnitOfWorkFactory
from research_os.core.enums import ActorType
from research_os.data.records import AuditEventRecord, HypothesisRecord
from research_os.data.unit_of_work import UnitOfWork
from research_os.research.discovery.graph import AttackSurfaceGraph
from research_os.research.selection import (
    HunterFamilyView,
    claim_from_template,
    families_for_node,
)


HUNT_HYPOTHESIS_GENERATED = "HUNT_HYPOTHESIS_GENERATED"
HYPOTHESIS_GENERATOR_ACTOR_ID = "control-plane:hunt-generator"


@dataclass(frozen=True)
class GenerateHuntHypothesesCommand:
    research_run_id: str
    graph: AttackSurfaceGraph
    registry: tuple[HunterFamilyView, ...] | None = None


@dataclass(frozen=True)
class GenerateHuntHypothesesResult:
    research_run_id: str
    hypothesis_ids: tuple[str, ...]
    generated_count: int
    # (hypothesis_id, node_id, family_id) for each generated hypothesis.
    hypothesis_sources: tuple[tuple[str, str, str], ...]


class GenerateHuntHypotheses:
    """Produce Hypothesis records from graph nodes and the data-driven family registry.

    This is deterministic, static logic: it does not call a model by default and
    does not create FindingProposals or Candidates. Each hypothesis is an
    untrusted claim ready for V1/V2/V3 validation tiers.
    """

    def __init__(self, uow_factory: UnitOfWorkFactory, *, clock: Clock | None = None) -> None:
        self._uow_factory = uow_factory
        self._clock = clock or SystemClock()

    def execute(self, command: GenerateHuntHypothesesCommand) -> GenerateHuntHypothesesResult:
        now = self._clock.now()
        with self._uow_factory.open() as uow:
            registry = command.registry
            if registry is None:
                registry = tuple(_to_view(item) for item in uow.hunter_families.list_enabled())
            hypothesis_ids: list[str] = []
            hypothesis_sources: list[tuple[str, str, str]] = []
            for node in command.graph.nodes:
                for family in families_for_node(node, command.graph, registry):
                    claim = claim_from_template(node, family)
                    hypothesis_id = new_opaque_id()
                    hypothesis_ids.append(hypothesis_id)
                    hypothesis_sources.append((hypothesis_id, node.node_id, family.family_id))
                    uow.hypotheses.insert(
                        HypothesisRecord(
                            hypothesis_id=hypothesis_id,
                            research_run_id=command.research_run_id,
                            claim=claim,
                            origin_reference=family.family_id,
                            created_at=now,
                        )
                    )
                    uow.audit_events.insert(
                        _generation_audit(
                            audit_id=new_opaque_id(),
                            occurred_at=now,
                            research_run_id=command.research_run_id,
                            hypothesis_id=hypothesis_id,
                            family_id=family.family_id,
                            node_canonical_key=node.canonical_key,
                            claim=claim,
                            validation_tier=family.validation_tier,
                        )
                    )
            uow.commit()
        return GenerateHuntHypothesesResult(
            research_run_id=command.research_run_id,
            hypothesis_ids=tuple(hypothesis_ids),
            generated_count=len(hypothesis_ids),
            hypothesis_sources=tuple(hypothesis_sources),
        )


def _to_view(record) -> HunterFamilyView:
    """Map a HunterFamilyRecord to the research-layer view."""
    return HunterFamilyView(
        family_id=record.family_id,
        name=record.name,
        target_node_kinds=record.target_node_kinds,
        preconditions=record.preconditions,
        claim_template=record.claim_template,
        evidence_requirements=record.evidence_requirements,
        validation_tier=record.validation_tier,
        enabled=record.enabled,
        version=record.version,
    )


def _generation_audit(
    *,
    audit_id: str,
    occurred_at,
    research_run_id: str,
    hypothesis_id: str,
    family_id: str,
    node_canonical_key: str,
    claim: str,
    validation_tier: str,
) -> AuditEventRecord:
    return AuditEventRecord(
        audit_event_id=audit_id,
        occurred_at=occurred_at,
        actor_id=HYPOTHESIS_GENERATOR_ACTOR_ID,
        actor_type=ActorType.CONTROL_PLANE.value,
        event_type=HUNT_HYPOTHESIS_GENERATED,
        subject_type="hypothesis",
        subject_id=hypothesis_id,
        correlation_id=research_run_id,
        payload={
            "research_run_id": research_run_id,
            "family_id": family_id,
            "node_canonical_key": node_canonical_key,
            "claim": claim,
            "validation_tier": validation_tier,
            "source": "deterministic_template",
        },
    )