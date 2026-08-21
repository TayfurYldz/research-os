# Slice 1 Completion Record — Minimal lease/fencing on `research_orchestration`

Status: IMPLEMENTATION COMPLETE / QUALIFICATION PENDING (implementation-level tests only). Supersedes `IMPLEMENTATION_SEQUENCE_LOCK.md` §5 Slice 1's "NOT_PRESENT" status and Runtime Gap Audit §3/§7 ("stale runtime owner cannot mutate run" — was NOT_PRESENT).

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 1 — Minimal lease/fencing on `research_orchestration`". Second slice in the locked ordering; no reordering occurred. Depended on Slice 0 (terminal-state guard), which is complete.

## What changed

- Runtime Gap Audit §3/§7 ("confirmed concurrent-attach gap" / "stale runtime owner cannot mutate run — NOT_PRESENT"): **CLOSED for the locked PASS criteria** ("two simulated concurrent attachers produce exactly one active owner; a stale lease is legitimately superseded"). Ownership of a `research_orchestration` row is now a CAS + monotonically increasing `lease_epoch` (not a distributed lock), anchored to PostgreSQL's clock (`_server_now`), not the application host's.
- `research_orchestration` gained three additive, nullable/defaulted columns: `owner_runtime_instance_id`, `lease_epoch` (default `0`, meaning "never leased"), `lease_expires_at`. No existing column changed. Migration `a35_001_orchestration_lease` is purely additive and has a symmetric downgrade.
- New atomic repository operations: `acquire_lease` (CAS: only non-terminal, only unowned-or-expired-or-same-owner, increments epoch), `renew_lease` (CAS: owner+epoch must match, extends TTL), `release_lease` (CAS: owner+epoch must match, clears ownership). All three return/report a typed outcome (`LeaseAcquireOutcome`) rather than raising for the expected "someone else holds it" case.
- `PostgresResearchOrchestrationRepository.save()` gained optional fencing parameters (`expect_owner_runtime_instance_id`, `expect_lease_epoch`, `require_unowned_or_expired`); a fenced call whose expectation no longer matches the persisted row raises `LeaseFencingError` ("0 rows affected = ownership lost") instead of silently succeeding or silently no-oping.
- `LocalRunSupervisorRegistry` now acquires a lease before attaching a supervisor to a run (`start()` returns `None`, not an error, if the lease is held live elsewheree or the run is terminal — "no lease" is an expected outcome, not a fault). `LocalRunSupervisor` renews its lease on a configurable heartbeat (`LeaseConfig`, default 30s heartbeat / 90s TTL) and immediately stops ticking — no further `controller.step()` calls — the first time a renewal is rejected.
- `AutonomousResearchController.mark_operational_failure()` (the reconciliation write path, Slice 0) now passes `require_unowned_or_expired=True`, so reconciliation can never override a run that a live owner is actually still ticking; `ResearchRunControl._reconcile_stale_running()` treats the resulting `LeaseFencingError` as "not actually stale, just unsupervised by me" rather than propagating it.

## Files changed

Production:
- `alembic/versions/a35_001_orchestration_lease.py` (new) — additive migration for the three lease columns + `lease_epoch >= 0` check constraint.
- `src/research_os/data/records.py` — `ResearchOrchestrationRecord` extended with the three lease fields; new `LeaseAcquireOutcome` enum and `LeaseAcquireResult` dataclass.
- `src/research_os/data/postgres/tables.py` — three new columns + check constraint on `research_orchestration`.
- `src/research_os/data/postgres/mapping.py` — `research_orchestration_from_row` maps the three new columns.
- `src/research_os/data/postgres/repositories.py` — `PostgresResearchOrchestrationRepository.save()` fencing parameters; new `acquire_lease`/`renew_lease`/`release_lease`; new `_server_now` helper (PostgreSQL-clock anchored).
- `src/research_os/data/ports.py` — `ResearchOrchestrationRepository` protocol extended to match.
- `src/research_os/data/errors.py` — new `LeaseFencingError`.
- `src/research_os/application/orchestration_lease.py` (new) — `LeaseConfig` (configurable `heartbeat_interval_seconds` / `lease_ttl_seconds`; not a magic constant).
- `src/research_os/application/local_run_supervisor.py` — `LocalRunSupervisor` gains lease-aware fields, heartbeat renewal in `tick()`, best-effort release on graceful stop; `LocalRunSupervisorRegistry` gains a process identity (`owner_runtime_instance_id`) and acquires a lease in `start()`.
- `src/research_os/application/research_run_control.py` — `_reconcile_stale_running()` treats `LeaseFencingError` from `mark_operational_failure()` as a no-op, not a fault.
- `src/research_os/application/autonomous_research_controller.py` — `mark_operational_failure()` calls `save(..., require_unowned_or_expired=True)`.

Tests:
- `tests/support/fake_unit_of_work.py` — in-memory repository mirrors `save()` fencing and adds `acquire_lease`/`renew_lease`/`release_lease`.
- `tests/integration/test_orchestration_lease.py` (new, 8 tests, real PostgreSQL) — fresh acquire; second owner cannot steal a live lease; same-owner re-acquire is idempotent and bumps epoch; expired lease taken over at next epoch; a stale owner's `renew_lease` **and** fenced `save()` are both rejected once superseded (while the new owner's checkpoint still succeeds); **two real threads racing an expired lease produce exactly one `ACQUIRED` and one `DENIED_HELD_BY_OTHER`**; a terminal run returns `DENIED_TERMINAL` and can never be leased; `release_lease` requires both matching owner and matching epoch, and a released run is immediately re-acquirable.
- 14 pre-existing tests across `tests/integration/**` and `tests/e2e/**` that assert the literal current Alembic head (`self.assertEqual(version, "a34_001_program_platforms")`) updated to `"a35_001_orchestration_lease"` — a required, mechanical consequence of adding any new migration, not a behavior change.

## Test evidence

- New lease-fencing integration tests (real PostgreSQL): 8/8 passed, repeated 3x with no flakes (includes one genuine two-thread concurrency race per run).
- Full unit suite: 1250 passed, 4 skipped, 0 failed.
- Full integration suite (real PostgreSQL): 180 passed, 18 subtests passed, **1 pre-existing failure** — `tests/integration/test_sd_g4_token_economy.py::test_cheap_call_records_tokens_and_deny_when_limit_reached`, the same `budget_consumption` CHECK-constraint migration defect already recorded as pre-existing/unrelated in `SLICE_0_COMPLETION_RECORD.md` (migration `a28_001_token_economy` added `ck_budget_consumption_resource_type_v2` but never dropped the now-narrower `ck_budget_consumption_resource_type` from `a16_001_orchestration_operations`; both constraints are simultaneously active, and the older one rejects `MODEL_TOKENS_IN`). Not touched by this slice; not fixed by this slice; classified `PRE_EXISTING_CONFIRMED`.
- Architecture/boundary tests: 26 passed.

## Invariants proven

- `acquire_lease` is atomic and race-safe under genuine concurrent PostgreSQL connections: exactly one of two simultaneous contenders for an expired lease wins; the other observes `DENIED_HELD_BY_OTHER`.
- A live lease cannot be acquired by a different owner (`DENIED_HELD_BY_OTHER`), only renewed/released by its current owner.
- A terminal `research_orchestration` row can never be leased (`DENIED_TERMINAL`), consistent with Slice 0's terminal-state immutability.
- Once an epoch is superseded, the old owner's `renew_lease` fails and its fenced `save()` raises `LeaseFencingError` rather than silently landing — the new owner's own checkpoint is unaffected.
- Lease-expiration comparisons are anchored to PostgreSQL's clock (`_server_now`), not the application host's, so runtime-instance clock skew cannot itself cause an incorrect acquire/expire decision.
- Reconciliation (Slice 0's `mark_operational_failure`) cannot override a run whose lease is currently live and held by another runtime instance.
- No maturity flag, gate, or readiness marker was changed. No second lock/consensus mechanism was introduced (no advisory locks, no Redis, no Kafka).

## Known limitation — read before treating Phase B as fully closed

The mega-campaign brief's Phase B language ("EVERY AUTHORITATIVE ORCHESTRATION MUTATION after ownership is established must be conditional on ... expected lease_epoch") is **stricter** than what is implemented here, and stricter than the locked Slice 1 PASS criteria in `IMPLEMENTATION_SEQUENCE_LOCK.md` (which this same audit process deliberately scoped down to "two simulated concurrent attachers produce exactly one active owner; a stale lease is legitimately superseded").

What is actually implemented is a **heartbeat-bounded CAS lease**, not per-write epoch fencing on every internal `AutonomousResearchController` checkpoint:
- `LocalRunSupervisor` renews its lease once per `heartbeat_interval_seconds` (default 30s) and stops ticking immediately — no further `controller.step()` calls — the first time renewal is rejected.
- The individual `uow.research_orchestrations.save(...)` calls made *inside* `AutonomousResearchController.step()` (roughly a dozen call sites across cycle/experiment/observation bookkeeping) are **not themselves** each conditioned on the caller's `owner_runtime_instance_id`/`lease_epoch`. Only `mark_operational_failure()` (the reconciliation path) uses fencing today.
- Consequence: if runtime instance A is superseded by B mid-tick (inside a single `step()` call, between two heartbeat renewals), A's in-flight tick can still complete and its writes can still land, bounded by at most `heartbeat_interval_seconds` of staleness — not zero.
- This was a deliberate, previously-made design decision (see prior-session notes): threading `(owner_runtime_instance_id, lease_epoch)` through every `save()` call site inside the ~1,175-line `AutonomousResearchController` would be a materially larger, higher-risk refactor of the sole research-lifecycle authority file, which the repo's own rules require surfacing to the user before doing rather than doing silently.
- Practical mitigation already in place: `LocalRunSupervisorRegistry.start()` refuses to attach a second local supervisor while a lease is live elsewhere, and `_release_lease_best_effort()` releases promptly on graceful stop — so the window only matters on ungraceful process death, and only for up to one heartbeat interval, which is itself operator-configurable (`LeaseConfig`).

This is flagged here explicitly rather than silently claimed as fully closed. Whether to invest in full per-write epoch fencing inside `AutonomousResearchController` (and, if so, how — e.g. injecting a fenced `UnitOfWorkFactory` decorator vs. threading explicit parameters) is an open architectural decision that should be made explicitly, not assumed, before Slice 4/5 (daemon extraction) makes multi-process contention routine rather than rare.

## Unresolved / explicitly out of scope for this slice

- Full per-write epoch fencing inside `AutonomousResearchController.step()` — see "Known limitation" above.
- The pre-existing `budget_consumption` CHECK-constraint migration defect (unrelated legacy bug, same one flagged at Slice 0).
- research-osd (Slice/Phase J) still not started; still correctly deferred per `CAMPAIGN_BASELINE.md`.

## Next locked slice

Slice 2 — Preflight use case (`IMPLEMENTATION_SEQUENCE_LOCK.md` §5 / campaign Phase I), parallelizable with Slice 1, not started.
