# Majority campaign completion report

Date: 2026-08-21.
Branch at Slice 7 close: `campaign/majority-implementation`.
This report is not `PRODUCTION_READY`, not `SECURITY_RESEARCH_VALIDATED`, and not a live-model certificate.

## Campaign claim

The locked sequence in `IMPLEMENTATION_SEQUENCE_LOCK.md` (Slices 0–7, with Phase J explicitly out of sequence) is implemented far enough to reconnect ARC-facing research lifecycle pieces that the reconnection audit found disconnected, without creating a second lifecycle owner, without promoting Candidates to Findings, and without inventing Worker primitives.

This campaign does **not** close canonical Hunter-reconnection **MR-5 PromotionPipeline** (Assessment→…→FindingProposal), does **not** close mutation/protocol execution, and does **not** constitute full exploratory attack capability. Slice 7 is only exploratory execution plumbing plus human-gated family registry write.

## Slice ledger

| Slice | Lock id | Qualification | Commit / record |
|---|---|---|---|
| 0 | Hygiene / baseline | CLOSED with campaign baseline | checkpoint 1 |
| 1 | Lease/fencing | CLOSED | Slice 1 record |
| 2 | Preflight | CLOSED | Slice 2 record |
| 3 | MR-1 unified opportunity | CLOSED | `e410da7` — `SLICE_3_COMPLETION_RECORD.md` |
| 4A | MR-2 compiler registry | PASS | `a830fa4` — `SLICE_4_COMPLETION_RECORD.md` |
| 4B | MR-3 mutation/protocol compile | PARTIAL | `714264c` — same; 9 matrix cells `BLOCKED_MISSING_SEMANTICS` |
| 4C V3 consumer | V3 dispatch | PASS | `2f76381` |
| 4C protocol execution | wire semantics | FAIL/DEFERRED | `PROTOCOL_EXECUTION_CAPABILITY_DESIGN.md` |
| 5 | lock MR-4 promotion trigger | PASS for **Evidence hop only** | `503b237` — `SLICE_5_COMPLETION_RECORD.md`. Not canonical MR-5 PromotionPipeline |
| 6 | Epistemic (edge proof + severity bound) | PASS | `9f159bb` — `SLICE_6_COMPLETION_RECORD.md` |
| 7 | lock “MR-5” exploratory plumbing + family write | **SLICE_QUALIFIED / PASS** for that narrow path | `SLICE_7_COMPLETION_RECORD.md`. Not canonical MR-5, not attack capability |
| J | `research-osd` | **DEFERRED** | `PHASE_J_DEFERRED.md` |

## Invariants held

- ARC is the sole semantic/next-action owner of `research_orchestration`.
- Worker dispatch stays behind Core authorization.
- Observation ≠ Hypothesis ≠ Evidence ≠ Finding.
- Candidate VALIDATED ≠ Finding. FindingProposal ≠ Finding.
- Model output is not Evidence. WorkerResult is not Evidence.
- Historical human approval is not an execution token (Slice 4C V3).
- Exploratory drafts cannot write `hunter_family`; promotion requires HUMAN_OPERATOR APPROVE (Slice 7).
- ImpactGraph edges require resolvable proof_refs (Slice 6).
- Caller ADMIN/BULK_SENSITIVE cannot raise DATA_READ above P2 (Slice 6).

## Final test evidence (post-Slice 7)

- Unit: **1344 passed**, 4 skipped, 44 subtests, 0 failed.
- Integration / real PostgreSQL (`RESEARCH_OS_TEST_DATABASE_URL=postgresql+psycopg://research_os_test@127.0.0.1:55432/research_os_test`): **189 passed**, 18 subtests, **1 failed** (pre-existing token-economy CHECK).
- E2E: **152 passed**, 5 skipped, **4 failed** (pre-existing `cli_session` isolation on full-suite gate14–17). Isolated gates 14–17: **131 passed**.

Pre-existing failures were not reclassified as Slice 7 defects and were not patched to fake PASS.

## Explicitly unfinished (honest remainder)

1. **Canonical MR-5 PromotionPipeline** (`RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md` §10 / reconnection MR-5): Assessment→Evidence exists (Slice 5); Candidate → Independent Verification → FindingProposal → HumanReview → Finding is still not a durable autonomous pipeline.
2. Protocol-level execution capability (smuggling/desync, cache) — design exists; current HTTP primitive must not impersonate it. Slice 7 did not open this.
3. Mutation-matrix cell payload contracts — 9 families stay blocked. Slice 7 did not open this.
4. **Full exploratory attack capability** — Slice 7 is diagnostic.echo plumbing for a registry-external hypothesis, not family-shaped discriminating experiments or exploratory verification/finding.
5. Persistent `research-osd` — Phase J deferred; needs a design pass.
6. Live model GATE_04B — still PENDING in `maturity.py`.
7. Token-economy CHECK vs `MODEL_TOKENS_IN` integration failure — pre-existing, still open.
8. Full-suite E2E `cli_session` isolation — pre-existing, still open.

## Adversarial QA

See `docs/plans/audit/ADVERSARIAL_QA.md`. No locked hard-fail was observed. PARTIAL/DEFERRED items remain labeled as such.

## Operator next

1. Commit Slice 7 + these audit docs if the operator wants a checkpoint (not done automatically).
2. Do not start Phase J code without an explicit design request.
3. Canonical PromotionPipeline tail, protocol execution, mutation payload contracts, and real exploratory attack capability remain open research-capability gaps. Do not treat Slice 7 PASS as closing them.
