from __future__ import annotations

import unittest

import pathsetup  # noqa: F401

from research_os.research.impact.chain import (
    ImpactChain,
    ImpactEdge,
    ImpactGraphError,
    ImpactNode,
    ImpactScopeRef,
)
from research_os.research.impact.types import ImpactKind, ImpactRelation


def _scope() -> ImpactScopeRef:
    return ImpactScopeRef(
        research_run_id="run-1",
        program_id="prog-1",
        target_reference="https://example.com",
    )


def _node(node_id: str, **overrides) -> ImpactNode:
    defaults = dict(
        proof_refs=("proof-1",),
        impact_kind=ImpactKind.DATA_READ,
        claim_text="attacker can read another user's object",
        scope_ref=_scope(),
        provenance={"source": "test"},
    )
    defaults.update(overrides)
    return ImpactNode(node_id=node_id, **defaults)


class ImpactChainConstructionTests(unittest.TestCase):
    def test_minimal_chain_accepts(self) -> None:
        node = _node("n1")
        chain = ImpactChain(chain_id="c1", nodes=(node,), edges=())
        self.assertEqual(chain.chain_id, "c1")
        self.assertEqual(len(chain.nodes), 1)

    def test_empty_nodes_rejected(self) -> None:
        with self.assertRaises(ImpactGraphError) as ctx:
            ImpactChain(chain_id="c1", nodes=(), edges=())
        self.assertIn("CHAIN_HAS_NO_NODES", str(ctx.exception))

    def test_dangling_edge_from_node_rejected(self) -> None:
        node = _node("n1")
        edge = ImpactEdge(from_node_id="missing", to_node_id="n1", relation=ImpactRelation.ENABLES)
        with self.assertRaises(ImpactGraphError) as ctx:
            ImpactChain(chain_id="c1", nodes=(node,), edges=(edge,))
        self.assertIn("DANGLING_EDGE_FROM_NODE", str(ctx.exception))

    def test_dangling_edge_to_node_rejected(self) -> None:
        node = _node("n1")
        edge = ImpactEdge(from_node_id="n1", to_node_id="missing", relation=ImpactRelation.ENABLES)
        with self.assertRaises(ImpactGraphError) as ctx:
            ImpactChain(chain_id="c1", nodes=(node,), edges=(edge,))
        self.assertIn("DANGLING_EDGE_TO_NODE", str(ctx.exception))

    def test_self_loop_rejected(self) -> None:
        node = _node("n1")
        edge = ImpactEdge(from_node_id="n1", to_node_id="n1", relation=ImpactRelation.ENABLES)
        with self.assertRaises(ImpactGraphError) as ctx:
            ImpactChain(chain_id="c1", nodes=(node,), edges=(edge,))
        self.assertIn("SELF_LOOP_NOT_ALLOWED", str(ctx.exception))

    def test_cycle_rejected(self) -> None:
        n1 = _node("n1")
        n2 = _node("n2")
        n3 = _node("n3")
        edges = (
            ImpactEdge(from_node_id="n1", to_node_id="n2", relation=ImpactRelation.ENABLES),
            ImpactEdge(from_node_id="n2", to_node_id="n3", relation=ImpactRelation.ENABLES),
            ImpactEdge(from_node_id="n3", to_node_id="n1", relation=ImpactRelation.ENABLES),
        )
        with self.assertRaises(ImpactGraphError) as ctx:
            ImpactChain(chain_id="c1", nodes=(n1, n2, n3), edges=edges)
        self.assertIn("CHAIN_CONTAINS_CYCLE", str(ctx.exception))

    def test_dag_accepts(self) -> None:
        n1 = _node("n1")
        n2 = _node("n2")
        n3 = _node("n3")
        edges = (
            ImpactEdge(from_node_id="n1", to_node_id="n2", relation=ImpactRelation.ENABLES),
            ImpactEdge(from_node_id="n1", to_node_id="n3", relation=ImpactRelation.ENABLES),
        )
        chain = ImpactChain(chain_id="c1", nodes=(n1, n2, n3), edges=edges)
        self.assertEqual(len(chain.edges), 2)

    def test_empty_proof_refs_rejected_at_node(self) -> None:
        with self.assertRaises(Exception):
            _node("n1", proof_refs=())
