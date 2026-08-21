# Slice 4 Completion Record — Compiler registry + V3/Mutation/Protocol dispatch

Status: CLOSED with split qualification (see §Qualification). Implemented as three internal checkpoints (4A / 4B / 4C). No operator stop between them: no architectural contradiction and no hard-fail on the V3-approval-as-authorization criterion.

Naming collision, stated once: `IMPLEMENTATION_SEQUENCE_LOCK.md` calls this slice **MR-2 + MR-3**, and calls promotion **MR-4** (Slice 5). The operator checkpoint names this slice **4A/MR-2, 4B/MR-3, 4C/MR-4**, where 4C/MR-4 means the V3 consumer + protocol fail-closed path, **not** promotion. This record uses both labels explicitly. Slice 5 (promotion trigger / lock MR-4) is **not** this work.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 4 — Experiment compiler registry + V3/Mutation/Protocol dispatch bridge (MR-2 + MR-3)" (campaign Phases E+F). Fifth slice implemented this campaign; depends conceptually on Slice 3 (already closed / MR-1 qualified).

## Repository-grounded split (operator override of a binary PASS/FAIL)

The operator required that this slice **not invent Worker semantics** to fake MR-3 / protocol PASS:

- Complete MR-2 now for families whose execution is already grounded.
- For mutation: compile a `MutationMatrixCell` onto an existing typed primitive only if a deterministic mapping is derivable from repo semantics. Otherwise fail closed. Do **not** count a family as MR-3 PASS without that mapping.
- For protocol: audit whether `http.transaction` can preserve wire semantics (CL/TE conflict, raw boundaries, connection reuse, exact bytes). If not, fail closed and write a design doc; do not fake smuggling through `http.transaction`.
- Implement the generic V3 consumer anyway: `APPROVED → compile | BLOCKED_UNSUPPORTED → fresh Core auth when compiled → exactly one ExecutionAttempt`. Approval ≠ authorization. Unsupported families must never silently succeed or be marked covered.

That split is what landed. Per-gate status is in §Qualification.

## What the repository actually had (audit, not the reconnection-doc claim)

- `compile_experiment_intent()` (`src/research_os/research/compiler.py`) already binds capability/action/version/fingerprint and refuses to understate side-effect. It does not authorize. Planners exist for diagnostic-echo, authorization-differential, state-transition, and a generic `plan_admitted_hypothesis` that only fills a `message` argument.
- Real Worker capabilities (`src/research_os/tools/capabilities.py`): `http.authorization.differential` / `probe`, `http.state_transition` / `probe`, `http.transaction` / `read|mutate`. Contracts under `src/research_os/resources/contracts/v1/capabilities/`.
- V3 queue planning **aliases** in `src/research_os/application/hunt_validation.py` are **not** Worker capabilities:
  - `OBJECT_AUTHORIZATION` → `http.authorization_differential` (wrong id; real is `http.authorization.differential`)
  - `WORKFLOW_STATE_TRANSITION` → `http.state_transition_authorization` (wrong id; real is `http.state_transition`)
  - 9 injection families → `mutation.matrix` (does not exist)
  - 2 protocol families → `protocol.parser` (does not exist)
- `MutationMatrixCell` is a Cartesian `(dimension_values, control)` with **no payload**. `MutationEngine` families already emit concrete `http.transaction` `MutationVariant`s; `mutation_variant_to_intent()` existed but used `variant_id` as `hypothesis_id` (test-only).
- Protocol plans (`src/research_os/research/protocol/parser_plan.py`) are abstract steps. `http.transaction` is one normalized request, `max_requests=1`, client-owned framing — it cannot express CL.TE / desync / raw bytes.
- `HuntV3QueueRecord` states: `PENDING | APPROVED | RUN | BLOCKED`. `ApproveHuntV3Queue` only sets `APPROVED`. **No consumer of APPROVED existed.** `RUN` was declared and unreachable.
- `ExecutePlannedExperiment` for HTTP-scope capabilities requires `CompiledScope`. A naive `ScopeEvaluationInput(ALLOW)` is not enough. That is the correct "approval ≠ authorization" behavior and is preserved.

The reconnection audit's "mutation-matrix-cell compiler bridges `MutationMatrixCell` → concrete arguments" was therefore **not implementable from repository semantics**. Repository evidence overrides the audit claim. Cells are persisted; compilation of those cells fail-closes.

## Checkpoints

### 4A / lock MR-2 — deterministic Compiler Registry

New `src/research_os/research/compiler_registry.py` (research layer; no `research_os.application` / `research_os.data` imports).

- `CompilerRequest` / `CompilerResult` / `CompilerOutcome`: `COMPILED | BLOCKED_UNSUPPORTED_CAPABILITY | BLOCKED_MISSING_SEMANTICS | BLOCKED_INVALID_INPUT`.
- Lookup: (1) known `family_name` → that compiler, never generic; (2) else if `arguments` has `mutation_rule_id` → `MutationVariantCompiler`; (3) else `GenericPlannerCompiler`.
- `AuthorizationDifferentialCompiler` (`authorization_differential.v1`) wraps `plan_authorization_differential`. Required: origin/actor/own_object/cross_object; mode defaults to `vulnerable`.
- `StateTransitionCompiler` (`state_transition.v1`) wraps `plan_state_transition`. Required: origin/actor/resource_id/transition; area defaults to `workflow`.
- `GenericPlannerCompiler` rejects `PLANNING_ALIAS_CAPABILITIES` (`mutation.matrix`, `protocol.parser`, `http.authorization_differential`, `http.state_transition_authorization`). Can compile a real Worker capability, or `plan_admitted_hypothesis` when proposal+challenge are present. `requested_side_effect=0` on state-transition → `RISK_UNDERSTATEMENT` via `compile_experiment_intent`.
- `assert_plan_not_understated(plan)` re-checks compiled side-effect against the capability registry.
- Planning aliases on the V3 **queue row** are left unchanged (historical tests assert `http.authorization_differential`). The compiler **translates** via `family_name`, never by passing the alias into `compile_experiment_intent`.
- `plan_admitted_hypothesis` is not deleted. Known families must not use it for active execution; tests prove OBJECT_AUTHORIZATION / WORKFLOW_STATE_TRANSITION bypass it even when diagnostic-echo arguments are present.

Mutation/protocol compilers live in the same module because the registry is one composition root. Their **execution** qualification is 4B/4C, not 4A.

### 4B / lock MR-3 (partial) — MutationMatrix persistence + fail-closed cell compile

- `MutationMatrixCellCompiler` — **always** `BLOCKED_MISSING_SEMANTICS` / `MUTATION_MATRIX_CELL_HAS_NO_PAYLOAD_CONTRACT` for all 9 HunterFamily matrix names. Even if HTTP fields are smuggled in arguments, do not compile (that would invent a cell→payload mapping).
- `MutationVariantCompiler` — compiles MutationEngine-shaped args onto real `http.transaction` using `request.hypothesis_id` (not `variant_id`). This is the grounded MR-3 partial-PASS path.
- `src/research_os/application/hunt_validation.py` — persist `cells` / `steps` (stop discarding), plus `_node_compile_context()` copying origin/path/method/resource_id/actor/own_object/cross_object/mode/transition/area from node attributes; `authorized_origin` copied from `origin` if missing. Existing keys (`cell_count`, `worker_dispatch`, `protocol_plan_hash`, `approval_required`) preserved. Payloads/bodies are **not** invented or persisted.

Per-family mutation matrix (all `EXECUTION_UNSUPPORTED` except MutationEngine variants, which are not HunterFamily-keyed):

| HunterFamily | Compiler outcome | Counted as MR-3 PASS? |
|---|---|---|
| SQL_INJECTION | `BLOCKED_MISSING_SEMANTICS` | No |
| SERVER_SIDE_TEMPLATE_INJECTION | `BLOCKED_MISSING_SEMANTICS` | No |
| FILE_INCLUDE_AND_PATH_TRAVERSAL | `BLOCKED_MISSING_SEMANTICS` | No |
| MASS_ASSIGNMENT | `BLOCKED_MISSING_SEMANTICS` | No |
| JWT_CRYPTO_AND_CLAIM_CONFUSION | `BLOCKED_MISSING_SEMANTICS` | No |
| CORS_CREDENTIAL_EXFILTRATION_CHAIN | `BLOCKED_MISSING_SEMANTICS` | No |
| GRAPHQL_AUTHORIZATION_AND_INJECTION | `BLOCKED_MISSING_SEMANTICS` | No |
| DOM_TAINT_AND_CLIENT_SIDE_EXECUTION | `BLOCKED_MISSING_SEMANTICS` | No |
| AI_LLM_PROMPT_INJECTION_AND_TOOL_ABUSE | `BLOCKED_MISSING_SEMANTICS` | No |
| MutationEngine `MutationVariant` (not a HunterFamily) | `COMPILED` → `http.transaction` | Yes (partial path) |

### 4C / operator MR-4 — V3 consumer + protocol fail-closed

New `src/research_os/application/dispatch_approved_v3_queue.py` — `DispatchApprovedV3Queue`.

- Load item; `RUN` → `ALREADY_DISPATCHED` (no second attempt).
- Non-APPROVED/RUN → `HuntV3DispatchError`.
- Merge `item.arguments` + `command.compile_arguments`; overlay `selected_cell_id` / `selected_step_id` from persisted `cells`/`steps`.
- Compile via registry. If not COMPILED → `set_state(BLOCKED, from_state=APPROVED)`, audit `HUNT_V3_QUEUE_DISPATCH_BLOCKED`, `not_coverage=True`.
- If COMPILED: `PreparePlannedExperiment` then `ExecutePlannedExperiment` (fresh Core). Core DENY / HUMAN_REVIEW → BLOCKED, not RUN. Success / unknown-after-dispatch → `set_state(RUN, from_state=APPROVED)`, audit `HUNT_V3_QUEUE_DISPATCHED`.
- Does **not** pass the V3 queue `ApprovalView` in as execution authorization. `compiled_scope` is a separate Core input; a historical APPROVE plus `ScopeEvaluationInput(ALLOW)` without `CompiledScope` still DENY for HTTP-scope capabilities.
- Does **not** write `research_orchestration`. This is not a second next-action owner and not a second ARC. ARC remains the sole orchestration-progression owner (Slice 3 / MR-1). This use case consumes one already-APPROVED queue row through existing prepare/execute primitives.

CAS on `HuntV3QueueRepository.set_state(..., *, from_state=None)`: mismatch → `PersistenceConflictError`. Existing `ApproveHuntV3Queue` callers still use the two-arg form.

`ProtocolStepCompiler` — **always** `BLOCKED_UNSUPPORTED_CAPABILITY` / `PROTOCOL_WIRE_SEMANTICS_NOT_REPRESENTABLE_BY_HTTP_TRANSACTION`. Design: `docs/plans/audit/PROTOCOL_EXECUTION_CAPABILITY_DESIGN.md`. No `http.raw_exchange` capability is added.

## Files changed

Production:

- `src/research_os/research/compiler_registry.py` (new)
- `src/research_os/application/dispatch_approved_v3_queue.py` (new)
- `src/research_os/application/hunt_validation.py` — persist cells/steps + node compile context
- `src/research_os/data/ports.py` — `HuntV3QueueRepository.set_state(..., *, from_state=None)`
- `src/research_os/data/postgres/repositories.py` — CAS `UPDATE ... WHERE state = from_state`
- `tests/support/fake_unit_of_work.py` — matching CAS

Tests:

- `tests/unit/research/test_compiler_registry.py` (new, 12)
- `tests/unit/application/test_dispatch_approved_v3_queue.py` (new, 7)
- `tests/unit/application/test_hunt_cycle.py` — node compile context + persisted protocol `steps`
- `tests/integration/test_sd_g5_hunt_cycle.py` — `len(cells) == cell_count`

Docs:

- this record
- `docs/plans/audit/PROTOCOL_EXECUTION_CAPABILITY_DESIGN.md`
- `docs/plans/audit/CAMPAIGN_BASELINE.md` campaign-order row for Slice 4

Migration: none. `RUN` / `BLOCKED` already existed. Additive arguments JSON only.

## Qualification

| Gate | Status | Why |
|---|---|---|
| MR-2 (lock) / 4A — compiler registry | **PASS** | OBJECT_AUTHORIZATION and WORKFLOW_STATE_TRANSITION bypass the generic planner; schema/fingerprint/side-effect bound; unknown family falls back to generic without understating; planning aliases rejected as non-capabilities |
| MR-3 (lock) / 4B — mutation execution | **PARTIAL** | MutationEngine variant → `http.transaction` compiles. All 9 HunterFamily `MutationMatrixCell` families `BLOCKED_MISSING_SEMANTICS` (no payload catalog). Not counted as PASS |
| Operator 4C / V3 consumer | **PASS** | APPROVED compiles or blocks; Core re-check; exactly one attempt; CAS RUN; historical approval is not an execution token |
| Operator 4C / protocol execution | **FAIL / deferred** | Fail-closed by design; design doc exists; not an executor. Not counted as PASS |
| Lock Slice 4 PASS criterion ("APPROVED V3 item reaches a real ExecutionAttemptRecord exactly once, authorized fresh by Core") | **PASS** for grounded families (OBJECT_AUTHORIZATION proven). Unsupported families reach BLOCKED with zero attempts, which is the required fail-closed behavior, not a silent skip of the criterion |
| Lock hard-fail ("V3 Approval becomes execution authorization") | **not triggered** | proven by `test_stale_approval_does_not_bypass_fresh_core_deny` |

## Invariants proven

- Known HunterFamily names never reach `GenericPlannerCompiler`.
- Planning aliases are not Worker capabilities and cannot be compiled.
- Compiled side-effect is the capability-registry minimum, re-checked by `assert_plan_not_understated`.
- `ApproveHuntV3Queue` still only sets `APPROVED` and does not dispatch.
- PENDING items are rejected, not compiled.
- Historical V3 `ApprovalRecord` + naive allow-match, without `CompiledScope`, is `CORE_DENIED` / `BLOCKED` / zero Worker calls. The approval row remains APPROVE.
- A compiled-scope ALLOW for OBJECT_AUTHORIZATION produces exactly one `ExecutionAttempt` and one Worker call; a second dispatch is `ALREADY_DISPATCHED` with the same attempt count.
- Protocol and mutation-matrix APPROVED items go to `BLOCKED`, not `RUN`, with zero Worker calls and `not_coverage=True`.
- `DispatchApprovedV3Queue` does not write `research_orchestration`.

## Test evidence

- Slice 4 focused unit: `tests/unit/research/test_compiler_registry.py` 12/12; `tests/unit/application/test_dispatch_approved_v3_queue.py` 7/7; hunt-cycle unit still green.
- Architecture boundaries: `tests/unit/test_architecture_boundaries.py` included in the unit suite (research must not import application/data; compiler registry is clean). Combined architecture + Slice 4 new tests: 45 passed.
- Full unit suite: **1314 passed**, 4 skipped, 44 subtests passed, 0 failed.
- Full integration suite (real PostgreSQL, `RESEARCH_OS_TEST_DATABASE_URL=postgresql+psycopg://research_os_test@127.0.0.1:55432/research_os_test`): **186 passed**, 18 subtests passed, **1 failed** — the same pre-existing `tests/integration/test_sd_g4_token_economy.py::SDG4TokenEconomyIntegrationTests::test_cheap_call_records_tokens_and_deny_when_limit_reached` (`budget_consumption` CHECK-constraint `ck_budget_consumption_resource_type` / `MODEL_TOKENS_IN`). Unrelated to compilers or V3 dispatch. No new failures.
- Full e2e suite: **152 passed**, 5 skipped, **4 failed** — the same pre-existing `cli_session` module-isolation failures recorded at Slice 3 (`test_gate14…test_20_no_codex_or_model_runtime_and_maturity_unchanged`, `test_gate15…test_18_no_codex_model_or_strix_invoked`, `test_gate16…test_30_no_model_or_codex_invocation`, `test_gate17…test_48_no_model_runtime`). No new e2e failures.

## Unresolved / explicitly out of scope

- `DispatchApprovedV3Queue` is not wired into a dashboard button, ARC cycle, or daemon poller. Wiring a silent poller that progressed orchestration would re-open the second-scheduler problem Slice 3 just closed. A future operator/CLI trigger that calls this use case per queue id is the intended next hop, not an autonomous second brain.
- `RunResearchSelection`'s deterministic HTTP probing policy is still not reachable from model-driven `ARC.step()`. The compilers now exist; teaching the model-driven proposal path to emit `CompilerRequest`s for those families is not this slice.
- No `mutation.matrix` or `protocol.parser` Worker capability was added (would be vendor lock-in to a fake primitive).
- No SQLi/SSTI/smuggling payloads were invented.
- Protocol `http.raw_exchange` is design-only (`PROTOCOL_EXECUTION_CAPABILITY_DESIGN.md`).
- Slice 5 (lock MR-4, promotion trigger after SUPPORTED assessment) is next, not this record.

## Next

Slice 5 — promotion trigger (`IMPLEMENTATION_SEQUENCE_LOCK.md` §5 / campaign Phase H / lock MR-4).
