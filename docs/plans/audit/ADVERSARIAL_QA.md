# Adversarial QA — majority campaign (Slices 0–7)

Date: 2026-08-21. Scope: locked implementation sequence only. Not a production-readiness certificate.

## Method

Re-read lock hard-fail criteria. Re-ran full unit, full PostgreSQL integration, full E2E after Slice 7. Reviewed source of new Slice 7 paths for second-scheduler, registry-write, and Finding-gate conflation. Did not treat pre-existing failures as new defects.

## Slice-by-slice

| Slice | Lock hard-fail | Result | Residual |
|---|---|---|---|
| 0 | Silent terminal-state mutation | Prior CLOSED | None reopened |
| 1 | Unfenced concurrent writers of orchestration | Prior CLOSED | Lease is durable; process daemon still absent (Phase J) |
| 2 | Preflight default-proceed on missing auth/scope/budget | Prior CLOSED | Worker-health probe still not a Preflight check |
| 3 / MR-1 | Second scheduler; Hunter bypass of selector admission | CLOSED `e410da7` | `RunResearchSelection` remains a delegation layer; do not reintroduce independent prepare/execute |
| 4A / MR-2 | Silent SE understatement; planning alias as Worker capability | PASS `a830fa4` | Generic planner still exists for registry-external work only |
| 4B / MR-3 | Invented payloads / new Worker primitives for matrix cells | PARTIAL `714264c` | All 9 HunterFamily matrix cells remain `BLOCKED_MISSING_SEMANTICS`. Correct. Do not force PASS |
| 4C V3 | Historical approval used as execution authorization | PASS `2f76381` | — |
| 4C protocol | Fake wire semantics through `http.transaction` | FAIL/DEFERRED | Still closed. Design: `PROTOCOL_EXECUTION_CAPABILITY_DESIGN.md` |
| 5 / lock MR-4 | Auto Candidate/Verification/FindingProposal | PASS `503b237` for Evidence hop | Canonical PromotionPipeline (reconnection MR-5) still open after Evidence |
| 6 | Relax node proofs; caller P0 from DATA_READ | PASS `9f159bb` | — |
| 7 / lock “MR-5” | `may_write_hunter_registry` true by model/default; exploratory Worker dispatch outside ARC | **PASS** for plumbing + family write | Not canonical MR-5 PromotionPipeline. Not mutation/protocol execution. Not full exploratory attack capability. Actor_type is a use-case command claim, not Core `Approval` |

## Cross-cutting attacks attempted (Slice 7)

- Tamper audit `may_write_hunter_registry=true` → execute/promote fail closed; registry unchanged.
- Propose family name `OBJECT_AUTHORIZATION` at compile time → still generic `diagnostic.echo`, SE 0.
- Core DENY scope → Worker not invoked.
- Echo mismatch (negative/deceptive) → `CONTRADICTS_PREDICTION`, no Evidence, no Finding, no registry row.
- PROCESS_FAILED → no falsifying assessment.
- CONTROL_PLANE APPROVE → no `hunter_family` insert.
- Reload new use-case instance after execute → `ALREADY_ASSESSED`, registry still seed-only.
- Source inspection: execute path does not construct Prepare/Execute; does not `hunter_families.insert`. Promote path does not `run_managed_cycle` / WorkerPort / finding_proposals.

## Known non-campaign failures (do not "fix" as Slice 7)

1. `tests/integration/test_sd_g4_token_economy.py` — `ck_budget_consumption_resource_type` / `MODEL_TOKENS_IN`. Present before Slice 7. Unrelated to exploratory/family code.
2. Four E2E `cli_session` module-isolation failures when the **full** `tests/e2e` suite runs (gate14–17 `no_model` tests). Isolated, those tests pass (131/131 on gates 14–17 this run). Pre-existing.

## Remaining product gaps (not Slice 7 regressions)

- Canonical MR-5 PromotionPipeline tail: Candidate / Verification / FindingProposal still not a durable autonomous pipeline.
- Protocol execution capability still absent. Slice 7 must not be read as having opened it.
- Mutation-matrix HunterFamily cells still have no payload contract. Slice 7 must not be read as having opened it.
- Exploratory execution is diagnostic.echo plumbing for registry-external ideas, not a new attack primitive and not Phase 8 / reconnection MR-6 attack capability.
- `research-osd` absent (Phase J deferred).

## Verdict

No campaign hard-fail observed on the **narrow** Slices 0–7 lock criteria. Slice 4B remains PARTIAL. Slice 4C protocol remains FAIL/DEFERRED. Canonical PromotionPipeline, mutation/protocol execution, and full exploratory attack capability remain **open**. Majority campaign may close with those exceptions recorded, not hidden.
