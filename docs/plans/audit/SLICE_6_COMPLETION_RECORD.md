# Slice 6 Completion Record — Epistemic hardening (edge proof + severity bound)

Status: CLOSED / PASS.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 6 — Epistemic hardening: ImpactGraph edge proof + severity bound". Seventh slice this campaign. Independent of reconnection slices; sequenced after Slice 5 because Slice 5 increases Evidence volume flowing toward Finding-adjacent work.

## Defects closed

1. **Unproven ImpactGraph edges.** Nodes already required non-empty `proof_refs`, resolved against Evidence/Observation/Experiment. Edges (`ENABLES` / `ESCALATES` / `CONFIRMS`) carried no proof of the *relation*. An attacker-or-caller could persist a causal chain between two proven nodes without independent proof that the relationship holds.

2. **Caller-supplied severity escalation.** `ScoreFindingSeverity` accepted `data_sensitivity` / `affected_scope` that independently drove P0 (`BULK_SENSITIVE`, `ADMIN`, `INFRASTRUCTURE`) even when the ImpactGraph only demonstrated `DATA_READ` (P2).

Hard-fail avoided: node-level proof requirements were not relaxed. Edge proofs are additional, not a substitute.

## What changed

Domain:

- `ImpactEdge` now requires non-empty `proof_refs` (`EMPTY_EDGE_PROOF_REFS` at construction).
- `validate_chain()` resolves edge proofs with the same resolver/cross-run rules as nodes (`HALLUCINATED_OR_ABSENT_PROOF`, `CROSS_RUN_PROOF`).

Persistence (additive):

- `ImpactChainEdgeRecord.proof_refs` — non-empty opaque-id tuple, same rigor as nodes.
- `impact_chain_edge.proof_refs` JSONB NOT NULL.
- `a37_001_impact_edge_proof` (revises `a36_001_opportunity_candidate`). Server default `'[]'` only for the ALTER of existing empty tables; default dropped immediately. New writes must supply proofs. Record-layer read of an empty array fails closed.

Application:

- `RegisterImpactChain` persists edge `proof_refs`.
- `rebuild_impact_chain` round-trips them.
- `ScoreFindingSeverity` classifies twice: demonstrated impact with default `NONE` / `SINGLE_USER`, then the caller-requested fields. `bound_severity()` returns the less-severe of the two. Caller escalation adds `CALLER_SEVERITY_CLAMPED`. Caller may not raise severity above the ImpactGraph-derived class.

`classify_severity()` as a pure function still accepts BULK_SENSITIVE → P0. That is input-in, output-out. The **use case** is what is bounded, which is the defect the audit named.

## Files changed

- `src/research_os/research/impact/chain.py`
- `src/research_os/research/impact/validator.py`
- `src/research_os/research/validation/severity.py` — `bound_severity`
- `src/research_os/application/score_finding_severity.py`
- `src/research_os/application/impact/register_impact_chain.py`
- `src/research_os/application/impact/proof_resolver.py`
- `src/research_os/data/records.py`, `tables.py`, `mapping.py`, `repositories.py`
- `alembic/versions/a37_001_impact_edge_proof.py`
- tests: chain, validator, severity, alembic smoke, sd_g10 clamp, alembic-head bumps

## Qualification

| Criterion | Status |
|---|---|
| Edges without resolvable proof rejected | **PASS** |
| Empty edge proof_refs rejected at construction | **PASS** |
| Node proof requirements unchanged | **PASS** |
| Caller ADMIN/BULK_SENSITIVE cannot escalate DATA_READ above P2 | **PASS** |
| Validated in-scope DATA_READ still scores P2 with default caller fields | **PASS** |

## Test evidence

- Full unit: **1328 passed**, 4 skipped, 44 subtests, 0 failed.
- Full integration (real PostgreSQL, a37 applied): **187 passed**, 18 subtests, **1 failed** — same pre-existing `test_sd_g4_token_economy` CHECK. New `test_caller_admin_scope_cannot_escalate_data_read_to_p0` passed.
- Full e2e: **152 passed**, 5 skipped, **4 failed** — same pre-existing `cli_session` isolation. No new failures.

## Next

Slice 7 — exploratory execution + permanent-family promotion (lock MR-5).
