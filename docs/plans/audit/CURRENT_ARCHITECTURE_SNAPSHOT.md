# Research OS — Current Architecture Snapshot

**Document class:** Phase-0 reconnaissance audit (read-only)
**Location note:** the task specified `docs/plan/audit/`. This repository's existing convention is `docs/plans/` (plural — see `docs/plans/RESEARCH_OS_MASTER_PLAN.md` and 18 other plan files there). No `docs/plan/` directory exists. To avoid creating a second, inconsistent top-level docs tree, this audit is filed under `docs/plans/audit/`. Flagged for operator awareness, not decided unilaterally as a renaming.
**Date:** 2026-08-21
**Status:** AUDIT — no production code, migrations, or tests were modified to produce this document.
**Method:** Direct code reading/grep by the primary agent, cross-checked against five independent `explore` sub-agent deep-dives (ARC/runtime, Hunter/Coverage/Mutation/V3/Protocol, Evidence→Finding promotion pipeline, OAST/Browser/ModelPort, migrations+tests). Every claim below is backed by a file:line citation. Where a claim could not be verified, it is marked `UNKNOWN`.

---

## 1. Git / worktree snapshot

```text
Repo:              /home/tayfur/research-os  (git repo; not itself a "directory is a git repo: No" — the harness flag refers to the parent shell CWD, the repo itself is git-tracked)
Remote:            origin = https://github.com/TayfurYldz/research-os.git
Current branch:    qualification/dashboard-runtime-closure
Current HEAD:      b2256e908e1a0906b47cf822c86b88418d7efa3b
                    "checkpoint: connect dashboard autonomous research runtime"
Master (origin):   d004656bc57162ba3776930a8eee2c2143f18f9f "Ignore local agent memory"
Merge-base:        d004656bc57162ba3776930a8eee2c2143f18f9f (branch is master + 1 commit)
Ahead/behind:      1 ahead, 0 behind origin/master (git rev-list --left-right --count HEAD...origin/master → "1 0")
```

Recent history on this branch (most recent first):

```text
b2256e9 (HEAD) checkpoint: connect dashboard autonomous research runtime
d004656 (origin/master, master) Ignore local agent memory
3578b8f Support YesWeHack program bootstrap
8c82fd0 Add dashboard program bootstrap flow
a8a68b6 Add local security operations dashboard
d402893 docs: reconcile sulandirma roadmap completion
113b99e SD-G16 sealed: exploratory hypothesis generator
dde38c5 SD-G15 sealed: live coverage recall consolidation
```

### Working-tree status (preserved, not touched)

```text
 M src/research_os/application/local_run_supervisor.py
 M src/research_os/interface/dashboard.py
?? docs/plans/RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md
?? docs/plans/RESEARCH_OS_MASTER_PLAN.md
?? docs/plans/RESEARCH_OS_PERSISTENT_RUNTIME_PLAN.md
?? tests/e2e/test_dashboard_operator_controls.py
?? var/live-runs/
```

**A. Master implementation** = `d004656` (origin/master). Does not contain the dashboard/ARC wiring changes below.

**B. Current branch implementation (committed, `b2256e9`)** = master + one checkpoint commit that:
- wired `AutonomousResearchController` into the dashboard's operator lifecycle (start/pause/resume/cancel),
- added `LocalRunSupervisorRegistry`/`LocalRunSupervisor` process-local scheduling,
- added `ResearchRunControl` as the dashboard-facing use case,
- did **not** add any daemon, lease, fencing, or preflight code.

**C. Uncommitted local implementation (dirty tree, not yet committed)**:
- `local_run_supervisor.py`: adds one-shot clearing of `command.surface_discovery` after the first successful tick (`replace(self.command, surface_discovery=None)`), so a discovery-seeded command only drives one discovery step before falling back to the normal ARC cycle path.
- `dashboard.py`: swaps `LocalProcessWorkerAdapter` → `PersistentBrowserWorkerAdapter` as the Worker used by the dashboard-constructed ARC; adds `SurfaceDiscoveryStart` construction from the operator-submitted target/scope on `START`; adds per-run START/PAUSE/RESUME/CANCEL buttons and a `/api/runs/{id}/{action}` handler (`unquote(parts[2])` fix for run IDs containing `/`).
- New file `tests/e2e/test_dashboard_operator_controls.py` (Playwright browser test of the new buttons, against a **fake** application-control object, not the real ARC/Postgres stack).
- New file `var/live-runs/` (runtime artifact directory, not source).
- Three new plan documents copied into `docs/plans/` (the three plans read as input to this audit) — these are **documentation-only**, not implementation.

**D. Documentation-only claims** = everything in `docs/plans/*.md`, `docs/OPERATIONS.md`, `TECHNICAL_DECISIONS.md`, `IMPLEMENTATION_PLAN.md`. These express design intent and, in several cases (`maturity.py` docstring, `OPERATIONS.md`), narrative gate history. They are **not** treated as implementation evidence anywhere in this audit; every architectural claim below cites `src/`, `alembic/`, or `tests/` instead.

No destructive git operation was performed. The dirty tree was read via `git diff` only.

---

## 2. Runtime / environment facts

```text
Python (active shell):        3.13.12  (resolved to /home/tayfur/strix/.venv/bin/python3 — NOTE: this is a
                               DIFFERENT project's virtualenv, not this repo's own .venv. This is an
                               environment hazard: `python3 -m alembic ...` failed under that interpreter
                               with "No module named alembic.__main__" until re-run under
                               /home/tayfur/research-os/.venv/bin/python3.)
Project's own venv:            /home/tayfur/research-os/.venv (exists, has python3.13, alembic installed)
requires-python (pyproject):   >=3.11
Alembic head (verified with
 the project's own venv):      a34_001_program_platforms  (confirmed twice: manual down_revision chain
                                walk across all 30 files, and `.venv/bin/python3 -m alembic heads` →
                                "a34_001_program_platforms (head)")
Migration count:               30 files (a3, a6–a34; there is no a1/a2/a4/a5 — those revision ids were
                                never created in this repo, this is not a gap, just non-contiguous naming)
Installed console scripts:     research-os → research_os.interface.cli:main
                                research-os-dashboard → research_os.interface.dashboard:main
                                (pyproject.toml:26-28) — no research-osd script exists.
```

---

## 3. Architecture layer map (what exists, where, who calls it)

| Layer | Directory | Representative modules | Notes |
|---|---|---|---|
| Core (authority) | `src/research_os/core/` | `execution.py`, `approval.py`, `authorization.py`, `budget.py`, `capability.py`, `scope.py`, `scope_compiler.py`, `rate_limit.py`, `enums.py` | Pure functions/dataclasses. `evaluate_execution()` (`core/execution.py:84-171`) is the single authorization entry point: capability → authorization → scope → budget → side-effect → approval, in that fixed order, always DENY-precedent. No mutable state. |
| Data (persistence contracts) | `src/research_os/data/` | `records.py` (~2650+ lines of frozen dataclasses), `unit_of_work.py`, `postgres/` (`tables.py`, `repositories.py`, `unit_of_work.py`, `mapping.py`, `hunter_family_seed.py`) | PostgreSQL is the only production `UnitOfWorkFactory` implementation. Tests substitute an in-memory fake (`tests/support/fake_unit_of_work.py`). |
| Research (domain logic) | `src/research_os/research/` | `orchestration.py`, `cycle.py`, `admission.py`, `assessment.py`, `evidence.py`, `candidate.py`, `verification.py`, `finding_proposal.py`, `exploration.py`, `exploratory.py`, `compiler.py`, `planning.py`, `selection.py`, `scheduler/`, `coverage/`, `mutation/`, `protocol/`, `oast/`, `impact/`, `evaluators/` | Pure domain rules: admission gates, state-machine legality, deterministic plan builders. No I/O, no model calls, no Worker calls. |
| Application (use-case coordination) | `src/research_os/application/` | `autonomous_research_controller.py` (1218 lines — the ARC), `local_run_supervisor.py`, `research_run_control.py`, `select_research_opportunities.py`, `propose_research_hypothesis.py`, `prepare_planned_experiment.py`, `execute_planned_experiment.py`, `evaluate_experiment_feedback.py`, `admit_diagnostic_evidence.py`, `propose_candidate.py`, `start_candidate_verification.py`, `complete_candidate_verification.py`, `submit_finding_proposal.py`, `start_human_review.py`, `record_human_review.py`, `finalize_finding.py`, `score_finding_severity.py`, `run_hunt_cycle.py`, `run_hunt_scheduler.py`, `generate_hunt_hypotheses.py`, `hunt_validation.py`, `hunt_v3_queue_approval.py`, `draft_exploratory_hypothesis.py`, `record_mutation_variants.py`, `reconcile_research_run.py`, `run_research_selection.py`, `discovery/runner.py` | Orchestrates domain + data + platform. This is where the "one lifecycle vs. many use-cases" question is decided (see Section 4 and the Reconnection Audit). |
| Platform (technical ports) | `src/research_os/platform/` | `worker.py` (WorkerPort protocol), `local_process_worker.py`, `persistent_browser_worker.py`, `secrets.py`, `contract_validation.py`, `observability.py`, `readiness.py`, `url_normalize.py` | `readiness.py` implements a `ReadinessStage` enum (`NOT_INSTALLED → INSTALLED → VERSION_KNOWN → AUTH_READY → DEPENDENCIES_READY → DIAGNOSTIC_READY → MODELPORT_COMPATIBLE → BENCHMARK_COMPATIBLE`) — this is model-runtime readiness only, not a system-wide Preflight (see Runtime Gap Audit). |
| Worker runtime | `src/research_os/worker_runtime/python/` | `implementation.py`, `browser_engine.py`, `playwright_chromium_engine.py`, `browser_page.py`, `http_transaction.py`, `http_authentication.py`, `http_authorization.py`, `http_state_transition.py`, `persistent_runtime.py`, `browser_containment.py` | Real Playwright/Chromium engine wired into a static capability dispatch table (`implementation.py:39-46`). Runs as a child process managed by `PersistentBrowserWorkerAdapter` (`platform/persistent_browser_worker.py`). |
| Integrations | `src/research_os/integrations/` | `models/` (OpenAI/Anthropic/Gemini/Codex-CLI/local/external-agent adapters), `strix/adapter.py` | ModelPort adapters; Strix integration is explicitly a separate, non-authoritative tool adapter. |
| Interface | `src/research_os/interface/` | `dashboard.py` (1913+ lines, stdlib `http.server`-based), `cli.py`, `git_provenance.py` | The **only** process that constructs and runs the ARC in production is the dashboard process (see Section 4). CLI has no lifecycle commands at all (`status/export-source/census/budget/coverage` only — `cli.py:332-357`). |

---

## 4. Current autonomous lifecycle (verified call graph, summary — full graph in the Reconnection and Runtime audits)

```text
Dashboard process (single Python process, stdlib http.server.ThreadingHTTPServer)
  build_dashboard_run_control_runtime()                       [dashboard.py:153-176]
    → AutonomousResearchController(factory, PersistentBrowserWorkerAdapter(), model)
    → ResearchRunControl(controller, LocalRunSupervisorRegistry(), factory)

POST /api/runs/{id}/start  → _operator_run_action("start", ...)  [dashboard.py:316-344, 1017-1018]
  → ResearchRunControl.start(command)                            [research_run_control.py:26-38]
    → AutonomousResearchController.start(command)                [autonomous_research_controller.py:170-179]
        - idempotent: re-finds existing ResearchOrchestrationRecord row, does not duplicate it
    → if state == READY: LocalRunSupervisorRegistry.start(...)    [local_run_supervisor.py:144-166]
        → threading.Thread(target=self._run, daemon=True).start() [local_run_supervisor.py:100-111]
            → loop: LocalRunSupervisor.tick() every cadence_seconds (default 0.25s)
                → AutonomousResearchController.step(command)      [autonomous_research_controller.py:299-...]
```

`step()` per cycle (normal, non-recovery path):

```text
SelectResearchOpportunities.execute()          [select_research_opportunities.py] — diagnostic opportunities only
  → propose_diagnostic_opportunities() / select_research_opportunities()   [research/exploration.py]
ProposeResearchHypothesis.execute()            [propose_research_hypothesis.py]
  → ResearchContextBuilder.build()
  → generate_proposal()  → ModelPort.complete(GENERATOR)     [research/cycle.py:144-168]
  → generate_challenge() → ModelPort.complete(FALSIFIER)     [research/cycle.py:171-197]
  → admit_hypothesis() → plan_admitted_hypothesis()
PreparePlannedExperiment.execute()             [prepare_planned_experiment.py] — persists Experiment + ExperimentPlan
ExecutePlannedExperiment.execute()             [execute_planned_experiment.py]
  → authorize(): evaluate_execution()          [core/execution.py:84] — CORE authorization, fresh per attempt
  → ExecutionAttemptRecord(state=AUTHORIZED) persisted, THEN
  → dispatch(): attempt → DISPATCHING (durable, committed) → WorkerPort.invoke() → _record_outcome()
  → IngestCompletedWorkerInvocation.execute() → WorkerResult + Observation persisted
EvaluateExperimentFeedback.execute()           [evaluate_experiment_feedback.py] — HypothesisAssessmentRecord persisted
_complete_cycle() / _stop()                    — ResearchOrchestrationRecord + ResearchCycleRecord updated
```

**Decisive fact (verified independently by direct grep and by two sub-agents):** `autonomous_research_controller.py` contains **zero** references to `Hunter`, `hunt_`, `Coverage`, `Mutation`, `protocol`, `v3_queue`, or `Exploratory`. The ARC's automatic progression stops at a durable `HypothesisAssessmentRecord`. It never imports or calls `AdmitDiagnosticEvidence`, `ProposeCandidateFromEvidence`, `StartCandidateVerification`, `CompleteCandidateVerification`, `SubmitFindingProposal`, `StartHumanReview`, `RecordHumanReview`, or `FinalizeFinding` (zero hits, confirmed by `rg` against the file). The orchestration phase enum includes `TRANSITION_B_COMPLETE` (`research/orchestration.py:74`) but the ARC never writes it.

The dashboard wires only the **tail** of the promotion chain as manual/operator endpoints: `StartHumanReview`, `RecordHumanReview`, `FinalizeFinding` (`dashboard.py:291-294`). Evidence admission, Candidate creation, and Verification have **no** production entry point anywhere (dashboard, CLI, or ARC) — they are reachable only from test files (confirmed by repo-wide constructor search: `AdmitDiagnosticEvidence(`, `ProposeCandidateFromEvidence(`, `StartCandidateVerification(`, `CompleteCandidateVerification(`, `SubmitFindingProposal(` all match only files under `tests/`).

## 5. Current execution lifecycle (Core → Worker boundary)

`ExecutePlannedExperiment` (`execute_planned_experiment.py`) already implements most of what the Persistent Runtime plan calls "RT-1 execution journal" at the single-attempt level:

- `request_id` is generated once (`new_opaque_id()`), is **DB-unique** (`uq_execution_attempt_request_id`, `alembic/versions/a7_001_execution_attempt.py:57`), and is checked for existing attempts before authorizing a new one (`_fail_closed_existing`, `execute_planned_experiment.py:573-611`) — this is the idempotency guard the runtime plan asks for.
- Attempt states: `AUTHORIZED → DISPATCHING → {COMPLETED|FAILED|TIMED_OUT|CANCELLED|UNKNOWN_OUTCOME}` (`data/records.py:67-77`, DB check constraint `alembic/versions/a7_001_execution_attempt.py:58-63`).
- `DISPATCHING` is durably committed **before** `WorkerPort.invoke()` is called (`execute_planned_experiment.py:532-561`) — crash-between-dispatch-and-result is therefore always observable from the DB alone as a stuck `DISPATCHING` row, and is explicitly turned into `UNKNOWN_OUTCOME` on the next authorize-path re-entry (`_mark_unknown`, lines 613-636) or via `ReconcileResearchRun` (see below).
- Missing relative to the plan's target schema: `lease_epoch`, `owner_runtime_instance_id`, `outcome_class`, a separate `result_recorded_at` (only `completed_at` exists), and explicit `INTENT_COMMITTED`/`DISPATCHED` phase names (nearest equivalents are implicit "row inserted with state=AUTHORIZED" and `DISPATCHING`).

`ReconcileResearchRun` (`application/reconcile_research_run.py`) already implements a non-trivial crash classifier (`SAFE_TO_RETRY`, `UNKNOWN_OUTCOME`, `REQUIRE_HUMAN_REVIEW`, `MARK_OPERATIONAL_FAILURE`, `RESUME_EXISTING`, `SAFE_TO_ADVANCE`, `INTEGRITY_ERROR`) that maps closely onto the Persistent Runtime plan's Section 7 recovery classes — but it has **zero production callers** (confirmed: constructor `ReconcileResearchRun(` appears only in `tests/unit/application/test_reconcile_research_run.py`, `tests/integration/test_gate12.py`, `tests/integration/test_gate13.py`). It is fully-built domain-adjacent logic that is not wired into any startup path, dashboard route, or supervisor.

## 6. Current epistemic lifecycle (confirmed strict separation, with one caveat)

The Signal/WorkerResult/Observation/Assessment/Evidence/Candidate/Verification/FindingProposal/Finding separation from the master plan is **implemented as distinct DB tables and distinct dataclasses**, not merely as documentation:

- `worker_result`, `observation` — `alembic/versions/a3_001_persistence_spine.py`
- `hypothesis_assessment` — `a9_001_learning_cycle.py`
- `evidence`, `evidence_observation`, `evidence_admission` — `a10_001_evidence_admission.py`
- `candidate`, `candidate_evidence`, `candidate_admission`, `verification` — `a11_001_candidate_verification.py`
- `finding_proposal`, `human_review`, `approval`, `finding` — `a12_001_finding_acceptance.py`
- `impact_chain`, `impact_chain_node` (with mandatory non-empty `proof_refs`), `impact_chain_edge` — `a31_001_impact_graph.py`

Admission functions independently enforce the "!=" boundaries the plan requires, e.g. `EvaluateExperimentFeedback` explicitly does not create Evidence (`evaluate_experiment_feedback.py:1-4` docstring plus code: its only durable write is `HypothesisAssessmentRecord`). `FinalizeFinding` requires a validated Candidate + `HUMAN_REVIEW`-state proposal + `HumanReview` row + a subject/fingerprint-bound Core `Approval`, evaluated together (`application/finalize_finding.py:113-227`, gated by `research/finding_proposal.py:599-693`).

**Caveat (contradiction found, not present in any plan doc):** `ImpactChainEdge` rows carry no `proof_refs` (`research/impact/chain.py:66-82`; DB columns confirm — `alembic/versions/a31_001_impact_graph.py:68-86`), only nodes do. An edge asserting `ENABLES`/`ESCALATES`/`CONFIRMS` between two proof-backed nodes can be persisted without independent proof that the *relationship* holds. Also, `ScoreFindingSeverity` accepts caller-supplied `data_sensitivity`/`affected_scope` fields that are not derived from Evidence or ImpactGraph proof metadata (`application/score_finding_severity.py:28-32`; escalation logic `research/validation/severity.py:158-165`) — so a proof-bounded `DATA_READ` impact chain can still be scored P0 by an operator/caller asserting `affected_scope="ADMIN"` without additional evidence. This is a genuine, currently-unaddressed epistemic gap, not a documentation gap.

## 7. Database / migration inventory summary

30 migrations, `a3 → a6 → a7 → a8 → a9 → a10 → a11 → a12 → a13 → a14 → a15 → a16 → a17 → a18 → a19 → a20 → a21 → a22 → a23 → a24 → a25 → a26 → a27 → a28 → a29 → a30 → a31 → a32 → a33 → a34` (linear chain, single head `a34_001_program_platforms`, verified both by manual `down_revision` graph walk and by running `alembic heads` under the project's own venv).

| Migration | Introduces (for this audit's purposes) |
|---|---|
| a3 | `program`, `authorization_source`, `research_run`, `issued_budget`, `hypothesis`, `experiment`, `worker_result`, `observation`, `audit_event` |
| a6 | request/idempotency columns on `worker_result` (`request_id` unique, `parent_request_id`) |
| a7 | `execution_attempt` (see Section 5 for exact columns — **no** lease/owner/heartbeat fields) |
| a8 | `research_reasoning` (Generator/Falsifier provenance) |
| a9 | `research_admission`, `experiment_plan`, `hypothesis_assessment` |
| a10 | `evidence`, `evidence_observation`, `evidence_admission` |
| a11 | `candidate`, `candidate_evidence`, `candidate_admission`, `verification` |
| a12 | `finding_proposal`, `human_review`, `approval`, `finding` |
| a13 | `target_inference`, `differential_observation` |
| a14 | `invariant_hypothesis`, `invariant_source_ref`, `invariant_counterexample_ref`, `chain_hypothesis` |
| a15 | `research_opportunity`, `research_selection`, `snapshot`, `snapshot_member`, `change_event` |
| a16 | `research_orchestration` (mutable checkpoint), `research_cycle`, `budget_consumption` |
| a17 | orchestration restart-integrity columns (`current_phase`, `active_cycle_id`, `last_attempt_id`, etc.) |
| a18/a19 | Candidate/Finding classification constraints widened for `HTTP_AUTHORIZATION_DIFFERENTIAL` / `HTTP_STATE_TRANSITION_AUTHORIZATION` |
| a20 | `experiment_plan.capability_version` / `capability_definition_fingerprint` (**not** added to `execution_attempt`) |
| a21 | `session_context` (no raw secret columns) |
| a22 | discovery ledger: `discovery_run_config`, `control_event`, `discovery_fact`, `discovery_inference(_source)`, `discovery_fact_source`, `frontier_item/_source/_event`, `discovery_projection_receipt` |
| a23 | `scope_rule_v2`, `program_policy`, `rate_limit_profile`, `bounty_table` |
| a24 | `sensor_observation` |
| a25 | discovery fact kinds expanded (DOMAIN/HOSTNAME/CERT/SERVICE/TECH/JS_BUNDLE/API_SPEC) |
| a26 | `discovery_fact_source.sensor_observation_id` |
| a27 | `attack_surface_snapshot` (rebuildable summary) |
| a28 | program LLM daily budget, `budget_consumption.resource_metadata` |
| a29 | **`hunter_family`**, **`hunt_v3_queue`** (seeds 5 families at migration time; the other 11 exist only in the live `SEED_FAMILIES` list, not backfilled by any later migration) |
| a30 | `oast_token` |
| a31 | `impact_chain`, `impact_chain_node`, `impact_chain_edge`, `finding_proposal.impact_chain_ids` |
| a32 | `coverage_debt_snapshot` (rebuildable summary) |
| a33 | `hypothesis.identity_id`, `hunt_v3_queue.identity_id` |
| a34 (head) | `program.platform` widened (hackerone/bugcrowd/manual/yeswehack/intigriti/other) |

**Confirmed NOT PRESENT anywhere in `alembic/versions/` or `data/postgres/tables.py`** (exhaustive grep, zero hits): `runtime_instance`, `owner_runtime_instance_id`, `lease_epoch`, `fencing`, `heartbeat_at`, `lease_until`, `desired_action`, `preflight`, `advisory_lock`/`pg_advisory`. These are 100% plan-only concepts today.

**16 HunterFamily rows exist in the live seed source** (`data/postgres/hunter_family_seed.py`, counted directly): 5 original (SD-G5) + 9 broad-injection (SD-G12: SQLi, SSTI, LFI/RFI, mass-assignment, JWT, CORS, GraphQL, DOM-taint, AI/LLM-target) + 2 protocol (SD-G13: HTTP smuggling/desync, cache poisoning/deception).

## 8. Test evidence summary

234 test files total (142 `tests/unit/**`, 1 `tests/contract/**` top-level file plus subdirectory content, 37–41 `tests/integration/**`, 8 direct + 10 `lab/` fixtures under `tests/e2e/**`). None qualify as `live-model` or `live-oast` by actual fixture inspection. `tests/e2e/test_gate21_linux_cgroup.py` is the only file with genuine host/kernel field-validation behavior (and it is platform-gated/skippable). The new uncommitted `tests/e2e/test_dashboard_operator_controls.py` **currently fails to collect**: `ModuleNotFoundError: No module named 'pathsetup'` (verified by running `python3 -m pytest tests/e2e/test_dashboard_operator_controls.py -q`, exit code 2). Full claim-by-claim test mapping is in `RESEARCH_LIFECYCLE_RECONNECTION_AUDIT.md` and `PERSISTENT_RUNTIME_GAP_AUDIT.md`.

## 9. Gate / maturity normalization

See the full table in `IMPLEMENTATION_SEQUENCE_LOCK.md` §1. Summary of the authoritative source (`src/research_os/maturity.py`, which the project itself uses to keep eras apart — this is genuinely useful in-repo self-documentation, not just narrative):

- **Legacy infrastructure gates** (`GATE 01–22`, closed 2026-08-16 and after): architecture/plumbing gates. `maturity.py` explicitly warns several numbers are reused with different meaning across eras (e.g. "SD-G2 is NOT the old infrastructure GATE 02 … those are separate eras and must never be confused" — `maturity.py:20-25`, and similarly for GATE 03/04/05/06/08/09/10/07).
- **Attack Period gates** (`SD-G1`–`SD-G16`): sealed capability build-out (HunterFamily registry, Mutation Engine, OAST core, Coverage Debt, HunterScore, Independent Validator/Severity/Circuit-breaker, ImpactGraph, protocol specialists, exploratory generator). Sealed = unit/contract/integration tests passed at seal time; **sealed is not the same as connected to ARC's execution lifecycle** — this audit's central finding is that most SD-G capability code is disconnected from ARC (see Reconnection Audit).
- **This audit introduces no new gate numbering.** `MR-*`/`RT-*` numbering from the two sub-plans is reconciled against current code in `IMPLEMENTATION_SEQUENCE_LOCK.md`.
- Current authoritative flags (`maturity.py:229-257`): `ARCHITECTURE_VALIDATED=True`, `DIAGNOSTIC_E2E_VALIDATED=True`, `LIVE_MODEL_VALIDATED=False`, `SECURITY_RESEARCH_VALIDATED=False`, `PRODUCTION_READY=False`, `GATE_21_STATUS="PENDING"`, `GATE_04B_STATUS="PENDING"`, `SUBSCRIPTION_OAUTH_STATUS="NOT_IMPLEMENTED"`, all other listed gates `"PASS"` (historical/architectural PASS, explicitly scoped by the docstring to not imply autonomous discovery, live models, or production readiness).

## 10. Confirmed facts vs. unresolved facts

### Confirmed (direct code/DB/test evidence)

1. ARC is the only production research-lifecycle authority actually invoked by the dashboard; it runs inside a `threading.Thread` owned by the dashboard's own Python process (`local_run_supervisor.py:100-111`).
2. There is no persistent daemon, no lease/fencing, no heartbeat, no Preflight subsystem, no `research-osd` anywhere in source (exhaustive grep, zero hits).
3. Hunter/Coverage/Mutation/Protocol/V3-queue/Exploratory-generator code exists, is tested, and is fully disconnected from ARC's production call path; their only production-reachable persistence terminus is either a queue row (`PENDING`/`APPROVED`, never `RUN`) or an audit-event summary.
4. Evidence admission, Candidate creation, Verification, and FindingProposal submission have zero ARC and zero dashboard callers; only `StartHumanReview`/`RecordHumanReview`/`FinalizeFinding` are wired to dashboard operator endpoints.
5. Terminal orchestration state is **not** immutable: `pause()`/`cancel()` perform unconditional `replace()` + `save()` with no terminal-state guard (`autonomous_research_controller.py:788-810`), and the repository update has no compare-and-swap predicate (`data/postgres/repositories.py:2053-2065`).
6. A second implementation capable of writing the same `research_orchestration` row exists: `RunResearchSelection` (`application/run_research_selection.py`), constructed only from `tests/e2e/gate17_harness.py` — not production-reachable today, but a structurally duplicate authority (see Reconnection Audit §9).
7. `execution_attempt` already has DB-unique `request_id` and durable pre-Worker-dispatch commit of `DISPATCHING` state — most of RT-1's intent already exists at the single-attempt level.
8. OAST core semantics + token persistence exist; there is no live external callback adapter (dashboard explicitly reports Interactsh detection as `live_ready=False` — `dashboard.py:904-910`); the only working implementation is a test-only in-memory loopback.
9. A real Playwright/Chromium Worker exists and is wired into the dashboard's ARC composition as of the current uncommitted diff (`PersistentBrowserWorkerAdapter`).

### Unresolved (explicitly UNKNOWN — evidence not obtainable without further work)

1. Whether the currently-configured PostgreSQL instance (if any is running in this environment) matches the `a34` schema head — no live DB connection was exercised as part of this read-only audit beyond the alembic-tool schema-graph check.
2. Whether `RESEARCH_OS_TEST_DATABASE_URL` is set in this environment (several `postgres-integration` tests silently skip without it; this audit did not force-enable them).
3. Live-provider (OpenAI/Anthropic/Gemini) authentication status — no API keys were exercised; ModelPort "available" claims beyond Codex CLI remain unverified beyond static SDK/env-var presence.
4. Whether `var/live-runs/` (untracked, present in the working tree) contains state from a previous manual run of the dashboard in this environment — its contents were not inventoried as part of this audit since it is a runtime artifact directory, not source.
