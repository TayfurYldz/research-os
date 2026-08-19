"""Impact scope rule: demonstrated capabilities bound claimed impact kinds.

K3 enforcement: an ImpactNode's impact_kind must not exceed the capabilities
actually demonstrated by its referenced proofs.
"""

from __future__ import annotations

from research_os.research.impact.chain import ImpactChain, ImpactNode
from research_os.research.impact.types import ChainValidation, ProofResolver


# Demonstrated capability -> allowed impact kinds.
# Unknown capability contributes nothing (fail-closed empty set).
DEMONSTRATED_CAPABILITY_TO_IMPACT_KIND: dict[str, frozenset[str]] = {
    "READ_OTHER_OBJECT": frozenset({"DATA_READ", "AUTH_BYPASS"}),
    "WORKFLOW_TRANSITION_WITHOUT_AUTH": frozenset({"STATE_CORRUPTION", "AUTH_BYPASS"}),
    "OAST_CALLBACK_RECEIVED": frozenset({"EXTERNAL_CALLBACK"}),
    "AUTHENTICATED_AS_USER": frozenset({"AUTH_BYPASS"}),
    "PRIVILEGE_ESCALATION_EVIDENCE": frozenset({"AUTH_BYPASS", "ACCOUNT_TAKEOVER_PATH"}),
    "WRITE_OTHER_OBJECT": frozenset({"DATA_WRITE", "STATE_CORRUPTION"}),
    "CROSS_ACCOUNT_SESSION_ASSUMPTION": frozenset({"ACCOUNT_TAKEOVER_PATH"}),
}


def _allowed_kinds(capabilities: frozenset[str]) -> frozenset[str]:
    allowed: set[str] = set()
    for capability in capabilities:
        allowed.update(DEMONSTRATED_CAPABILITY_TO_IMPACT_KIND.get(capability, frozenset()))
    return frozenset(allowed)


def validate_impact_scope(
    node: ImpactNode,
    resolver: ProofResolver,
) -> ChainValidation:
    """Check that a node's impact_kind is supported by its proof capabilities."""

    capabilities: set[str] = set()
    for proof_id in node.proof_refs:
        record = resolver.resolve(proof_id)
        if record is None:
            return ChainValidation(
                valid=False,
                reason_codes=("HALLUCINATED_OR_ABSENT_PROOF",),
            )
        capabilities.update(record.demonstrated_capabilities)
    allowed = _allowed_kinds(frozenset(capabilities))
    if node.impact_kind.value not in allowed:
        return ChainValidation(
            valid=False,
            reason_codes=("IMPACT_EXCEEDS_DEMONSTRATED_CAPABILITY",),
        )
    return ChainValidation(
        valid=True,
        reason_codes=("IMPACT_KIND_WITHIN_DEMONSTRATED_CAPABILITY",),
    )


def validate_chain_impact_scope(
    chain: ImpactChain,
    resolver: ProofResolver,
) -> ChainValidation:
    """Validate K3 for every node in the chain."""

    reason_codes: list[str] = []
    for node in chain.nodes:
        result = validate_impact_scope(node, resolver)
        if not result.valid:
            reason_codes.extend(result.reason_codes)
    if reason_codes:
        return ChainValidation(valid=False, reason_codes=tuple(reason_codes))
    return ChainValidation(
        valid=True,
        reason_codes=("IMPACT_SCOPE_VALIDATED",),
    )
