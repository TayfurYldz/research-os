# Research OS — Implementation Sequence Lock

**Reconciles:** `RESEARCH_OS_MASTER_PLAN.md`, `RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md`, `RESEARCH_OS_PERSISTENT_RUNTIME_PLAN.md` against actual code (per `CURRENT_ARCHITECTURE_SNAPSHOT.md` and the two companion audits).
**Status:** AUDIT — sequencing/design only. No slice below has been implemented.

---

## 1. Gate / maturity normalization table

| Gate id / era | Intended purpose | Implementation status | Validation status | Evidence | Current authoritative maturity implication |
|---|---|---|---|---|---|
| Legacy `GATE 01–03` | Core persistence spine, capability/authorization primitives | IMPLEMENTED | historical unit-test PASS | `maturity.py` flags, `tests/unit/core/` | Architectural PASS only; does not imply live/production readiness |
| Legacy `GATE 04B` | Two benchmark-compatible live model runtimes | PARTIALLY_IMPLEMENTED | **PENDING** (per `maturity.py: GATE_04B_STATUS="PENDING"`, current) | `platform/readiness.py`, benchmark runner exists but tests use fabricated tuples/mocks (`tests/unit/platform/test_model_benchmark*.py` style) — no live comparative run proven in this audit | PENDING stands; do not infer PASS from adapter code existing |
| Legacy `GATE 05–20` | Various infra/planning/domain build-out gates | Mixed IMPLEMENTED/PARTIALLY_IMPLEMENTED per-gate (not individually re-audited beyond what feeds this task) | historical PASS per `maturity.py` | `maturity.py` docstrings explicitly warn against conflating with SD-G numbers of the same digit | Historical PASS; scope limited to what each gate's own criteria covered at seal time |
| Legacy `GATE 21` | Browser worker containment (cgroup/session/process isolation) | PARTIALLY_IMPLEMENTED — real cgroup v2 containment code exists (`worker_runtime/python/browser_containment.py`) but unit tests use mocks; e2e test (`tests/e2e/test_gate21_linux_cgroup.py`) is platform-gated and may skip | **PENDING** (`maturity.py: GATE_21_STATUS="PENDING"`, current) | see above | PENDING stands; a skipped platform-gated e2e run is not evidence of PASS |
| Legacy `GATE 22` | (per `maturity.py` enumeration — final legacy infra gate) | UNKNOWN — not independently re-verified beyond its listing in `maturity.py`; no dedicated sub-agent trace was requested for GATE 22 specifically | per `maturity.py` flag (historical) | `maturity.py` | Treat as historical PASS scope only; do not extend claim beyond documented criteria |
| Attack Period `SD-G1` | Program/scope bootstrap (v2 scope rules, policy, rate limits) | IMPLEMENTED | integration-tested (`tests/integration/test_sd_g1_*` style, `a23_001_program_scope.py`) | migration + tests | Sealed; scope enforcement itself is real (Core-level), this is a legitimate PASS for its own narrow claim |
| `SD-G2` | External scope census (DNS/subdomain) | IMPLEMENTED (fixture-validated) | postgres-integration, file-backed DNS fixtures, **not** live DNS | `tests/integration/test_sd_g2_scope_census.py` | Sealed for its narrow claim; does not prove live external census behavior |
| `SD-G5` | Original 5 HunterFamily registry | IMPLEMENTED (data) | unit-tested resolver logic | `hunter_family_seed.py`, `test_hunter_family_registry.py` | Sealed as data-layer capability; **does not imply ARC execution connectivity** (see Reconnection Audit) |
| `SD-G6` | MutationEngine (concrete variants) | IMPLEMENTED (as a planning/variant generator; execution bridge PLANNING_ONLY) | unit-tested | `research/mutation/engine.py`, `test_mutation_engine.py` | Sealed for variant-generation claim only |
| `SD-G9` | HunterScore / CoverageDebt scheduler | IMPLEMENTED (scheduling logic) | unit + integration | `run_hunt_scheduler.py`, `test_sd_g9_hunterscore_scheduler.py` | Sealed for scheduling-computation claim only; disconnected from ARC |
| `SD-G12` | Broad-injection mutation matrix (9 families) + MutationMatrix | PLANNING_ONLY (by design, per its own docstring) | unit-tested for determinism/shape | `research/mutation/matrix.py`, `test_sd_g12_mutation_matrix.py` | Sealed as a planning-artifact claim; never claimed execution capability — no contradiction here, just must not be conflated with "attack capability live" |
| `SD-G13` | Protocol specialists (smuggling/desync, cache poisoning) | PLANNING_ONLY | unit-tested plan-shape | `research/protocol/parser_plan.py` | Sealed as planning-artifact claim only |
| `SD-G15` | Live coverage / change-recall consolidation | PARTIALLY_IMPLEMENTED — unit proves computation; postgres-integration proves persistence with a **stub** coverage view, skips without `RESEARCH_OS_TEST_DATABASE_URL` | unit + conditionally-run integration | `tests/unit/research/coverage/test_sd_g15_live_coverage.py`, `tests/integration/test_sd_g15_live_coverage.py` | Sealed for its own claim; does not prove a real graph/registry-backed coverage rebuild |
| `SD-G16` | Exploratory hypothesis generator | PARTIAL_EXECUTION (per Reconnection Audit §6) | unit-tested | `research/exploratory.py`, `draft_exploratory_hypothesis.py` | Sealed for hypothesis-drafting claim; family-promotion path explicitly not implemented |
| `MR-1..MR-6` (Hunter Reconnection plan's own gates) | Opportunity unification through exploratory-execution reconnection | **NOT_PRESENT** — none of MR-1 through MR-6 have any implementing code yet; the plan document itself is aspirational | N/A | Reconnection Audit §2–§7 | PENDING; this audit is the first evidence-based checkpoint for these |
| `RT-1..RT-5` (Persistent Runtime plan's own gates, e.g. execution journal, lease, preflight, daemon, dashboard-as-client) | Runtime durability/liveness | RT-1 (execution journal) PARTIALLY_IMPLEMENTED (see Runtime Gap Audit §4); RT-2 (lease/fencing) NOT_PRESENT; RT-3 (crash classification) PARTIALLY_IMPLEMENTED but unwired; RT-4 (Preflight) NOT_PRESENT as a unified concept; RT-5 (daemon) NOT_PRESENT | N/A | Runtime Gap Audit §4–§8 | PENDING across the board except RT-1's substrate |

**Rule applied throughout:** no PASS was inferred anywhere in this table from feature existence alone; every PASS cited is either a pre-existing `maturity.py` historical flag or explicitly scoped to "sealed for its own narrow claim."

---

## 2. Disconnected organs table (proves/disproves the diagnosis)

| Component | Current producer | Current consumer | Expected lifecycle position | Connection status | Missing bridge | Severity | Evidence |
|---|---|---|---|---|---|---|---|
| SurfaceDiscovery | `application/discovery/runner.py` (uncommitted) | Dashboard-initiated `SurfaceDiscoveryStart` → one ARC tick, then cleared | Feeds ResearchOpportunity | PARTIAL — wired for a single discovery step, not continuous | Recurring discovery scheduling | Medium | `local_run_supervisor.py` diff, `dashboard.py` diff |
| ResearchOpportunity | `select_research_opportunities.py` (diagnostic only) | ARC's `ProposeResearchHypothesis` | Common currency for all research inputs | CONFIRMED DISCONNECTED from Hunter path | `HunterCoverageOpportunitySource` (MR-1) | **High** | Reconnection Audit §2 |
| HunterScore | `research/scheduler/score.py` via `RunHuntScheduler` | Only the Hunter path's own `RunHuntCycle` | Should inform ARC opportunity ranking | CONFIRMED DISCONNECTED | MR-1 | **High** | Reconnection Audit §2 |
| CoverageDebt | `research/coverage/debt.py` | `RunHuntScheduler` only | Should inform ARC opportunity ranking | CONFIRMED DISCONNECTED | MR-1 | **High** | Reconnection Audit §2 |
| HunterFamily Registry | `a29` seed + `hunter_family_seed.py` (16 families) | `HunterFamilyRegistry` resolver (test/CLI only) | Should compile to ExperimentPlan | CONFIRMED DISCONNECTED from execution | MR-2 (compiler registry) | **High** | Reconnection Audit §4 |
| Generator/Falsifier | `research/cycle.py` | ARC only | Model-assisted hypothesis reasoning | CONNECTED (this one works as designed) | none | — | ARC call graph §1 |
| Mutation Engine | `research/mutation/engine.py` | `RecordMutationVariants` (audit-only terminus) | Should reach ExperimentPlan | CONFIRMED DISCONNECTED (variant→intent bridge exists but is test-only) | Compiler wiring (MR-2/MR-3) | **High** | Reconnection Audit §4 |
| Broad Injection Wave (SD-G12 matrix) | `research/mutation/matrix.py` | `hunt_validation._v3_arguments_for_family` (metadata-only) | Should reach ExperimentPlan cell-by-cell | CONFIRMED DISCONNECTED (planning-only by current design) | Cell compiler (MR-2/MR-3) | **High** | Reconnection Audit §4 |
| Protocol Specialist | `research/protocol/parser_plan.py` | `hunt_validation._v3_arguments_for_family` (metadata-only) | Per-step Core-reauthorized execution | CONFIRMED DISCONNECTED | Step compiler (MR-3) | **High** | Reconnection Audit §5 |
| V3 Queue | `hunt_validation.py` | `ApproveHuntV3Queue` (state→APPROVED only) | Should reach fresh Core authorization + Worker dispatch | CONFIRMED DISCONNECTED past APPROVED | Dispatch use case (MR-3) | **Critical** (approved-but-unexecutable work with no path forward at all) | Reconnection Audit §3 |
| Exploratory Hypothesis Generator | `research/exploratory.py` | Visible to ARC context only, no compile/execute path, no family-promotion consumer | Ephemeral testing + human-gated permanent promotion | PARTIAL_EXECUTION | Run-scoped compiler + promotion workflow (MR-5) | Medium | Reconnection Audit §6 |
| ImpactGraph | `research/impact/chain.py` | `SubmitFindingProposal` (nodes only) | Proof-bounded chaining substrate | CONNECTED for nodes; edges unproven (defect, not disconnection) | proof_refs on edges | Medium (epistemic, not connectivity) | Reconnection Audit §7 |
| Evidence Admission | `admit_diagnostic_evidence.py` | test-only | First promotion-pipeline hop after Assessment | CONFIRMED DISCONNECTED from ARC/dashboard | Promotion trigger (MR-4) | **High** | Reconnection Audit §7 |
| Candidate | `propose_candidate.py` | test-only | Second promotion hop | CONFIRMED DISCONNECTED from ARC/dashboard | MR-4 (cascades from Evidence trigger) | High | Reconnection Audit §7 |
| Verification | `start/complete_candidate_verification.py` | test-only | Independent re-test hop | CONFIRMED DISCONNECTED from ARC/dashboard | MR-4 | High | Reconnection Audit §7 |
| FindingProposal | `submit_finding_proposal.py` | test-only for submission; dashboard for review/finalize | Human-facing proposal | Submission disconnected; review/finalize CONNECTED (manual) | MR-4 for submission trigger | High (submission side only) | Reconnection Audit §7 |
| HumanReview | `start/record_human_review.py` | Dashboard operator endpoints | Human gate | **CONNECTED** (manual trigger, by design — this is correct, not a defect) | none | — | Reconnection Audit §7 |
| AutonomousResearchController | see ARC call graph | dashboard (only production caller) | Sole research-semantic owner | CONNECTED, and confirmed the *only* one in production | none | — | Snapshot §4 |
| LocalRunSupervisor | `local_run_supervisor.py` | dashboard | Should be a thin scheduling shim under a persistent supervisor | CONNECTED to ARC, but itself has no persistent owner (see Runtime Gap Audit) | research-osd / lease (RT-2/RT-5) | **Critical** (operational liveness gap) | Runtime Gap Audit §1–§3 |
| dashboard lifecycle | `dashboard.py` | operator (human, via HTTP) | Should become a thin client to research-osd | Currently the runtime owner itself, not a client | RT-5 | **Critical** | Runtime Gap Audit §1 |
| ModelPort | `integrations/models/*` | ARC (Generator/Falsifier) | Untrusted reasoning input | CONNECTED for reasoning; readiness claims narrower than "available" (see below) | Live benchmark validation (GATE 04B) | Medium (maturity overstatement risk, not wiring) | Snapshot §9, ModelPort sub-agent trace |
| WorkerPort | `platform/persistent_browser_worker.py`, `platform/local_process_worker.py` | ARC via `ExecutePlannedExperiment` | Bounded execution | CONNECTED | none | — | ARC call graph §1 |
| OAST | `research/oast/` core + `oast_token` table | test loopback fixture only in production tests; no live adapter | Out-of-band evidence channel | core CONNECTED to Evidence-adjacent discovery-fact path; **live adapter NOT_PRESENT** | Live OAST integration (e.g. Interactsh client) | High (capability gap, not a wiring defect — nothing to wire to yet) | Snapshot §10, OAST sub-agent trace |

**Verdict on the "disconnected organs" diagnosis: CONFIRMED, with precision.** It is not that the codebase is broadly incoherent — Core, ARC's own path, Worker execution, and the human-review tail of promotion are all genuinely well-connected and well-tested. The diagnosis is precisely correct for exactly the components the reconnection plan targets: Hunter/Coverage/Mutation/Protocol/V3/Exploratory-family-promotion, and the middle of the promotion pipeline (Evidence→Candidate→Verification→FindingProposal-submission).

---

## 3. Duplicate brains / duplicate authorities

| Decision | Modules found | Classification |
|---|---|---|
| Next research opportunity | `SelectResearchOpportunities` (ARC path) vs. `RunHuntScheduler` (Hunter path) | **POTENTIAL DUPLICATE AUTHORITY** — both decide "what to research next" for a run today, but they do not currently write to overlapping decision state simultaneously in production (Hunter path has no production caller at all). Classified potential, not confirmed, because they cannot yet collide in practice. Becomes a real risk the moment MR-1 is implemented unless the unification explicitly merges them into one ranked pool (as MR-1 proposes) rather than running them independently against the same run. |
| Run lifecycle state (`research_orchestration` row) | `AutonomousResearchController` (production path) vs. `RunResearchSelection` (`application/run_research_selection.py`, only constructed from `tests/e2e/gate17_harness.py`) | **CONFIRMED DUPLICATE AUTHORITY, but test-harness-scoped.** `RunResearchSelection` independently inserts and repeatedly `save()`s `ResearchOrchestrationRecord` for a run, using the same table and same repository as ARC, via a parallel bounded loop that calls `PreparePlannedExperiment`/`ExecutePlannedExperiment`/`EvaluateExperimentFeedback` directly without going through the model/ARC layer. It is not reachable from the dashboard or CLI (confirmed by constructor grep — see snapshot §10 fact 6), so it cannot collide with ARC in current production use, but it is real, working, duplicate-authority code sitting in `application/`, not `tests/`. This should be explicitly resolved (moved under `tests/` as harness support, or formally retired) in the next phase rather than left as latent risk. |
| Execution permission | `evaluate_execution()` (Core) — single call site pattern, invoked identically by `ExecutePlannedExperiment` and by `RunResearchSelection`'s own execution step | **NONE** — both callers still go through the same Core function; this is intentional composition/reuse, not duplicate authority, even though `RunResearchSelection` is itself a duplicate orchestrator. |
| Side-effect / budget / scope allowance | Only `core/execution.py`, `core/budget.py`, `core/scope.py` | **NONE** |
| Finding truth | Only `finalize_finding.py` + `core/approval.py` | **NONE** |
| Candidate validation | Only `research/candidate.py` + `complete_candidate_verification.py` | **NONE** |
| Runtime ownership (who may tick a run) | `LocalRunSupervisorRegistry` (in-process only) — no second implementation found | **NONE today** (would become **POTENTIAL DUPLICATE AUTHORITY** the moment a second dashboard-like process is run against the same DB, per Runtime Gap Audit §3 — this is a concurrency gap, not a second codebase deciding differently) |

---

## 4. Required invariant table

| Invariant | Intended owner | Enforcement location | DB enforcement? | Application enforcement? | Test evidence | Current status |
|---|---|---|---|---|---|---|
| Scope cannot expand outside Core | Core | `core/scope.py`, `core/scope_compiler.py` | Partial (`scope_rule_v2` table stores compiled rules; expansion itself is a code-path property, not a constraint) | Yes — `evaluate_execution()` calls `check_scope()` fresh per attempt | `tests/unit/core/test_scope.py`, `test_scope_compiler*.py` | IMPLEMENTED |
| Model cannot authorize | Core / ModelPort boundary | ModelPort returns only proposal text/structured output; `evaluate_execution()` never takes model output as an authorization input | N/A (architectural) | Yes — model output flows only into Hypothesis/Plan content, never into `ExecutionDecision` | `tests/unit/core/*` (Core tests never accept model-shaped input) | IMPLEMENTED |
| Worker cannot self-authorize | Core / WorkerPort boundary | `WorkerPort.invoke()` receives an already-authorized dispatch; returns only `WorkerResult` | N/A | Yes — `execute_planned_experiment.py` calls `evaluate_execution()` before ever constructing the Worker call | direct code trace, ARC call graph | IMPLEMENTED |
| WorkerResult cannot become Evidence directly | Epistemic pipeline | `research/evidence.py` admission gates require assessment/observation lineage, not raw WorkerResult | Table separation (`worker_result` vs `evidence` are distinct tables with no direct FK bypass) | Yes — `AdmitDiagnosticEvidence` requires an `HypothesisAssessmentRecord`, not a raw `WorkerResultRecord` | `tests/unit/research/test_evidence.py`-style suites (per sub-agent trace) | IMPLEMENTED |
| Operational failure != hypothesis falsification | Epistemic pipeline | `evaluate_experiment_feedback.py` outcome mapping | N/A | Yes — distinct outcome codes for `UNSUPPORTED` vs. operational/timeout/insufficient results | `tests/unit/application/test_evaluate_experiment_feedback.py` | IMPLEMENTED |
| UNKNOWN_OUTCOME not automatically retried | Runtime / Core | `_mark_unknown`/`_fail_closed_existing` (`execute_planned_experiment.py`) + `ReconcileResearchRun` classifying side-effectful UNKNOWN_OUTCOME as `REQUIRE_HUMAN_REVIEW` | CHECK constraint allows the state; no DB-level retry logic exists (retry is an application decision) | Yes for the "don't silently retry" direction; `ReconcileResearchRun`'s enforcement is **built but unwired** (see Runtime Gap Audit §5) | `tests/unit/application/test_reconcile_research_run.py` | PARTIALLY_IMPLEMENTED (logic correct, not wired into the live start path) |
| Terminal state immutable | Runtime | *intended*: `TERMINAL_ORCHESTRATION_STATES` guard | No (`save()` has no state predicate) | **No** — `pause()`/`cancel()` have no guard (confirmed defect) | No test covers "cancel a COMPLETED run" | **PENDING / CONFIRMED DEFECT** (Runtime Gap Audit §6) |
| Duplicate execution prevented | Application / Core | `request_id` uniqueness (`uq_execution_attempt_request_id`) + `_fail_closed_existing` pre-authorize check | Yes — DB unique constraint | Yes | inferred from `execute_planned_experiment.py` logic; no dedicated adversarial test found for the double-authorize race specifically | PARTIALLY_IMPLEMENTED (DB constraint is real; no test proves the race is actually closed under concurrency) |
| Stale runtime owner cannot mutate run | Runtime | *intended*: lease/fencing | No | No | No | **NOT_PRESENT** (Runtime Gap Audit §7) |
| Human approval required for Finding | Core / Human Review | `finalize_finding.py` requires `Approval` bound to a `HumanReview` decision by a `HUMAN_OPERATOR` actor | Yes — `finding` table FKs to `approval_id`/`human_review_id`, non-null | Yes — `check_approval()`/`finalize_finding.py` gate | Gate 15 e2e harness explicitly tests "human approval before Finding" | IMPLEMENTED |
| Permanent HunterFamily cannot be model-written | Data / Application | Only `a29` migration's `bulk_insert` writes `hunter_family`; no application use case calls `uow.hunter_families.insert(...)` | Yes, by omission — no application code path exists to write this table at all today | N/A (nothing to enforce against, since nothing writes it) | N/A | IMPLEMENTED (trivially, by absence of any writer — but also means the "promote exploratory pattern → family, human-reviewed" feature literally does not exist yet, see Reconnection Audit §6) |
| Approval != execution authorization | Core | `evaluate_execution()` is re-evaluated fresh for every `ExecutePlannedExperiment` call; an `Approval` row satisfies the Human-Review requirement for Finding creation, not for any future Worker dispatch | N/A | Yes — no code path reads `approval` table to skip `evaluate_execution()` | direct trace of `evaluate_execution()` inputs | IMPLEMENTED |
| AttackSurfaceGraph does not grant scope | Core / Research | `attack_surface_snapshot` is a rebuildable summary table consumed nowhere as a scope input | N/A | Yes — no code path treats surface-graph membership as a scope decision (`check_scope()` reads only `scope_rule_v2` compiled rules) | UNKNOWN — no dedicated adversarial test found proving surface-graph membership is *rejected* as a scope justification; absence of a positive code path is the evidence, not a negative test | PARTIALLY_IMPLEMENTED (architecturally sound by omission; not test-proven) |
| Budget cannot be silently increased | Core | `core/budget.py` — `check_budget()` compares consumption against the originally `issued_budget` row; no code path increases a `max_*` field after issuance | Partial — no UPDATE statement touching `issued_budget.max_*` columns was found anywhere in `src/` | Yes | `tests/unit/core/test_budget.py` | IMPLEMENTED |
| Dashboard payload cannot override authoritative run config | Application | `command_factory` in `dashboard.py` builds a `StartAutonomousResearchCommand` from operator payload, but budgets/scope/authorization are resolved from `research_run_id`-linked DB rows inside `ExecutePlannedExperiment`/Core, not from the HTTP payload | N/A | Yes for budget/scope/authorization specifically; **UNKNOWN** whether every field on `StartAutonomousResearchCommand` (e.g. `surface_discovery` target) is independently re-validated against scope before use, versus trusted from the operator payload — the discovery-seeded path is new/uncommitted and was not exhaustively traced for this specific invariant | Not found | PARTIALLY_IMPLEMENTED / UNKNOWN for the new discovery-seeding path specifically — flagged as an open question below |

---

## 5. Recommended ordered implementation slices

Each slice is additive, reuses existing code per the two companion audits, and does not touch anything not listed. None of these have been implemented as part of this audit.

### Slice 0 — Terminal-state immutability + wire the existing reconciler
- **Objective:** Close the confirmed terminal-state mutation defect (Runtime Gap Audit §6) and give crash recovery an actual production caller (Runtime Gap Audit §5).
- **Reason for ordering first:** Zero new schema, zero new concepts, smallest possible diff, removes a live correctness bug, and every later runtime slice (lease, daemon) is safer to build once terminal states are actually terminal.
- **Existing components reused:** `TERMINAL_ORCHESTRATION_STATES`, `ReconcileResearchRun`.
- **New components required:** none (guard clauses + one new call site).
- **Schema impact:** none.
- **Production files:** `autonomous_research_controller.py`, `data/postgres/repositories.py`, `research_run_control.py`.
- **Tests:** the two RT-A/RT-B tests listed in Runtime Gap Audit §12.
- **Rollback boundary:** revert the guard clauses; no data migration to undo.
- **PASS criteria:** cancel/pause on a terminal run is rejected or is a verified no-op; a simulated crash-left `RUNNING` run is reconciled before a new supervisor attaches.
- **Hard-fail criteria:** any change that makes `pause`/`cancel` silently succeed without persisting a rejection/no-op signal; any change that makes the reconciler auto-retry a side-effectful `UNKNOWN_OUTCOME`.
- **Dependencies:** none.

### Slice 1 — Minimal lease/fencing on `research_orchestration`
- **Objective:** Close the confirmed concurrent-attach gap (Runtime Gap Audit §3, §7).
- **Reason for ordering:** Must exist before any persistent daemon is introduced (Slice 4), since a daemon without a lease only widens the race window.
- **Existing components reused:** `research_orchestration` table/record (extended, not replaced), `LocalRunSupervisorRegistry`.
- **New components required:** `owner_runtime_instance_id`, `lease_epoch`, `lease_expires_at` columns; a small lease-acquire/renew/release helper.
- **Schema impact:** one additive migration (`aXX_lease_fields`).
- **Production files:** `data/records.py`, `data/postgres/tables.py`, `data/postgres/repositories.py`, `local_run_supervisor.py`, `research_run_control.py`.
- **Tests:** the two RT-C tests in Runtime Gap Audit §12.
- **Rollback boundary:** migration is additive-only (new nullable columns); can be reverted by a down-migration without data loss to pre-existing columns.
- **PASS criteria:** two simulated concurrent attachers produce exactly one active owner; a stale lease is legitimately superseded.
- **Hard-fail criteria:** any lease design that allows a superseded owner's writes to still land after supersession; any design that requires the model to participate in lease decisions.
- **Dependencies:** Slice 0 (terminal-state guard should exist before lease renewal logic is added, so the two don't need to be reasoned about simultaneously).

### Slice 2 — Preflight aggregation
- **Objective:** Give `start()` one coherent go/no-go report instead of fragmented per-attempt-only checks (Runtime Gap Audit §8, §10).
- **Reason for ordering:** Cheap, additive, and directly enforces the master plan's authorization-boundary invariant ("do not start active testing if AuthorizationSource or effective scope is missing") at the point of operator action rather than only at first Worker dispatch.
- **Existing components reused:** `RuntimeReadiness`, scope/authorization/budget checks from Core.
- **New components required:** `application/preflight.py` aggregator only.
- **Schema impact:** none (or a thin `preflight_report` audit-event payload — no new table strictly required).
- **Production files:** new `application/preflight.py`; `research_run_control.py` calls it before `start()` proceeds.
- **Tests:** the RT-D test in Runtime Gap Audit §12.
- **Rollback boundary:** trivial (single new use case, one call site).
- **PASS criteria:** start is denied with a clear reason when AuthorizationSource/scope/budget is missing, before any Worker or model call happens.
- **Hard-fail criteria:** Preflight silently defaulting to "proceed" on ambiguous/missing data (must default DENY/REQUIRE_HUMAN_REVIEW per master-plan authorization boundary).
- **Dependencies:** none (parallelizable with Slice 1).

### Slice 3 — Unified opportunity source (MR-1)
- **Objective:** Make Hunter/Coverage-sourced opportunities visible to ARC's existing, unmodified opportunity selector.
- **Reason for ordering:** This is the single highest-leverage reconnection step and every subsequent Hunter-side slice (2, 3 below) depends on opportunities actually reaching ARC.
- **Existing components reused:** `research_opportunity`/`research_selection` tables, `SelectResearchOpportunities` (read side unchanged), `RunHuntScheduler`, `compute_coverage_debt`.
- **New components required:** `HunterCoverageOpportunitySource` (new, small, write-side only).
- **Schema impact:** none (uses existing `research_opportunity` table).
- **Production files:** new `application/hunter_coverage_opportunity_source.py`; no change required to `select_research_opportunities.py` itself if it already reads generically (must be re-verified against the exact read query at implementation time, not assumed).
- **Tests:** the MR-1 regression test in Reconnection Audit §11.
- **Rollback boundary:** disable/remove the new producer; ARC's diagnostic-only behavior is unaffected since nothing about the read path changes.
- **PASS criteria:** a Hunter-sourced opportunity is selectable by the unmodified ARC selection logic without altering diagnostic-opportunity precedence in any existing test.
- **Hard-fail criteria:** any change that makes Hunter opportunities bypass `select_research_opportunities`'s existing admission/dedup logic, or that requires modifying ARC's `step()` control flow itself.
- **Dependencies:** Slice 0 recommended first (general hygiene), not strictly required.

### Slice 4 — Experiment compiler registry + V3/Mutation/Protocol dispatch bridge (MR-2 + MR-3)
- **Objective:** Give known HunterFamily/Mutation-cell/Protocol-step work a deterministic path to `ExperimentPlan` and close the V3 `APPROVED` dead end.
- **Reason for ordering:** Depends on Slice 3 existing conceptually (opportunities feeding ARC) but is independently useful even before Slice 3 lands, since it also serves the existing `hunt_validation.py` metadata-discarding call sites. Must come before any broader autonomous-hunter expansion since it is the actual bridge to Core/WorkerPort.
- **Existing components reused:** `compile_experiment_intent()`, `PreparePlannedExperiment`, `ExecutePlannedExperiment` (unmodified — fresh Core authorization per dispatch), `hunter_family_seed.py`, `MutationMatrixCell`, `ProtocolParserPlanStep`, `ApproveHuntV3Queue`.
- **New components required:** `ExperimentCompilerRegistry`, family/cell/step-specific compilers, one new `application/dispatch_approved_v3_queue.py` use case.
- **Schema impact:** likely none (uses existing `experiment_plan`, `execution_attempt`); possible additive column on `hunt_v3_queue` if dispatch provenance needs tracking beyond `state`.
- **Production files:** `hunt_validation.py` (stop discarding cells/steps once a compiler exists), new registry + compiler modules, `hunt_v3_queue_approval.py`-adjacent new dispatch use case.
- **Tests:** the MR-2/MR-3 tests in Reconnection Audit §11, including the explicit "approval is not authorization, re-checked fresh" adversarial test.
- **Rollback boundary:** the dispatch use case can be disabled without affecting existing `PENDING`/`APPROVED` queue semantics (they remain valid states either way).
- **PASS criteria:** an `APPROVED` V3 item reaches a real `ExecutionAttemptRecord` exactly once, authorized fresh by Core at dispatch time, not by the historical approval alone.
- **Hard-fail criteria:** any design where the V3 `Approval`/human-review step itself becomes the execution authorization (explicitly forbidden by master-plan §1 CORE rules — "a human approval artifact must NEVER become permanent execution authorization").
- **Dependencies:** Slice 3 (conceptually), Slice 0.

### Slice 5 — Promotion trigger (MR-4)
- **Objective:** Automatically attempt Evidence admission after a `SUPPORTED` assessment, without touching the human-controlled tail (Candidate/Verification/FindingProposal remain separately invoked exactly as today, unless the operator/next-phase decides otherwise).
- **Reason for ordering:** Independent of the Hunter-reconnection slices; can land in parallel with Slice 3/4, but is sequenced after Slice 0 (terminal-state hygiene) since it adds a new automatic write path off of ARC's cycle completion.
- **Existing components reused:** `AdmitDiagnosticEvidence`, `EvaluateExperimentFeedback`'s existing outcome codes.
- **New components required:** one small hook/call in ARC (or a thin `PromotionPipeline.on_assessment()`), invoked only for `SUPPORTED` outcomes.
- **Schema impact:** none.
- **Production files:** `autonomous_research_controller.py` (one new call after assessment persistence), possibly a new thin `application/promotion_pipeline.py` wrapper.
- **Tests:** the MR-4 test in Reconnection Audit §11.
- **Rollback boundary:** remove the single call site; Evidence admission reverts to manual/test-only invocation.
- **PASS criteria:** exactly one Evidence-admission attempt per `SUPPORTED` assessment, none for `UNSUPPORTED`/`INCONCLUSIVE`.
- **Hard-fail criteria:** any design that also auto-invokes Candidate creation, Verification, or FindingProposal submission — the master plan and this audit deliberately keep those manually/human-gated until a separate, explicitly-approved decision is made to automate further.
- **Dependencies:** Slice 0.

### Slice 6 — Epistemic hardening: ImpactGraph edge proof + severity bound
- **Objective:** Fix the two confirmed epistemic defects (Reconnection Audit §7): unproven ImpactGraph edges, and caller-supplied severity fields exceeding Evidence.
- **Reason for ordering:** Independent of runtime/reconnection work; should land before any slice that increases autonomous Finding-adjacent throughput (i.e., before or alongside Slice 5), since Slice 5 increases the volume of Evidence flowing toward eventual Candidates/Findings.
- **Existing components reused:** `research/impact/chain.py`, `application/impact/proof_resolver.py`, `score_finding_severity.py`.
- **New components required:** none structurally — additive validation + one additive column.
- **Schema impact:** additive migration for `impact_chain_edge.proof_refs`.
- **Production files:** `research/impact/chain.py`, `alembic/versions/aXX_impact_edge_proof.py`, `score_finding_severity.py`, `research/validation/severity.py`.
- **Tests:** the two epistemic tests in Reconnection Audit §11.
- **Rollback boundary:** additive column, safe to leave nullable and unenforced if reverted.
- **PASS criteria:** edges without resolvable proof are rejected; severity cannot exceed the class supported by admitted Evidence/ImpactGraph nodes from caller input alone.
- **Hard-fail criteria:** weakening node-level proof requirements while "fixing" edges (must only add rigor, not relax existing checks).
- **Dependencies:** none (fully independent; can run first or in parallel with everything above).

### Slice 7 — Exploratory execution + permanent-family promotion (MR-5)
- **Objective:** Let exploratory hypotheses execute in a run-scoped, ephemeral manner and add the missing human-gated permanent-HunterFamily promotion workflow.
- **Reason for ordering:** Last, because it depends on the compiler registry (Slice 4) for ephemeral execution and introduces the one genuinely new human-review workflow this audit found missing outright (no existing code to reuse for family promotion).
- **Existing components reused:** `draft_exploratory_hypothesis.py`, `research/exploratory.py` metadata flags, Slice 4's compiler registry, `HumanReview`/`Approval` machinery pattern (new use case, same pattern as `FinalizeFinding`).
- **New components required:** run-scoped ephemeral compiler adapter enforcing `may_write_hunter_registry=False`; a new `PromoteExploratoryFamily` human-review use case (genuinely new, not a rewire).
- **Schema impact:** likely none beyond what Slice 4 adds; possibly a new `family_promotion_review` table if promotion needs its own audit trail distinct from `human_review` (design decision for implementation time, not this audit).
- **Production files:** new compiler adapter, new `application/promote_exploratory_family.py`.
- **Tests:** exploratory-execution and family-promotion tests (not yet specified in detail — this audit only established that no such tests exist today; the next phase must design them).
- **Rollback boundary:** new, isolated use cases; disabling them leaves exploratory hypotheses exactly as informative-only, as they are today.
- **PASS criteria:** an exploratory hypothesis can be tested without writing `hunter_family`; a permanent family write requires an explicit human-review decision, never a model or automatic write.
- **Hard-fail criteria:** any path that allows `may_write_hunter_registry` to be set true by model output or by default.
- **Dependencies:** Slice 4.

---

## 6. Unresolved questions that genuinely block implementation (not merely follow-ups)

1. Whether `select_research_opportunities.py`'s read path is already fully generic (reads any `ResearchOpportunityRecord` regardless of `opportunity_kind`/producer) or has a diagnostic-only filter baked in — this determines whether Slice 3 truly requires zero changes to the read side, and was not verified to the exact-query level in this audit.
2. The exact current behavior of `prepare_start` (referenced in `research_run_control.py`) — whether it already performs any of the Preflight-shaped checks Slice 2 would add, which would change Slice 2's scope from "new" to "extend existing."
3. Whether `PersistentBrowserWorkerAdapter` exposes any standalone health/probe method usable by a future Worker-probe Preflight check, or whether one must be added to the Worker port itself.
4. Whether the newly-introduced (uncommitted) `surface_discovery` operator payload path independently re-validates scope before use, or trusts the dashboard-constructed command — this bears directly on the invariant "dashboard payload cannot override authoritative run config" and was left PARTIALLY_IMPLEMENTED/UNKNOWN above.
5. Whether a PostgreSQL instance matching the `a34` head is actually reachable in this environment (no live DB connection was exercised in this read-only audit) — this affects whether Slice 0 onward can be validated with real integration tests immediately or requires environment setup first.
6. The intended disposition of `RunResearchSelection`/`gate17_harness.py` — retire, formally relocate under `tests/`, or keep as a second-tier non-model bounded loop for a defined purpose. This is a duplicate-authority risk (§3 above) that the operator should explicitly resolve before Slice 3/4 make Hunter-path opportunities richer (a richer, disconnected second loop is a bigger risk than today's near-empty one).
