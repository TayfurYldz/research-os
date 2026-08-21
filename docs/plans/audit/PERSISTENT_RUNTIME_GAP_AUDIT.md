# Research OS — Persistent Runtime Gap Audit

**Companion to:** `CURRENT_ARCHITECTURE_SNAPSHOT.md`, reconciles against `RESEARCH_OS_PERSISTENT_RUNTIME_PLAN.md`
**Status:** AUDIT — no production code changed.

---

## 1. Current dashboard / run-control / supervisor lifecycle (call graph)

```text
main()                                              dashboard.py (module entrypoint, research-os-dashboard script)
  → build_dashboard_run_control_runtime(uow_factory, model, ...)   dashboard.py:153-176   [IMPLEMENTED CALL]
      → worker = PersistentBrowserWorkerAdapter()                                          [IMPLEMENTED CALL, uncommitted change]
      → controller = AutonomousResearchController(uow_factory, worker, model)              [IMPLEMENTED CALL]
      → registry = LocalRunSupervisorRegistry()                                            [IMPLEMENTED CALL — process-local dict]
      → control = ResearchRunControl(controller, registry, uow_factory, prepare_start=...) [IMPLEMENTED CALL]
      → approval = DashboardApprovalRuntime(StartHumanReview(uow_factory),
                     RecordHumanReview(uow_factory), FinalizeFinding(uow_factory))          [IMPLEMENTED CALL]
  → DashboardHandler (http.server.BaseHTTPRequestHandler subclass) bound to runtime, served
      by http.server.ThreadingHTTPServer                                                    [IMPLEMENTED CALL]

POST /api/runs/{id}/start
  → DashboardHandler._operator_run_action("start", run_id, payload)   dashboard.py:316-344  [IMPLEMENTED CALL]
      → command_factory(run_id, payload) → StartAutonomousResearchCommand(..., surface_discovery=...)
      → getattr(runtime.control, "start")(command)
          → ResearchRunControl.start(command)                          research_run_control.py:26-38  [IMPLEMENTED CALL]
              → AutonomousResearchController.start(command)             (idempotent re-find-or-create)  [IMPLEMENTED CALL]
              → if READY: LocalRunSupervisorRegistry.start(run_id=..., controller=..., command=..., uow_factory=...)
                  → returns existing supervisor if one is already running for this run_id (dict lookup by
                    research_run_id, in-process only)                   local_run_supervisor.py:150-166 [IMPLEMENTED CALL]
                  → else constructs LocalRunSupervisor(...) and calls .start()
                      → threading.Thread(target=self._run, daemon=True).start()  local_run_supervisor.py:100-111 [IMPLEMENTED CALL]
POST /api/runs/{id}/pause|resume|cancel   → same _operator_run_action dispatch to control.pause/resume/cancel
POST /api/finding-proposals/{id}/review   → DashboardApprovalRuntime.record_review (manual, human-actor required)
POST /api/finding-proposals/{id}/finalize → DashboardApprovalRuntime.finalize (manual)
```

**Process owner:** the single Python process running `research-os-dashboard` (or whatever process imports and calls `build_dashboard_run_control_runtime`). There is no separate daemon process. Confirmed absence of `research-osd` by (a) no such console script in `pyproject.toml`, (b) no file matching `*osd*.py`/`*daemon*.py` under `src/research_os/` (glob checked), (c) `LocalRunSupervisorRegistry` docstring itself states "process-local... does not survive process restart" (`local_run_supervisor.py:114-120`).

---

## 2. Process ownership map

| State | Where it lives | Survives dashboard process exit? | Survives machine restart? |
|---|---|---|---|
| `ResearchOrchestrationRecord` (state, phase, bounds, checkpoints) | PostgreSQL `research_orchestration` | Yes | Yes |
| `ExecutionAttemptRecord` | PostgreSQL `execution_attempt` | Yes | Yes |
| Evidence/Candidate/Verification/FindingProposal/Finding | PostgreSQL | Yes | Yes |
| The fact that a `RUNNING` orchestration currently *has* an active supervisor thread ticking it | Python process memory (`LocalRunSupervisorRegistry._supervisors: dict`) | **No** | **No** |
| The `threading.Thread` itself, and thus "who is allowed to call `.step()` right now" | Python process memory | **No** | **No** |
| Playwright/Chromium child process(es) owned by `PersistentBrowserWorkerAdapter` | OS child process, parented to the dashboard process | **No** (orphan risk, see §3) | **No** |
| In-flight session cookies/secrets used by the browser worker mid-run | Playwright browser context memory / OS process memory only (confirmed: `session_context` DB table stores only metadata — `secret_scheme`, `secret_name`, no raw secret column, `a21_001_session_context.py`) | **No** | **No** |

---

## 3. Restart behavior (what actually happens)

- **Browser closes (operator's browser tab, i.e. the dashboard UI client):** No effect on the ARC/supervisor — the dashboard server and its threads are independent of any HTTP client connection. Confirmed by the handler being a stateless request/response HTTP server (`http.server.BaseHTTPRequestHandler`), not a WebSocket/SSE session tied to a browser tab. `dashboard.py` does implement a polling `/api/runs` status endpoint, not a push channel — there is no SSE implementation anywhere in `src/research_os/interface/` (grep for `text/event-stream`, `EventSource` — zero hits in `src/`).
- **Dashboard server process exits (Ctrl-C, crash, redeploy):** All `LocalRunSupervisor` threads die immediately (they are daemon threads inside that process). Any orchestration mid-cycle is left exactly where its last `PERSISTED HANDOFF` left it in Postgres — most likely `RUNNING` with `current_phase` at whatever phase was last checkpointed. **No process resumes it automatically.** The run is "stranded RUNNING" until an operator restarts the dashboard and manually calls `start` again on that run id (which the idempotent `AutonomousResearchController.start()` will happily do — it re-finds the existing `RUNNING` record and, per code, does not require the state to be `READY` to re-attach a supervisor if a check permits — the exact resume mechanics are handled by the existing recovery/checkpoint-replay path in `step()`, not by a purpose-built crash classifier).
- **The Python process itself dies mid-`ExecutePlannedExperiment.dispatch()`** (i.e., between `DISPATCHING` being committed and the Worker returning): the attempt is left `DISPATCHING` in Postgres. On the next `start`, `ExecutePlannedExperiment`'s own re-entry path (`_mark_unknown` / `_fail_closed_existing`, `execute_planned_experiment.py:573-636`) will classify it, **not** silently retry it as if nothing happened. This is a genuinely correct partial implementation of "operational failure != hypothesis falsification."
- **Machine restart:** identical to "process exits" above, plus the Playwright/Chromium child process(es) are also gone (they die with their parent or become orphans depending on OS process-group cleanup — `worker_runtime/python/browser_containment.py` implements Linux cgroup-based containment/cleanup **for process trees the supervisor itself spawned in the current run**, per the sub-agent verification of GATE 21 material; it explicitly does not attempt to discover and clean up orphans from a *previous* process's crash). No automatic resumption of any run occurs on OS boot — there is no systemd unit, no init script, nothing under `/etc/systemd` or equivalent in this repo (none expected, since no daemon exists to register).
- **Duplicate-start protection:** exists at two levels today — `AutonomousResearchController.start()` is idempotent against the DB record (won't create a second orchestration row), and `LocalRunSupervisorRegistry.start()` returns the existing supervisor if `existing.is_running` is true for that `research_run_id` **within the same process** (`local_run_supervisor.py:161-166`). There is **no protection at all** against two different *processes* (e.g., two dashboard instances, or an operator running the CLI concurrently with the dashboard) both attaching a supervisor to the same `research_run_id` — nothing prevents two threads in two processes from both reading `RUNNING`, both passing the in-process idempotency check (which only sees its own process's dict), and both calling `.step()` concurrently against the same orchestration row. This is the exact scenario lease/fencing exists to prevent, and it is unmitigated today.

---

## 4. Execution attempt state (already exists — do not rebuild)

Covered fully in `CURRENT_ARCHITECTURE_SNAPSHOT.md` §5; restated here for completeness against the runtime plan's RT-1 requirement:

- Table: `execution_attempt` (`a7_001_execution_attempt.py`), 16 columns exactly (verified against `data/postgres/tables.py`).
- States: `AUTHORIZED, DISPATCHING, COMPLETED, FAILED, TIMED_OUT, CANCELLED, UNKNOWN_OUTCOME` (DB CHECK constraint).
- `request_id`: non-null, DB-unique (`uq_execution_attempt_request_id`) — this **is** the idempotency key the plan asks for, just not named `idempotency_key`.
- `DISPATCHING` committed before `WorkerPort.invoke()` — durable evidence of intent-to-execute exists before the side effect happens (`execute_planned_experiment.py:532-561`).
- **Missing relative to plan:** `lease_epoch`, `owner_runtime_instance_id` (no column links an attempt to which runtime/supervisor dispatched it), `outcome_class` (nearest equivalent: `state` itself, no separate coarse/fine split), a distinct `result_recorded_at` (only `completed_at`), `INTENT_COMMITTED`/`DISPATCHED` as named phases (nearest equivalents: row-insert time and `DISPATCHING`, respectively — semantically present, not nominally present).

---

## 5. Reconciliation support (already exists — dormant, not wired)

`ReconcileResearchRun` (`application/reconcile_research_run.py`) implements, in domain-adjacent application code:

- Classifies `AUTHORIZED` + `side_effect_level == 0` attempts as `SAFE_TO_RETRY`.
- Classifies `DISPATCHING` (any side-effect level) as needing `UNKNOWN_OUTCOME` treatment.
- Classifies side-effectful `UNKNOWN_OUTCOME` as `REQUIRE_HUMAN_REVIEW` (not auto-retried — matches the master plan's explicit invariant).
- Classifies a stale `RUNNING` orchestration (no forward progress) as eligible for `MARK_OPERATIONAL_FAILURE`.
- Detects `INTEGRITY_ERROR` states (e.g., checkpoint pointing at a non-existent attempt).

**This is real, tested logic** (`tests/unit/application/test_reconcile_research_run.py`) that maps closely onto the runtime plan's Section 7 crash classifier. **It has zero production callers** — not from the dashboard, not from `LocalRunSupervisor`, not from any startup path. Building a new crash classifier from scratch would violate "reuse existing architecture where correct" (task instruction §11); the correct next step is to **wire this existing class in**, not replace it.

---

## 6. Terminal-state bug — verified

`AutonomousResearchController.pause()` and `.cancel()`:

```python
# autonomous_research_controller.py:788-810 (paraphrase of structure, not a rewrite — cited for audit only)
current = uow.research_orchestrations.get(research_run_id)
updated = replace(current, state=OrchestrationState.PAUSED.value, pause_reason=...)
uow.research_orchestrations.save(updated)
```

No guard checks `current.state in TERMINAL_ORCHESTRATION_STATES` before this `replace()`/`save()`. `TERMINAL_ORCHESTRATION_STATES = frozenset({"COMPLETED", "BUDGET_EXHAUSTED", "FAILED_OPERATIONAL"})` is defined (`research/orchestration.py`) and used to *stop* automatic `step()` progression, but is **not** consulted by the manual `pause`/`cancel` control paths. The repository-level `save()` (`data/postgres/repositories.py:2053-2065`) performs an unconditional `UPDATE ... WHERE research_run_id = %s`, with no `AND state NOT IN (...)` predicate and no optimistic-concurrency check (no version column compared). **Confirmed defect: an operator (or a racing second process, per §3) can overwrite a `COMPLETED`/`BUDGET_EXHAUSTED`/`FAILED_OPERATIONAL` run's `stop_reason` by calling pause or cancel after the fact.** No existing test exercises "cancel a COMPLETED run" or "pause a BUDGET_EXHAUSTED run" (confirmed absent from `tests/unit/application/test_autonomous_research_controller.py` and `test_orchestration_recovery.py` test-name inventories).

---

## 7. Lease / fencing inventory

Exhaustive search terms and result, across `alembic/versions/*.py`, `src/research_os/data/postgres/tables.py`, `src/research_os/data/records.py`, all of `src/research_os/application/`, all of `src/research_os/platform/`:

| Term | Result |
|---|---|
| `runtime_instance` | 0 matches |
| `owner_runtime_instance_id` | 0 matches |
| `lease_epoch` | 0 matches |
| `fencing` / `fencing_epoch` / `fencing_token` | 0 matches |
| `heartbeat` | 0 matches |
| `lease_until` | 0 matches |
| `advisory_lock` / `pg_advisory` | 0 matches |
| CAS-style conditional update (`WHERE ... AND version = ...` or similar) on any orchestration/attempt table | 0 matches — all `save()`/`set_state()` repository methods use unconditional `WHERE id = %s` |

**Verdict: 100% NOT_PRESENT.** This is the one area of the runtime plan with zero existing substrate to reuse; it must be built new. This audit does not design the schema (task instruction §2 forbids it) but records that the *smallest* correct version is bounded by what already exists: `ResearchOrchestrationRecord` already has an `updated_at`/`checkpoint_at` pair that a lease could piggyback on rather than requiring a wholly separate `runtime_instance` table on day one — that is a design decision for the next phase, not this audit.

---

## 8. Preflight inventory

| Plan concept | Existing equivalent | Coherent or fragmented? |
|---|---|---|
| Model probe / runtime discovery | `platform/readiness.py` — `RuntimeReadiness`, `ReadinessStage` (`NOT_INSTALLED → INSTALLED → VERSION_KNOWN → AUTH_READY → DEPENDENCIES_READY → DIAGNOSTIC_READY → MODELPORT_COMPATIBLE → BENCHMARK_COMPATIBLE`) | Coherent, but scoped **only** to ModelPort. Codex CLI has a real `AUTH_READY` probe (subprocess call checking login state); other adapters (OpenAI/Anthropic/Gemini) report readiness from config/env-var presence, not a live API round-trip (per the dedicated ModelPort sub-agent verification) — i.e. "configured" is being used where the plan's ladder implies "probed". |
| Authorization/scope validation before a run starts | `PrepareAutonomousResearchStart` (referenced as `prepare_start` in `research_run_control.py`) performs some pre-start checks, and every *individual* execution attempt is authorized fresh via `evaluate_execution()` — but there is no single "can this run start at all" aggregate check that covers AuthorizationSource validity + effective ScopeRules resolvability + budget existence + model readiness + worker readiness in one gate. | Fragmented — the checks exist, distributed across `core/execution.py` (per-attempt) and whatever `prepare_start` currently does; there is no unified pre-run report object. |
| Worker probe | No equivalent found. `PersistentBrowserWorkerAdapter` does not appear to expose a standalone health-check call distinct from actually dispatching work (UNKNOWN — not exhaustively verified against every method on that class; flagged as unresolved below). | Fragmented/absent. |
| Budget allocation check before start | `IssuedBudgetRecord` existence is implied to be a precondition (execution attempts reference `budget_id`), but whether "no budget issued yet" is caught before `start()` vs. only at first `evaluate_execution()` call was not directly traced in this audit. | UNKNOWN — requires reading `prepare_start`'s exact implementation, not completed in this pass. |

**Verdict: no coherent Preflight exists today.** Readiness exists for models only; scope/authorization/budget checks exist but are enforced per-attempt (correctly, per Core's design) rather than aggregated into a single pre-start report the plan's `RT-4 Preflight` concept calls for.

---

## 9. Current persistence gaps (summary, cross-referencing above)

1. Runtime ownership (who is actively ticking a run) is process-memory-only — the single largest gap.
2. No lease/fencing — a second process can race a first without detection (§3, §7).
3. Terminal-state mutability bug (§6) — smallest fix, highest correctness value, essentially free to fix alongside the lease work since it touches the same `pause`/`cancel` code paths.
4. `ReconcileResearchRun` built but unwired (§5) — smallest-effort win: wire an existing, tested class rather than building a new one.
5. No unified Preflight (§8).
6. No SSE/push channel — dashboard is poll-only; not a correctness gap, but relevant to the "operator visibility" requirement in the runtime plan.
7. Browser/session process cleanup is scoped to processes spawned within the *same* run/process tree; cross-crash orphan discovery does not exist (per §3 and the dedicated OAST/Browser sub-agent verification of `browser_containment.py`).

---

## 10. Minimal persistent-runtime design, based on EXISTING code (direction only, not implementation)

Reusing what already exists rather than adopting plan-document names wholesale:

- **RT-A (terminal-state guard):** Add the missing `if current.state in TERMINAL_ORCHESTRATION_STATES: reject/no-op` check to `pause()` and `cancel()` in `AutonomousResearchController`, and add a `WHERE state NOT IN (...)` predicate (or a `version`/`updated_at` optimistic check) to the orchestration `save()` repository method. This is the cheapest, highest-value fix and has zero dependency on anything else in this list.
- **RT-B (wire the existing reconciler):** Call `ReconcileResearchRun` from the `start()` path (or a new lightweight startup routine) before attaching a new `LocalRunSupervisor`/successor to an existing `RUNNING`-but-unowned orchestration, instead of leaving recovery entirely to `step()`'s own phase-keyed re-entry.
- **RT-C (minimal lease, reusing `research_orchestration`):** Add `owner_runtime_instance_id`, `lease_epoch` (monotonic integer), `lease_expires_at` to `research_orchestration` (additive migration) rather than a brand-new table on day one; require every `save()` that represents "I am actively driving this run" to include `WHERE lease_epoch = :expected_epoch`, and have `LocalRunSupervisorRegistry.start()` acquire the lease (increment epoch, set owner id, set expiry) before spawning its thread, with the thread renewing (`heartbeat`) the expiry each tick and stopping itself if the CAS renewal fails (meaning another owner has taken the lease). This directly closes the concurrent-attach gap in §3 using the table that already exists.
- **RT-D (Preflight aggregation):** A single new `application/preflight.py` use case that calls the *existing* pieces (model `RuntimeReadiness`, a to-be-checked worker health call, AuthorizationSource/ScopeRule resolvability check, budget existence check) and returns one report object; does not reimplement any of the underlying checks.
- **research-osd / dashboard-as-client / systemd / Operator API / SSE:** all remain fully unbuilt (`NOT_PRESENT`) and are the largest remaining item; per task instruction §11, this audit does not design that subsystem beyond noting it depends on RT-A through RT-C existing first (a daemon supervising unleased, non-terminal-guarded runs would just make the race in §3 worse, not better).

---

## 11. Production files likely affected in the NEXT phase (not touched in this audit)

`autonomous_research_controller.py` (pause/cancel guard — small, targeted change), `data/postgres/repositories.py` (conditional `save()` for orchestration), `local_run_supervisor.py`/`local_run_supervisor.py`'s registry (lease acquire/renew/release), a new additive `alembic/versions/aXX_lease_fields.py` migration, `research_run_control.py` (call reconciler on start), a new `application/preflight.py`, `data/records.py` (new optional fields on `ResearchOrchestrationRecord`).

## 12. Tests required before implementation

- A test proving `pause()`/`cancel()` on a `COMPLETED`/`BUDGET_EXHAUSTED`/`FAILED_OPERATIONAL` run is rejected (or is a true no-op) and does not alter `stop_reason` (RT-A — this is the literal invariant-table requirement "terminal state immutable").
- A test proving two concurrent `start()` calls against the same `research_run_id`, simulated as two separate `UnitOfWorkFactory`/registry instances (i.e., two "processes"), result in exactly one active lease holder and the second attacher backing off (RT-C).
- A test proving a stale lease (expired `lease_expires_at`) can be legitimately taken over by a new owner, and that the old owner's next heartbeat/save attempt is rejected once superseded (RT-C — "stale runtime owner cannot mutate run").
- A test proving `ReconcileResearchRun`'s classification is actually invoked and acted upon at `start()` time for a `RUNNING`-but-unowned run left over from a simulated crash (RT-B).
- A test proving the new Preflight report correctly denies a start when scope is unresolvable/AuthorizationSource is missing, matching the master-plan invariant "do not start active testing if AuthorizationSource or effective scope is missing" (RT-D).
