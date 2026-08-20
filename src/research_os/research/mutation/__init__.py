"""Mutation Engine: deterministic attack-variant generation from observed surface.

This is the research-layer planning stage. Variants are not executed here;
execution flows through the existing capability/envelope/approval pipeline.
"""

from research_os.research.mutation.engine import MutationEngine, mutate_for_node
from research_os.research.mutation.families import (
    AuthHeaderVariationFamily,
    BoundaryValueFamily,
    ContentTypeConfusionFamily,
    IdOrTraversalCandidateFamily,
    MethodOverrideFamily,
    ParamPollutionFamily,
    TypeJugglingFamily,
)
from research_os.research.mutation.intent import mutation_variant_to_intent
from research_os.research.mutation.matrix import (
    MutationMatrixCell,
    MutationMatrixPlan,
    build_mutation_matrix,
)
from research_os.research.mutation.types import MutationFamily, MutationRule, MutationVariant

__all__ = [
    "MutationEngine",
    "mutate_for_node",
    "MutationFamily",
    "MutationRule",
    "MutationVariant",
    "ParamPollutionFamily",
    "TypeJugglingFamily",
    "BoundaryValueFamily",
    "AuthHeaderVariationFamily",
    "MethodOverrideFamily",
    "ContentTypeConfusionFamily",
    "IdOrTraversalCandidateFamily",
    "mutation_variant_to_intent",
    "MutationMatrixCell",
    "MutationMatrixPlan",
    "build_mutation_matrix",
]
