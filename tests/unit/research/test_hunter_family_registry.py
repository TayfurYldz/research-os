"""SD-G5 HunterFamily registry resolver tests."""

from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.core.enums import ScopeClassification
from research_os.research.discovery.graph import AttackSurfaceGraph, AttackSurfaceNode
from research_os.research.discovery.types import AttackSurfaceNodeKind
from research_os.research.selection import (
    HunterFamilyView,
    HypothesisFamily,
    claim_from_template,
    families_for_node,
    family_for_claim,
)
from research_os.research.target_model import TargetEpistemicStatus
from research_os.research.types import ResearchInputError


def _node(
    *,
    node_id: str,
    kind: AttackSurfaceNodeKind,
    canonical_key: str,
    scope_classification: ScopeClassification = ScopeClassification.IN_SCOPE,
    epistemic_status: TargetEpistemicStatus = TargetEpistemicStatus.UNTRUSTED_EXTERNAL,
    attributes: dict | None = None,
) -> AttackSurfaceNode:
    return AttackSurfaceNode(
        node_id=node_id,
        kind=kind,
        canonical_key=canonical_key,
        epistemic_status=epistemic_status,
        identity_ids=(),
        provenance_refs=(),
        scope_classification=scope_classification,
        attributes=attributes,
    )


def _graph(*nodes: AttackSurfaceNode) -> AttackSurfaceGraph:
    return AttackSurfaceGraph(
        research_run_id="run-1",
        strategy_version="test",
        nodes=nodes,
        edges=(),
    )


class FamilyResolverTests(unittest.TestCase):
    def test_empty_registry_returns_empty_tuple(self) -> None:
        node = _node(node_id="n1", kind=AttackSurfaceNodeKind.HOSTNAME, canonical_key="example.com")
        self.assertEqual(families_for_node(node, _graph(node), ()), ())

    def test_disabled_family_is_not_matched(self) -> None:
        family = HunterFamilyView(
            family_id="hf-disabled",
            name="DISABLED",
            target_node_kinds=("HOSTNAME",),
            preconditions={},
            claim_template="disabled claim for {canonical_key}",
            evidence_requirements={},
            validation_tier="V2",
            enabled=False,
            version=1,
        )
        node = _node(node_id="n1", kind=AttackSurfaceNodeKind.HOSTNAME, canonical_key="example.com")
        self.assertEqual(families_for_node(node, _graph(node), (family,)), ())

    def test_kind_mismatch_returns_empty(self) -> None:
        family = HunterFamilyView(
            family_id="hf-host",
            name="HOST_TEST",
            target_node_kinds=("HOSTNAME",),
            preconditions={},
            claim_template="host claim",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(node_id="n1", kind=AttackSurfaceNodeKind.TECH, canonical_key="tech:nginx")
        self.assertEqual(families_for_node(node, _graph(node), (family,)), ())

    def test_scope_precondition_filters_out(self) -> None:
        family = HunterFamilyView(
            family_id="hf-inscope",
            name="IN_SCOPE_TEST",
            target_node_kinds=("HOSTNAME",),
            preconditions={"scope_classification": "IN_SCOPE"},
            claim_template="inscope claim",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(
            node_id="n1",
            kind=AttackSurfaceNodeKind.HOSTNAME,
            canonical_key="example.com",
            scope_classification=ScopeClassification.UNKNOWN,
        )
        self.assertEqual(families_for_node(node, _graph(node), (family,)), ())

    def test_absent_edge_precondition_filters_out(self) -> None:
        family = HunterFamilyView(
            family_id="hf-unprotected",
            name="UNPROTECTED_HOSTNAME",
            target_node_kinds=("HOSTNAME",),
            preconditions={"absent_edge_kind": "OBSERVED_UNDER"},
            claim_template="unprotected {canonical_key}",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(node_id="n1", kind=AttackSurfaceNodeKind.HOSTNAME, canonical_key="example.com")
        from research_os.research.discovery.graph import AttackSurfaceEdge, AttackSurfaceEdgeKind

        identity_node = AttackSurfaceNode(
            node_id="identity:ANONYMOUS",
            kind=AttackSurfaceNodeKind.IDENTITY_REF,
            canonical_key="identity:ANONYMOUS",
            epistemic_status=TargetEpistemicStatus.OBSERVED,
            identity_ids=("ANONYMOUS",),
            provenance_refs=(),
            scope_classification=ScopeClassification.IN_SCOPE,
        )
        graph_with_edge = AttackSurfaceGraph(
            research_run_id="run-1",
            strategy_version="test",
            nodes=(node, identity_node),
            edges=(
                AttackSurfaceEdge(
                    edge_id="n1:under:ANONYMOUS",
                    kind=AttackSurfaceEdgeKind.OBSERVED_UNDER,
                    from_node_id="n1",
                    to_node_id="identity:ANONYMOUS",
                    identity_id="ANONYMOUS",
                    provenance_refs=(),
                    epistemic_status=TargetEpistemicStatus.OBSERVED,
                ),
            ),
        )
        self.assertEqual(families_for_node(node, graph_with_edge, (family,)), ())

    def test_required_edge_precondition_must_exist(self) -> None:
        family = HunterFamilyView(
            family_id="hf-needs-edge",
            name="NEEDS_EDGE",
            target_node_kinds=("HOSTNAME",),
            preconditions={"required_edge_kind": "RESOLVES_TO"},
            claim_template="needs edge {canonical_key}",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(node_id="n1", kind=AttackSurfaceNodeKind.HOSTNAME, canonical_key="example.com")
        self.assertEqual(families_for_node(node, _graph(node), (family,)), ())

    def test_multiple_families_can_match(self) -> None:
        f1 = HunterFamilyView(
            family_id="hf-a",
            name="A",
            target_node_kinds=("HOSTNAME",),
            preconditions={},
            claim_template="a {canonical_key}",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        f2 = HunterFamilyView(
            family_id="hf-b",
            name="B",
            target_node_kinds=("HOSTNAME", "TECH"),
            preconditions={},
            claim_template="b {canonical_key}",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(node_id="n1", kind=AttackSurfaceNodeKind.HOSTNAME, canonical_key="example.com")
        matched = families_for_node(node, _graph(node), (f1, f2))
        self.assertEqual(len(matched), 2)
        self.assertEqual({item.family_id for item in matched}, {"hf-a", "hf-b"})

    def test_non_node_input_rejected(self) -> None:
        family = HunterFamilyView(
            family_id="hf-a",
            name="A",
            target_node_kinds=("HOSTNAME",),
            preconditions={},
            claim_template="a {canonical_key}",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        with self.assertRaises(ResearchInputError):
            families_for_node("not-a-node", _graph(), (family,))  # type: ignore[arg-type]


class ClaimTemplateTests(unittest.TestCase):
    def test_claim_replaces_canonical_key(self) -> None:
        family = HunterFamilyView(
            family_id="hf-api",
            name="EXPOSED_API_SPEC",
            target_node_kinds=("API_SPEC",),
            preconditions={},
            claim_template="API spec at {canonical_key} documents surface.",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(
            node_id="n1",
            kind=AttackSurfaceNodeKind.API_SPEC,
            canonical_key="origin:http://example.com/spec.json",
        )
        claim = claim_from_template(node, family)
        self.assertIn("origin:http://example.com/spec.json", claim)
        self.assertNotIn("{canonical_key}", claim)

    def test_claim_uses_other_attributes(self) -> None:
        family = HunterFamilyView(
            family_id="hf-tech",
            name="TECH_KNOWN_CVE_SURFACE",
            target_node_kinds=("TECH",),
            preconditions={},
            claim_template="Technology {technology} at {canonical_key} is a candidate.",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(
            node_id="n1",
            kind=AttackSurfaceNodeKind.TECH,
            canonical_key="tech:nginx:example.com",
            attributes={"technology": "nginx"},
        )
        claim = claim_from_template(node, family)
        self.assertIn("nginx", claim)
        self.assertIn("tech:nginx:example.com", claim)

    def test_missing_placeholder_raises(self) -> None:
        family = HunterFamilyView(
            family_id="hf-missing",
            name="MISSING",
            target_node_kinds=("TECH",),
            preconditions={},
            claim_template="Missing {missing_attr} here.",
            evidence_requirements={},
            validation_tier="V2",
            enabled=True,
            version=1,
        )
        node = _node(
            node_id="n1",
            kind=AttackSurfaceNodeKind.TECH,
            canonical_key="tech:nginx:example.com",
            attributes={"technology": "nginx"},
        )
        with self.assertRaises(ResearchInputError):
            claim_from_template(node, family)


class FamilyForClaimBackwardsCompatibilityTests(unittest.TestCase):
    def test_object_authorization_claim_maps_to_enum(self) -> None:
        from research_os.research.planning import HTTP_AUTHORIZATION_DIFFERENTIAL_CLAIM

        self.assertEqual(
            family_for_claim(HTTP_AUTHORIZATION_DIFFERENTIAL_CLAIM),
            HypothesisFamily.OBJECT_AUTHORIZATION,
        )

    def test_workflow_transition_claim_maps_to_enum(self) -> None:
        from research_os.research.planning import HTTP_STATE_TRANSITION_CLAIM

        self.assertEqual(
            family_for_claim(HTTP_STATE_TRANSITION_CLAIM),
            HypothesisFamily.WORKFLOW_STATE_TRANSITION,
        )

    def test_unknown_claim_maps_to_unknown(self) -> None:
        self.assertEqual(
            family_for_claim("some other claim"),
            HypothesisFamily.UNKNOWN,
        )
