# Slice 3 Completion Record — Unified opportunity source (MR-1)

Status: IMPLEMENTATION COMPLETE / QUALIFICATION PENDING.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 3 — Unified opportunity source (MR-1)" (campaign Phase D). Fourth slice implemented this campaign; depends on nothing already in place (parallelizable with Slices 1/2, already complete).

## Documented contradiction between the lock/audit doc and the actual repository — and the correction applied

`docs/plans/audit/RESEARCH_LIFECYCLE_RECONNECTION_AUDIT.md` (the source document `IMPLEMENTATION_SEQUENCE_LOCK.md` cites for MR-1) asserts that `SelectResearchOpportunities` **"already unions arbitrary opportunity rows for a run"** and only needs a producer wired in.

Code evidence that this is false, as it stood before this slice
(`src/research_os/application/select_research_opportunities.py`, pre-Slice-3):

```python
generated = propose_diagnostic_opportunities(
    command.research_run_id,
    DiagnosticOpportunitySources(...),
    id_prefix=new_opaque_id(),
)
decisions = select_research_opportunities(
    generated,
    research_run_id=command.research_run_id,
    budget=command.budget,
    negative_knowledge=tuple(negatives),
    previously_selected_identities=previously,
)
```

`select_research_opportunities()`'s **only** input was `generated` — opportunities freshly synthesized in-process from `DiagnosticOpportunitySources` (differential/invariant/chain/change-event/hypothesis ids read from the ledger). The **only** read of the persisted `research_opportunities` table was `previously = frozenset(item.structural_identity for item in uow.research_opportunities.list_for_research_run(...))`, used exclusively as a **dedup set of already-selected identities**, never as a source of additional candidate opportunities to select from. There was no code path by which a Hunter-, Coverage-, or any other externally-produced opportunity could ever reach this selector. The audit doc's claim was incorrect; repository evidence overrides it per the user's explicit instruction, without weakening any MR-1 invariant.

### Corrected design (approved by the user before implementation)

Equivalent to "Option A" from the pre-implementation review: a small, additive **opportunity-selection/candidate** table bridges non-diagnostic producers into the existing selector, instead of (a) mutating `select_research_opportunities()`'s pure decision logic, or (b) adding mutable workflow/status semantics onto the existing `research_opportunity` table.

- `research_opportunity` remains the sole canonical `ResearchOpportunity` representation. Nothing about its schema, its meaning, or who writes to it (still only `SelectResearchOpportunities`, on a `SELECT` decision) changed.
- New table `opportunity_selection_candidate` is **only** a durable pre-admission proposal/bridge, not a second `ResearchOpportunity` authority and not a second lifecycle: it has exactly one state transition, `PENDING → {ADMITTED, NOT_ADMITTED}`, decided exclusively by `SelectResearchOpportunities` itself (never by the producer, never by any other code).
- Deliberately **not** named/reused in a way that conflicts with the existing epistemic `Candidate` concept (`Evidence → Candidate → Verification → FindingProposal → Finding`, defined in `src/research_os/data/records.py`'s `CandidateRecord` and this repository's own rules doc). Chosen name: `OpportunitySelectionCandidateRecord` / table `opportunity_selection_candidate` — explicit about being an opportunity-selection candidate, not a security-finding Candidate.
- `AutonomousResearchController` (ARC) is unchanged and remains the single next-action owner and the only caller of `SelectResearchOpportunities`; it is unaware the new table exists. No second scheduler, no second Worker-dispatch path.
- The pure decision function `select_research_opportunities()` in `src/research_os/research/exploration.py` is **not modified at all** — same signature, same admission/dedup/precedence/budget logic. Only its caller's input tuple grew (diagnostics ⊕ pending candidates).
- The producer (`HunterCoverageOpportunitySource`) is isolated: it has its own file, its own command/result types, and touches only `research_run`, `research_opportunity` (read-only, for cross-producer dedup), and the new table. It never writes `Hypothesis`, `Experiment`, `ExecutionAttempt`, `Evidence`, or `Candidate` state, and never calls `WorkerPort`.

## What changed

Producer (new, isolated):

- `src/research_os/application/hunter_coverage_opportunity_source.py` (new) — `HunterCoverageOpportunitySource`. Consumes an **already-computed** `tuple[ScoredCell, ...]` (e.g. `RunHuntSchedulerResult.recommended`, which itself wraps `compute_coverage_debt()` + `schedule_cells()`; neither is called again here, so this producer cannot drift from or duplicate that decision logic). For each cell whose `CoverageState` is `UNTESTED` or `HYPOTHESIZED` (cells already `V1_PASSED`/`V2_PASSED`/`V3_QUEUED`/`COVERED`/`NOT_APPLICABLE` have their own existing follow-up path — V1–V3 tier progression in `RunHuntCycle`, or a `HYPOTHESIS_FOLLOWUP` diagnostic opportunity once assessed — and are explicitly skipped here to avoid a second path for the same work), builds one deterministic `OpportunitySelectionCandidateRecord` (dimensions are ordinal, never a raw `HunterScore`/priority number, matching the existing "not a priority score" invariant in `research.exploration`) and inserts it if its `structural_identity` is not already present as a candidate or a canonical opportunity for that run (own dedup, so a coverage gap that persists across cycles is proposed exactly once, not once per cycle). Proposing a candidate never mutates coverage state itself — coverage is still reduced only by executed/admitted research results, exactly as required.

Selector (existing use case, minimal additive read-side change):

- `src/research_os/application/select_research_opportunities.py` — `SelectResearchOpportunities.execute()` now also loads still-`PENDING` `opportunity_selection_candidate` rows for the run, converts each into the same domain `ResearchOpportunity` value object diagnostics use (`_opportunity_from_candidate`, using the candidate's own `candidate_id` as a stable `opportunity_id`), and passes `generated + candidate_opportunities` into the **unmodified** `select_research_opportunities()`. Diagnostics are listed first in that tuple, so they retain first claim on shared budget/exploration slots exactly as before this change; Hunter/Coverage candidates only fill remaining capacity — this was a deliberate precedence choice, not an accident, and is called out explicitly here for review. After a decision, only outcomes that cannot change on a later cycle retire a candidate: `SELECT → ADMITTED` (with `resulting_opportunity_id` set to the same id, since the canonical `ResearchOpportunityRecord` was inserted with `opportunity_id = candidate_id`), `SKIP_DUPLICATE`/`BLOCKED_POLICY → NOT_ADMITTED`. Capacity/context-dependent outcomes (`DEFER`, `BLOCKED_BUDGET`, `SKIP_LOW_INFORMATION`, `NEEDS_MORE_CONTEXT`) leave the candidate `PENDING` so a still-relevant gap is reconsidered on a later cycle instead of being permanently discarded because this cycle's budget happened to be full.

Domain (additive):

- `src/research_os/research/exploration.py` — added `OpportunityKind.HUNTER_COVERAGE_GAP` (new enum member; nothing renamed) and `dimensions_from_mapping()` (exact inverse of the existing `OpportunityDimensions.to_mapping()`, used to round-trip a candidate's persisted dimensions back into a real, validated `OpportunityDimensions` instead of duplicating its validation).

Data (additive-only; no existing table/column changed):

- `src/research_os/data/records.py` — new `OpportunitySelectionCandidateRecord` (own validation, same rigor as `ResearchOpportunityRecord`: opaque ids, forbidden-key rejection, no priority score, and additionally a state-machine check — `PENDING` cannot carry `resulting_opportunity_id`/`decided_at`; `ADMITTED` must carry `resulting_opportunity_id`; `NOT_ADMITTED` must not). Added `"HUNTER_COVERAGE_GAP"` to `ALLOWED_OPPORTUNITY_KINDS` (required for a `SELECT` decision on a Hunter-sourced opportunity to pass `ResearchOpportunityRecord` validation). Incidentally also added the pre-existing-but-never-allow-listed `"SURFACE_DISCOVERY"` kind (declared in `research.exploration.OpportunityKind` since before this slice but never reachable — confirmed unused anywhere in the codebase — added here only because this exact allow-list was already being touched; not otherwise in scope).
- `src/research_os/data/ports.py`, `src/research_os/data/unit_of_work.py` — new `OpportunitySelectionCandidateRepository` protocol (`insert`, `get`, `list_for_research_run`, `mark_decided`) and `UnitOfWork.opportunity_selection_candidates` field.
- `src/research_os/data/postgres/tables.py` — new `opportunity_selection_candidate` table (JSONB payload columns mirroring `research_opportunity`'s; `CheckConstraint`s on `source_system` (closed to `'HUNTER_COVERAGE'` today — a future second producer must be added explicitly, not silently accepted), `mode`, `outcome`; `UniqueConstraint(research_run_id, structural_identity)` mirroring `research_opportunity`'s own uniqueness). Added to `SPINE_TABLES`. **Not** added to `APPEND_ONLY_TABLES` — unlike `research_opportunity`/`research_selection`, a candidate row receives exactly one guarded `UPDATE` (`mark_decided`), so it is not append-only.
- `src/research_os/data/postgres/mapping.py`, `src/research_os/data/postgres/repositories.py` (`PostgresOpportunitySelectionCandidateRepository`), `src/research_os/data/postgres/unit_of_work.py` — standard row-mapping/repository/wiring, following the exact pattern of `PostgresResearchOpportunityRepository`. `mark_decided()` is a CAS (`UPDATE ... WHERE candidate_id = :id AND outcome = 'PENDING'`), returning whether it actually transitioned a row, so a retried/duplicate call after a crash is a safe no-op rather than a silent overwrite of the first decision.
- `alembic/versions/a36_001_opportunity_candidate.py` (new, additive-only; `CREATE TABLE`, no `ALTER`/`DROP` on any existing table). New head: `a36_001_opportunity_candidate` (was `a35_001_orchestration_lease`).
- `tests/support/fake_unit_of_work.py` — in-memory fake repository mirroring the same dedup-on-insert and CAS-on-`mark_decided` semantics, for unit tests.

Tests (new):

- `tests/unit/application/test_hunter_coverage_opportunity_source.py` (9 tests) — eligible/ineligible coverage states, no-duplicate-across-reruns, no-duplicate-against-an-already-canonical-opportunity, `max_candidates` bound, invalid input, missing research run, and an explicit assertion that this producer never touches `Hypothesis`/`Experiment`/`ExecutionAttempt`/`Evidence`/`Candidate`/`Finding` state.
- `tests/unit/application/test_opportunity_candidate_bridge.py` (7 tests) — a `PENDING` candidate is selected and transitions to `ADMITTED` with a canonical `ResearchOpportunityRecord` created (**and** an explicit assertion of zero `execution_attempts`/`worker_results`, i.e. no alternative Worker dispatch path); zero-candidates-present is a byte-for-byte regression guard against the pre-Slice-3 diagnostic-only path; a candidate duplicating an already-canonical opportunity is marked `NOT_ADMITTED`; a candidate deferred purely for budget-capacity reasons stays `PENDING` (retryable) while a `BLOCKED_POLICY` (side-effect level 3) candidate is `NOT_ADMITTED` (terminal); a candidate belonging to a different `research_run_id` is never loaded; an already-decided candidate is never reconsidered.
- `tests/integration/test_opportunity_selection_candidate.py` (6 tests, real PostgreSQL, skips cleanly to `PENDING` without `RESEARCH_OS_TEST_DATABASE_URL`) — insert/get round trip, run-scoped listing, the real unique-constraint rejection (`PersistenceConflictError`) for a duplicate `structural_identity` in the same run, `mark_decided` as a real CAS (second call is a no-op, first result wins), and record-level rejection of an invalid `source_system`/inconsistent outcome state before ever reaching the database.
- `tests/unit/data/test_alembic_smoke.py` — extended `SPINE_TABLES` expectation with the new table name; added `test_a35_migration_adds_orchestration_lease` (a gap from Slice 1 — that migration had no smoke-test coverage until now) and `test_a36_migration_adds_opportunity_selection_candidate`.
- All hardcoded `"a35_001_orchestration_lease"` alembic-head assertions across `tests/integration/test_gate*.py`, `test_postgres_spine.py`, `test_endurance.py`, `test_gate22_discovery_persistence.py`, and `tests/e2e/test_gate14-17*.py` bumped to the new head `"a36_001_opportunity_candidate"` (mechanical; same pattern as the Slice 1 head bump).

## Test evidence

- New Slice 3 unit + integration tests: 22/22 passed, repeated 3x with no flakes.
- Full unit suite: 1293 passed (1275 + 18 new), 4 skipped, 0 failed.
- Full integration suite (real PostgreSQL): 186 passed, 18 subtests passed, 1 failed — the same pre-existing `test_sd_g4_token_economy.py::test_cheap_call_records_tokens_and_deny_when_limit_reached` failure recorded at every prior slice (`budget_consumption` CHECK-constraint migration defect, unrelated to opportunity selection). No new failures.
- Full e2e suite: 152 passed, 5 skipped, 4 failed — all 4 confirmed **pre-existing** by direct experiment: `git stash` (reverting every Slice-3 code change) still reproduces the identical 4 failures (`test_gate14…test_20_no_codex_or_model_runtime_and_maturity_unchanged`, `test_gate15…test_18_no_codex_model_or_strix_invoked`, `test_gate16…test_30_no_model_or_codex_invocation`, `test_gate17…test_48_no_model_runtime`), each asserting `result.model_modules_loaded == ()` but observing `('research_os.integrations.models.cli_session',)` — a test-isolation/module-caching artifact of running the full e2e suite in one interpreter process, unrelated to Slice 3, present before this slice. No new e2e failures.
- Architecture/boundary tests (`tests/unit/test_architecture_boundaries.py`): 26 passed, unchanged from Slice 2.

## Invariants proven

- `research_opportunity` remains the single canonical `ResearchOpportunity` representation; `opportunity_selection_candidate` never becomes a second authority (proven by: the only writer of `research_opportunity` is still `SelectResearchOpportunities.execute()`'s existing `SELECT`-branch insert, unchanged; the candidate table has no reader anywhere else in the codebase).
- Hunter/Coverage-sourced opportunities and diagnostic opportunities converge into the exact same admission/dedup/precedence pure function and the exact same `ResearchOpportunityRecord`/`ResearchSelectionRecord` persistence path — proven by `test_pending_candidate_is_selected_and_admitted` (a `HUNTER_COVERAGE_GAP` candidate produces a `research_opportunity` row indistinguishable in shape from a diagnostic one) and by the zero-candidates regression guard (diagnostic-only behavior is unchanged when no candidates exist).
- No alternative Worker dispatch path exists for Hunter/Coverage opportunities: `test_pending_candidate_is_selected_and_admitted` and `test_no_worker_execution_or_authorization_side_effects` assert zero `execution_attempts`/`worker_results`/`hypotheses`/`experiments`/`evidence`/`candidates`/`findings` after running the producer and the selector; `AutonomousResearchController` is the only caller of `SelectResearchOpportunities` and is unmodified, so it remains the sole path from a selected opportunity into `Hypothesis`/`ExperimentIntent`/Core/Worker.
- Planning/proposing a candidate is not coverage reduction: the producer never writes to `hunter_family`/`coverage_debt_snapshot`/any hypothesis/assessment table; it only reads `ScoredCell`s already computed elsewhere and writes a `PENDING` proposal row.
- Ambiguity fails closed: an invalid `source_system`, a `PENDING` candidate carrying a `resulting_opportunity_id`, an `ADMITTED` candidate missing one, or an out-of-enum `opportunity_kind`/`mode`/`outcome` are all rejected by `OpportunitySelectionCandidateRecord.__post_init__` before ever reaching PostgreSQL (and, redundantly, by real `CheckConstraint`s in the database).
- A decided candidate is never reconsidered or overwritten (`mark_decided` is a genuine CAS, proven against real PostgreSQL: a second `mark_decided` call after the first succeeds returns `False` and does not change the row).
- A capacity/context-only non-selection (`DEFER`/`BLOCKED_BUDGET`/`SKIP_LOW_INFORMATION`/`NEEDS_MORE_CONTEXT`) does not permanently discard an otherwise-valid opportunity — it remains `PENDING`.

## Unresolved / explicitly out of scope for this slice

- `HunterCoverageOpportunitySource` is not yet wired into any scheduled/periodic caller (e.g. `AutonomousResearchController`'s own cycle loop, or an operator-triggered hunt step). It exists as a complete, tested, standalone use case that a future integration point can call with `RunHuntSchedulerResult.recommended`; wiring that call site is Hunter-lifecycle integration work, not part of MR-1's schema/selector bridge, and was not requested as part of this slice's scope.
- `RunResearchSelection` (`src/research_os/application/run_research_selection.py`) was discovered during this slice's survey to be a **second, independent selection loop** — it owns its own `ResearchOrchestrationRecord` mutation and writes `ResearchOpportunityRecord`/`ResearchSelectionRecord` via its own `ExperimentOption`-based generation path (`research.selection`), entirely separate from `AutonomousResearchController`'s `SelectResearchOpportunities` call. This is the "two independent schedulers" anti-pattern campaign Phase C explicitly warns against. It is **not** touched by this slice (out of scope for MR-1; `IMPLEMENTATION_SEQUENCE_LOCK.md`'s locked slice list does not include a Phase-C unification slice) but is flagged here as a real, pre-existing architectural risk for a future phase.
- The pre-existing `budget_consumption` CHECK-constraint migration defect (unrelated legacy bug, flagged at every prior slice).
- The pre-existing `cli_session` model-module-loaded e2e test-isolation artifact (flagged above; unrelated to opportunity selection).

## Next locked slice

Slice 4 — deterministic `ExperimentCompiler` registry + V3/Mutation/Protocol dispatch bridge (MR-2+MR-3) (`IMPLEMENTATION_SEQUENCE_LOCK.md` §5 / campaign Phases E+F), not started.
