# Majority Implementation Campaign — Baseline

**Status:** Baseline snapshot before campaign implementation begins. Synthesizes the four existing audit documents (already delivered; five sub-agent investigations already incorporated — NOT re-run) plus fresh environment/git verification. No broad re-audit was performed; two previously-unresolved questions (`IMPLEMENTATION_SEQUENCE_LOCK.md` §6.1/§6.2) were spot-checked because they gate Slice 2/Slice 3 scope — see §5 below.

## 1. Branch / commit

```
Original branch:   qualification/dashboard-runtime-closure  (master + 1 commit, b2256e9)
Campaign branch:    campaign/majority-implementation  (created from the same dirty tree, non-destructively)
origin/master:      d004656 "Ignore local agent memory"
```

## 2. Initial dirty worktree (at campaign start, before any new commit)

Two independent sets of uncommitted changes coexisted in the same files:

1. **Already-completed Slice 0** (terminal-state immutability + reconciler wiring) — implemented and fully tested in the prior session. See `docs/plans/audit/SLICE_0_COMPLETION_RECORD.md`.
2. **Pre-existing, unrelated operator/dashboard work** (not authored this campaign): `PersistentBrowserWorkerAdapter` wiring, `SurfaceDiscoveryStart` seeding from the operator payload, dashboard run-control buttons (start/pause/resume/cancel) and their `/api/runs/{id}/{action}` handler, and `tests/e2e/test_dashboard_operator_controls.py` (a Playwright test of those buttons against a fake control object).

Both sets were preserved (not discarded, not rewritten). Housekeeping performed before the campaign's own work began:
- Removed a stale `.git/index.lock` (confirmed no live git process holding it).
- Added `var/live-runs/` to `.gitignore` (runtime artifact directory from a prior manual run, not source — same treatment already given to `var/benchmark-results/`).
- Fixed one broken import (`import pathsetup`) in `tests/e2e/test_dashboard_operator_controls.py` that caused a collection **error** (not a skip) for that file; no assertion/behavior was changed. This test now runs (Playwright is installed) and passes.

Both sets of changes were committed together as commit 1 of this campaign (see completion report for exact hash), since the two are interleaved in the same files and cannot be safely split by hunk without risking corruption of either.

## 3. Migration head / maturity flags (verified fresh, this session)

```
Alembic head:  a34_001_program_platforms   (single linear chain, a3..a34, confirmed via `alembic heads`)
Postgres test DB: running, matches a34 head, RESEARCH_OS_TEST_DATABASE_URL set and reachable
```

Maturity flags (`src/research_os/maturity.py`), verified unchanged from audit baseline:
`ARCHITECTURE_VALIDATED=True`, `DIAGNOSTIC_E2E_VALIDATED=True`, `LIVE_MODEL_VALIDATED=False`, `SECURITY_RESEARCH_VALIDATED=False`, `PRODUCTION_READY=False`, `GATE_04B_STATUS=PENDING`, `GATE_21_STATUS=PENDING`, `SUBSCRIPTION_OAUTH_STATUS=NOT_IMPLEMENTED`, all other listed gates `PASS` (historical/architectural scope only). This campaign does not change any of these.

## 4. Verified pre-existing features (do not rebuild)

Per `CURRENT_ARCHITECTURE_SNAPSHOT.md` / `PERSISTENT_RUNTIME_GAP_AUDIT.md`, confirmed still accurate:

- `AutonomousResearchController` is the sole production research-lifecycle authority; ARC's own path (opportunity → hypothesis → plan → execution → assessment) is fully wired and automatic.
- `execution_attempt` already has DB-unique `request_id`, and durably commits `DISPATCHING` before `WorkerPort.invoke()` — RT-1's core intent already exists at the single-attempt level. No new execution-journal table is needed.
- `ReconcileResearchRun` already implements a real crash classifier (`SAFE_TO_RETRY`, `UNKNOWN_OUTCOME`→`REQUIRE_HUMAN_REVIEW`, `MARK_OPERATIONAL_FAILURE`, `RESUME_EXISTING`, `SAFE_TO_ADVANCE`, `INTEGRITY_ERROR`); now wired into `ResearchRunControl.start()` as of Slice 0.
- Terminal-state immutability is now enforced (Slice 0, this campaign's first checkpoint).
- Lease/fencing is 100% NOT_PRESENT (exhaustive grep, confirmed) — first genuinely new schema/concept this campaign introduces (Slice 1 / Phase B).
- Hunter/Coverage/Mutation/Protocol/V3-queue/Exploratory-generator code all exist, are unit/integration tested, and are fully disconnected from ARC's production call path (Slices 3–7 / Phases D–G close this).
- Evidence/Candidate/Verification/FindingProposal submission have zero ARC/dashboard callers; only `StartHumanReview`/`RecordHumanReview`/`FinalizeFinding` are dashboard-wired (Slice 5 / Phase H closes the first hop only, by design — the human-gated tail stays manual).
- `RunResearchSelection` (`application/run_research_selection.py`) is a structurally duplicate run-lifecycle writer, reachable only from `tests/e2e/gate17_harness.py`, not production-reachable. **Flagged, not resolved by this campaign** — the audit itself recommends the operator explicitly decide its disposition (retire vs. relocate under `tests/` vs. keep as a defined non-model bounded-loop harness) before further Hunter-side work makes the disconnected pool richer. This campaign does not touch it, to avoid an unrequested architectural decision.

## 5. Spot-checks performed this session (per audit's own "unresolved question" flags, not a re-audit)

- **`IMPLEMENTATION_SEQUENCE_LOCK.md` §6.1** (is `select_research_opportunities.py`'s read path already generic?): **Verified NO.** `SelectResearchOpportunities.execute()` only reads existing `ResearchOpportunityRecord` rows to build a `previously_selected_identities` dedup set; it does not select among pre-existing *undecided* rows written by another producer. Slice 3 therefore requires a small, additive change to this file's read side (load undecided externally-sourced opportunities and feed them into the same `select_research_opportunities()` domain call), not a zero-change bridge. This does not introduce a second decision authority — one call, one decision function, both diagnostic and Hunter-sourced candidates in the same pool.
- **`IMPLEMENTATION_SEQUENCE_LOCK.md` §6.2** (`prepare_start`'s exact behavior): `prepare_start` in `dashboard.py` only verifies the `ResearchRun` row exists; it performs none of the Preflight-shaped checks (scope resolvability, budget existence, model/worker readiness). Slice 2 (Preflight) is therefore net-new aggregation, not an extension of `prepare_start`.

## 6. Campaign order (unchanged from `IMPLEMENTATION_SEQUENCE_LOCK.md` §5, mapped onto the campaign's lettered phases)

| Campaign phase | Locked slice | Status at campaign start |
|---|---|---|
| A (terminal immutability + attempt/recovery semantics) | Slice 0 | DONE (prior session) |
| B (fenced ownership) | Slice 1 | DONE this campaign (see `SLICE_1_COMPLETION_RECORD.md`; PASS criteria met, one documented residual risk — bounded, not per-write, fencing inside `AutonomousResearchController`) |
| I (Preflight) | Slice 2 | DONE this campaign (see `SLICE_2_COMPLETION_RECORD.md`; use case complete and unit-tested; live `dashboard.py` wiring explicitly deferred pending a browser-worker health-check design decision) |
| D (opportunity ingestion) | Slice 3 (MR-1) | DONE this campaign (see `SLICE_3_COMPLETION_RECORD.md`; confirms and resolves the §6.1 finding below — `RESEARCH_LIFECYCLE_RECONNECTION_AUDIT.md`'s claim that the selector "already unions arbitrary opportunity rows" was false; corrected via a small additive `opportunity_selection_candidate` bridge table rather than either mutating the pure selector or the existing `research_opportunity` table) |
| E + F (compiler + V3/mutation/protocol bridge) | Slice 4 (MR-2+MR-3) | DONE this campaign (see `SLICE_4_COMPLETION_RECORD.md`; split qualification — MR-2 PASS, mutation execution PARTIAL, V3 consumer PASS, protocol execution FAIL/deferred; no invented Worker primitives) |
| H (promotion trigger) | Slice 5 (MR-4) | Not started |
| — (epistemic hardening, same-generation fix) | Slice 6 | Not started |
| G (exploratory execution + family promotion) | Slice 7 (MR-5) | Not started |
| C (one lifecycle) | Satisfied structurally by Slices 3–5 (ARC remains sole owner; no second brain introduced) | N/A — no separate implementation slice |
| J (persistent research-osd shell) | **Not locked by any slice.** The audit explicitly deferred designing this subsystem, noting it depends on RT-A/RT-B/RT-C (now Slices 0–1) existing first, and that a daemon without a lease "would just make the race worse, not better." No schema/interface decision exists yet for `runtime_instance`, Operator API transport, or SSE. | Deferred — see completion report for rationale; will not be freelanced without an explicit design pass, consistent with "do not treat the technology stack as decided" and "tell the user first" before any new architectural component. |

No reordering was applied. Slices are implemented strictly in locked order.
