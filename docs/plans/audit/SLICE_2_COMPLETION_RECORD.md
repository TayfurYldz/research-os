# Slice 2 Completion Record — Preflight aggregation

Status: IMPLEMENTATION COMPLETE (standalone use case, fully unit-tested) / PRODUCTION WIRING DEFERRED (explicit, disclosed decision — see "Known limitation" below) / QUALIFICATION PENDING.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 2 — Preflight aggregation" (campaign Phase I). Third slice implemented this campaign; dependencies: none (parallelizable with Slice 1, which was already complete).

## What changed

- Runtime Gap Audit §8/§10 ("fragmented per-attempt-only checks, no unified go/no-go"): **CLOSED at the use-case level.** `Preflight` aggregates authorization, scope, budget, orchestration-recoverability, lease-conflict, database/schema, worker, and model readiness into one `PreflightReport` with a single `READY_TO_START` / `NOT_READY` status and per-check reasons.
- No new table. No new persistence entity. Exactly as scoped ("Schema impact: none").
- Ambiguous/missing input fails closed everywhere: a missing authorization source, an unreachable database, a `None` model candidate, a missing issued budget, etc. all resolve to `NOT_READY`, never to a silent default-proceed. `Preflight` never authorizes anything itself; `start()` and every Worker dispatch still perform their own independent Core authorization exactly as before.

## Files changed

Production:
- `src/research_os/application/preflight.py` (new) — the aggregator: `Preflight`, `PreflightCommand`, `PreflightReport`, `PreflightCheckResult`, `PreflightCheckName`, `PreflightStatus`, plus the caller-supplied freshness-carrying input types `SchemaHealthInput`, `WorkerReadinessInput`, `ModelReadinessInput`. Reuses, without modification: `check_authorization`, `check_scope`/`evaluate_scope_candidate`, `check_budget`, `load_program_research_context`, `normalize_url`, `ReconcileResearchRun`, `TERMINAL_ORCHESTRATION_STATES`, `ledger_totals`, the Slice 1 lease fields, and `platform.health.{ComponentHealth, HealthCheck}` (which already has a `RATE_LIMITED` state, so "model rate-limited" and "worker unavailable" reuse an existing type rather than inventing a new one).
- `src/research_os/data/postgres/engine.py` — new `check_schema_head(engine, alembic_ini_path)` helper (Alembic-revision-vs-database comparison; Postgres/Alembic-specific, so it lives in the Postgres data adapter, not in the application-layer aggregator).

Tests:
- `tests/unit/application/test_preflight.py` (new, 25 tests) — every individual check's PASS and NOT_READY path, plus: unreachable database short-circuits to a single `DATABASE_REACHABLE=False` check (not a crash, not a partial report); a missing research run still runs and reports the checks that do not depend on it (schema/worker/model) rather than silently omitting them; `reasons`/`is_ready` report helpers.

Migration: none.

Docs: this record.

## Test evidence

- New Preflight unit tests: 25/25 passed, repeated 3x with no flakes.
- Full unit suite: 1275 passed (1250 + 25 new), 4 skipped, 0 failed.
- Full integration suite (real PostgreSQL): 180 passed, 18 subtests passed, same single pre-existing `test_sd_g4_token_economy.py` failure already recorded at Slice 0/Slice 1 (unrelated `budget_consumption` CHECK-constraint migration defect); no new failures.
- Architecture/boundary tests: 26 passed.
- `check_schema_head()` smoke-tested directly against the real test database (`database='a35_001_orchestration_lease' expected='a35_001_orchestration_lease'` → `True`).

## Invariants proven

- A missing or inactive `AuthorizationSource`, or one outside its `effective_from`/`effective_until` window (a temporal check that existed as persisted data but was **never evaluated anywhere at runtime** before this slice — confirmed by the read-only survey preceding implementation), denies with a specific reason.
- A target that does not normalize, or normalizes but is not explicitly allowed by any compiled scope rule, denies — `SCOPE_COMPILES` and `TARGET_IN_SCOPE` are reported as two independent checks so a caller can tell "no rules configured" apart from "rules configured but this target isn't in them."
- A missing or exhausted issued budget denies, reusing the exact same `check_budget`/`ledger_totals` Core logic already authoritative at dispatch time (Preflight does not invent a second budget-accounting algorithm).
- An orchestration checkpoint already in a terminal state (Slice 0) denies with "cannot be restarted"; a live reconciliation blocker (`UNKNOWN_OUTCOME`, `REQUIRE_HUMAN_REVIEW`, `INTEGRITY_ERROR` from `ReconcileResearchRun`, Slice 0's own classifier) denies.
- A lease (Slice 1) held live by a different runtime instance denies; the same lease held by the requesting instance, or already expired, does not — explicitly documented as an advisory pre-check only, since the authoritative decision remains `acquire_lease()`'s own PostgreSQL-clock-anchored CAS at actual attach time.
- Worker/model checks consume already-computed `HealthCheck`/`RuntimeCandidate` values (never perform their own network call), and correctly deny on every required scenario from the campaign brief's QA checklist: worker unavailable, missing required capability, no model candidate, model not authenticated, model rate-limited (`ComponentHealth.RATE_LIMITED`), model not structured-output compatible.
- A database read failure during Preflight itself denies with exactly one check (`DATABASE_REACHABLE=False`) rather than fabricating results for checks that never ran.
- No maturity flag, gate, or readiness marker was changed.

## Known limitation — read before treating Phase I as fully closed

**`Preflight` is implemented, correct, and fully unit-tested, but it is not yet wired into the live `dashboard.py` production path.** This is a deliberate, disclosed decision, not an oversight:

- `research_run_control.py` already has exactly the extension point the lock doc anticipated (`prepare_start: Callable[[str], None] | None`, called first inside `start()`), so wiring `Preflight` in would require **zero changes** to `research_run_control.py` itself — only a richer `prepare_start` closure in `dashboard.py`.
- Building that closure requires fresh, real values for `WorkerReadinessInput` and `ModelReadinessInput` on every `start()` call. Investigating this surfaced a real gap: the dashboard's actual production Worker is `PersistentBrowserWorkerAdapter` (a supervised, Chromium-launching subprocess), which has **no lightweight health-check method** — the only way to "probe" it for real is `invoke()`, which spawns a real contained browser process. `platform.worker_health.probe_local_python_worker()` (the only existing worker health probe) targets a *different* adapter (`LocalProcessWorkerAdapter`) and would silently check the wrong thing if reused here.
- Deciding what "worker runtime healthy" should even mean for a persistent browser worker on every `start()` call (spin up a real browser as a precondition of starting research? add a new lightweight liveness signal to the adapter? treat "not yet started" as healthy-by-default?) is an actual architectural decision about an area of `dashboard.py`/`persistent_browser_worker.py` that the campaign baseline already flagged as containing pre-existing, unrelated, delicately-uncommitted operator work. Per this repository's own rule ("If a task would change existing architectural decisions, do not do it silently. Tell the user first"), this was surfaced here rather than guessed.
- Model-runtime freshness has a smaller version of the same tension: `dashboard.py` currently computes Codex CLI availability once, at process-wiring time; re-probing on every `start()` is cheap (a `--version`/`login status` check, not a token-consuming completion) and would be a reasonable small addition, but was left alongside the worker-health decision above rather than half-wiring one side of `PreflightCommand` and not the other.
- Practical consequence: the RT-D **PASS criterion is proven** ("start is denied with a clear reason when AuthorizationSource/scope/budget is missing, before any Worker or model call happens") at the use-case level, with real PostgreSQL-shaped fakes standing in for the SoR. It is **not yet proven** that `dashboard.py`'s actual `start()` call path invokes this gate today — it does not, yet.

## Unresolved / explicitly out of scope for this slice

- Live production wiring of `Preflight` into `dashboard.py`'s `prepare_start` — see "Known limitation" above; requires an explicit decision on browser-worker health-check semantics first.
- The pre-existing `budget_consumption` CHECK-constraint migration defect (unrelated legacy bug, same one flagged at Slice 0/1).
- Slice 1's own documented residual risk (heartbeat-bounded, not per-write, lease fencing inside `AutonomousResearchController`) is unchanged by this slice.

## Next locked slice

Slice 3 — Unified opportunity source (MR-1) (`IMPLEMENTATION_SEQUENCE_LOCK.md` §5 / campaign Phase D), not started.
