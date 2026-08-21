# Slice 0 Completion Record — Terminal-state immutability + wire the existing reconciler

Status: IMPLEMENTATION COMPLETE / QUALIFICATION PENDING (implementation-level tests only; see `IMPLEMENTATION_SEQUENCE_LOCK.md` for the distinction between this record and any formal readiness gate).

This record supersedes nothing in `CURRENT_ARCHITECTURE_SNAPSHOT.md`, `RESEARCH_LIFECYCLE_RECONNECTION_AUDIT.md`, or `PERSISTENT_RUNTIME_GAP_AUDIT.md` except the two specific findings named below, which are now closed by this implementation.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 0 — Terminal-state immutability + wire the existing reconciler". First not-yet-implemented slice in the locked ordering; no reordering occurred.

## What changed (current truth, supersedes prior audit finding)

- Runtime Gap Audit §6 ("confirmed terminal-state mutation defect"): **CLOSED.** `AutonomousResearchController._operator_state()` (the shared path for `pause()`/`cancel()`) now rejects any command against a run already in `COMPLETED`, `BUDGET_EXHAUSTED`, or `FAILED_OPERATIONAL`, persists an `ORCHESTRATION_OPERATOR_COMMAND_REJECTED` audit event, and returns the untouched record. `PostgresResearchOrchestrationRepository.save()` independently enforces the same invariant at the data boundary with a conditional `UPDATE ... WHERE state NOT IN (terminal)`, raising `TerminalOrchestrationStateError` on a no-op update — so the guarantee holds even if a future application-layer caller forgets the check.
- Runtime Gap Audit §5 ("reconciler built but unwired"): **CLOSED.** `ReconcileResearchRun` is now invoked from `ResearchRunControl.start()` (via `dashboard.py`'s production wiring) before a new `LocalRunSupervisor` attaches to a run, whenever this process has no live supervisor thread for that run id. A `MARK_OPERATIONAL_FAILURE` classification now results in a real call to the new `AutonomousResearchController.mark_operational_failure()` method, transitioning a crash-left `RUNNING` checkpoint to `FAILED_OPERATIONAL` with an audit trail, instead of being computed and discarded.

## Files changed

Production:
- `src/research_os/application/autonomous_research_controller.py` — terminal guard in `_operator_state()`; new `mark_operational_failure()`.
- `src/research_os/application/local_run_supervisor.py` — `LocalRunSupervisorRegistry.is_active()`; `LocalRunSupervisor.tick()` catches `TerminalOrchestrationStateError` from a losing race and stops supervising instead of raising.
- `src/research_os/application/research_run_control.py` — optional `reconciler` field; `_reconcile_stale_running()` called from `start()`.
- `src/research_os/data/errors.py` — new `TerminalOrchestrationStateError`.
- `src/research_os/data/records.py` — new `TERMINAL_ORCHESTRATION_STATES` (duplicated from, not imported from, `research.orchestration`, to preserve the Data→Research import boundary).
- `src/research_os/data/postgres/repositories.py` — `PostgresResearchOrchestrationRepository.save()` enforces the terminal guard at the SQL level.
- `src/research_os/interface/dashboard.py` — `ReconcileResearchRun(factory)` injected into the production `ResearchRunControl` construction (two lines; this file also carries pre-existing unrelated uncommitted operator work — surface-discovery seeding and run-control UI buttons — which predates this slice and was intentionally left untouched).

Tests:
- `tests/support/fake_unit_of_work.py` — in-memory repository mirrors the same terminal guard.
- `tests/unit/application/test_autonomous_research_controller.py` — terminal-guard rejection + audit event; repository-level rejection; `mark_operational_failure` behavior (RUNNING→FAILED_OPERATIONAL, non-RUNNING no-op).
- `tests/unit/application/test_research_run_control.py` — reconciler wiring to `mark_operational_failure` on stale `RUNNING`; no reconciliation when a live supervisor owns the run; deterministic (non-racy) pause/cancel delegation test.
- `tests/unit/application/test_local_run_supervisor.py` — `is_active()`; graceful handling of a losing race against `TerminalOrchestrationStateError` inside `tick()`.
- `tests/integration/test_orchestration_terminal_immutability.py` (new) — real PostgreSQL proof of the repository-level guard: allowed non-terminal update, rejected terminal update, no partial write on rejection.
- `tests/integration/test_gate12.py` — updated `test_pause_resume_and_cancel` assertion (cancel on an already-`COMPLETED` run must preserve `MAX_CYCLES_REACHED`, not overwrite it with `OPERATOR_CANCELLED`); added `test_cancel_actually_cancels_a_still_active_run` proving cancel still functions on a genuinely active run.

Migration: none (schema impact was `none` per the lock; confirmed no migration was required or added).

Docs: this record.

## Test evidence (see chat response for full PASS/FAIL/SKIP breakdown)

- Narrow slice tests: 41 passed, 18 subtests passed (0 failed).
- Full unit suite: 1250 passed, 4 skipped (1 pre-existing, unrelated, environment-timing-flaky test observed in 1 of 3 full-suite runs — `test_authorization_false_positives.py`, an HTTP-server-backed test untouched by this slice).
- Full integration suite (real PostgreSQL): 172+ passed, 1 pre-existing failure (`test_sd_g4_token_economy.py`, a `budget_consumption` CHECK-constraint migration defect introduced in commit `1bc89cf`, unrelated to and unmodified by this slice).
- Full e2e suite: 155 passed, 5 skipped (excluding one pre-existing broken collection target, `tests/e2e/test_dashboard_operator_controls.py`, `ModuleNotFoundError: pathsetup`, pre-existing/unrelated).
- Architecture/boundary tests: 44 passed.
- Full repository regression: 1579 passed, 9 skipped, 62 subtests passed, 1 pre-existing failure (same token-economy defect).

## Invariants proven

- Terminal orchestration states (`COMPLETED`, `BUDGET_EXHAUSTED`, `FAILED_OPERATIONAL`) cannot be overwritten by `pause()`/`cancel()`, at both the application layer (guard + audit event) and the data layer (conditional `UPDATE`), against a real PostgreSQL database.
- Rejected operator commands are audited (`ORCHESTRATION_OPERATOR_COMMAND_REJECTED`), not silently swallowed.
- A crash-left `RUNNING` checkpoint with no live process-local owner is reclassified to `FAILED_OPERATIONAL` by `ReconcileResearchRun` before a new supervisor attaches, in the actual production `ResearchRunControl.start()` path.
- `mark_operational_failure()` never falsifies a hypothesis; it only ever produces an operational-failure state (`StopReason.OPERATIONAL_FAILURE`), never a research conclusion.
- No auto-retry of `UNKNOWN_OUTCOME` was introduced; reconciliation only acts on `MARK_OPERATIONAL_FAILURE`-classified items.
- No maturity flag, gate, or readiness marker was changed.

## Unresolved / explicitly out of scope for this slice

- Cross-process lease/fencing (Slice 1) is not implemented; `is_active()` is process-local only, as documented in its own docstring.
- The pre-existing `budget_consumption` CHECK-constraint migration defect (unrelated legacy bug).
- The pre-existing broken `tests/e2e/test_dashboard_operator_controls.py` collection error (`pathsetup` module missing).
- The pre-existing uncommitted surface-discovery/dashboard-UI operator work in `dashboard.py` and `local_run_supervisor.py` (already flagged as open question #4 in `IMPLEMENTATION_SEQUENCE_LOCK.md`) — untouched, not evaluated further by this slice.

## Next locked slice

Slice 1 — Minimal lease/fencing on `research_orchestration` (`IMPLEMENTATION_SEQUENCE_LOCK.md` §5), dependent on this slice, not started.
