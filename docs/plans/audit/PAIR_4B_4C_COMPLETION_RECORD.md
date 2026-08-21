# Pair 4B + 4C Completion Record — Mutation execution semantics + protocol execution bridge

Status: IMPLEMENTATION_COMPLETE. PAIR_4B_4C_QUALIFIED = YES.

Sealed as checkpoint 9 on `campaign/majority-implementation` (this pair's
code + this record). Targeted counts below are the qualification evidence
at seal time; they are not a later full-campaign QA.

Baseline this pair started from: `d4b75fca11053376aea2380e70b390200c29a917`
(`campaign/majority-implementation`, Slice 3–7 sealed).

This pair does **not** change global maturity flags, does not close canonical
PromotionPipeline, and does not add exploratory attack capability.

## What closed

### 4B — Mutation execution semantics

The 9 HunterFamily `MutationMatrixCell` families no longer fail closed with
`MUTATION_MATRIX_CELL_HAS_NO_PAYLOAD_CONTRACT`.

Path for a selected cell:

`MatrixCell → MutationMatrixCellCompiler → typed ExperimentPlan (http.transaction)
→ fresh Core authorization → WorkerPort → WorkerResult → Observation →
MutationMatrixEvaluator`

AI may select `cell_id`. Incoming query/body/headers are ignored. The compiler
owns the catalog (`research/mutation/cell_contract.py`). Each actual variant is
one bounded experiment with its own attempt/request id and budget/rate-limit
consumption. `planned` / `compiled` is not coverage. `coverage_recorded` is true
only after `OBSERVATION_PRODUCED`. Control is the cell's own `control` field
(secure/deceptive/read-back cycling already in the matrix). Disconfirming
observation is required on every compiled plan.

Cells were not deleted. Scope was not shrunk. Families were not relabeled
unsupported to mint PASS.

### 4C — Protocol execution bridge

Specialist `ProtocolParserPlan` builders are unchanged. Missing execution
bridge only:

`ProtocolPlan step → ProtocolStepCompiler → typed ExperimentPlan (http.raw_exchange)
→ fresh Core authorization → WorkerPort → WorkerResult → Observation →
ProtocolStepEvaluator`

Approved ProtocolPlan is not an execution token. One step does not authorize
the next. Queue item stays `APPROVED` so later steps can be re-authorized.
Redirect → Worker `REAUTHORIZATION_REQUIRED` / STOP / no follow.
Same `step_id` cannot be blindly retried (`HUNT_V3_UNIT_INTENT`).
`UNKNOWN_OUTCOME` is not a hypothesis falsification and is not retried.
No second dispatcher / second research brain: still `DispatchApprovedV3Queue`
inside Application, ARC remains the sole lifecycle owner.

`http.transaction` is still not used to fake CL.TE / raw framing.

## 9 matrix cells BEFORE → AFTER

| HunterFamily | BEFORE | AFTER |
|---|---|---|
| SQL_INJECTION | `BLOCKED_MISSING_SEMANTICS` / `MUTATION_MATRIX_CELL_HAS_NO_PAYLOAD_CONTRACT` | `COMPILED` → `http.transaction` + evaluator `mutation.matrix.v1` |
| SERVER_SIDE_TEMPLATE_INJECTION | same BLOCKED | same COMPILED path |
| FILE_INCLUDE_AND_PATH_TRAVERSAL | same BLOCKED | same COMPILED path |
| MASS_ASSIGNMENT | same BLOCKED | same COMPILED path (`mutate` when `write_attempt`) |
| JWT_CRYPTO_AND_CLAIM_CONFUSION | same BLOCKED | same COMPILED path (catalog sentinels; no Authorization-header capability weakening) |
| CORS_CREDENTIAL_EXFILTRATION_CHAIN | same BLOCKED | same COMPILED path |
| GRAPHQL_AUTHORIZATION_AND_INJECTION | same BLOCKED | same COMPILED path |
| DOM_TAINT_AND_CLIENT_SIDE_EXECUTION | same BLOCKED | same COMPILED path |
| AI_LLM_PROMPT_INJECTION_AND_TOOL_ABUSE | same BLOCKED | same COMPILED path |

Incomplete cells (missing dimensions/origin/control) still
`BLOCKED_MISSING_SEMANTICS`. That is fail-closed, not PASS-by-deletion.

## Protocol plans BEFORE → AFTER

| Plan | BEFORE | AFTER |
|---|---|---|
| HTTP_REQUEST_SMUGGLING_DESYNC `ProtocolParserPlan` | plan persisted; every step `BLOCKED_UNSUPPORTED_CAPABILITY` / `PROTOCOL_WIRE_SEMANTICS_NOT_REPRESENTABLE_BY_HTTP_TRANSACTION` | plan **unchanged**; selected step compiles to `http.raw_exchange` / `probe` |
| HTTP_CACHE_POISONING_DECEPTION `ProtocolParserPlan` | same BLOCKED | plan **unchanged**; selected step compiles to `http.raw_exchange` / `probe` |

## Reused architecture

- Core `evaluate_execution` + compiled scope (sole auth/scope/budget/side-effect authority)
- ARC lifecycle unchanged; `DispatchApprovedV3Queue` is not a second next-action owner
- `compile_experiment_intent` schema/fingerprint/side-effect bind
- `PreparePlannedExperiment` / `ExecutePlannedExperiment` / Transition A ingest
- `http.transaction` for mutation cells (existing primitive)
- Hunt V3 queue CAS / APPROVED admission (approval ≠ authorization)

## Schema / migration

None. Additive capability JSON `http.raw_exchange` and audit events
`HUNT_V3_UNIT_INTENT` / `HUNT_V3_UNIT_OUTCOME`. No Alembic revision.

New Worker capability was mandatory: the existing design record proved
`http.transaction` cannot preserve wire semantics. Adding the capability is
the execution bridge; impersonating smuggling through `http.transaction` was
forbidden.

## Invariants preserved

- Core = sole scope/auth/budget/side-effect authority
- ARC = sole research lifecycle owner
- Worker = authorized bounded execution only
- Model is not Worker payload authority
- WorkerResult ≠ Observation ≠ Evidence
- Operational failure / `UNKNOWN_OUTCOME` ≠ falsified hypothesis
- Approval ≠ authorization
- Capability schema `additionalProperties: false`; fingerprint and SE minima not lowered
- `http.transaction` header/path risk ceilings were not relaxed for JWT/CORS/LFI encodings

## Test evidence

Targeted:

- `tests/unit/research/test_compiler_registry.py` (9-family compile + protocol compile)
- `tests/unit/research/test_mutation_cell_contract.py`
- `tests/unit/application/test_dispatch_approved_v3_queue.py` (cell/step execution, Core DENY = 0 Worker, crash-after no retry)
- `tests/unit/worker_runtime/test_http_raw_exchange.py`
- `tests/integration/test_slice4b_4c_execution.py` (real PostgreSQL + loopback lab)
- architecture boundary copies for `http.raw_exchange`
- G14–G17 isolated e2e: **131 passed**
- SD-G6 / SD-G12 / SD-G13 unit + relevant integration: passed with the suites below

Exact counts this pair:

| Suite | PASS | FAIL | SKIP |
|---|---|---|---|
| unit (`tests/unit`) | **1354** | 0 | **4** |
| integration (`tests/integration`) | **191** | **1** | 0 |
| e2e G14–G17 isolated | **131** | 0 | 0 |

The integration failure is the **pre-existing**
`tests/integration/test_sd_g4_token_economy.py::test_cheap_call_records_tokens_and_deny_when_limit_reached`
(`ck_budget_consumption_resource_type` / `MODEL_TOKENS_IN`). Not caused by 4B/4C.

Previous Slice 7 unit baseline was 1344 passed / 4 skipped. This pair adds 10
unit tests net. Integration baseline was 189 passed + 1 pre-existing fail;
this pair adds 2 Postgres tests.

## Regressions

None introduced by this pair. Pre-existing only:

- SD-G4 token-economy CHECK constraint
- Full e2e suite `cli_session` module-isolation failures on G14–G17 `no_model`
  tests when the **entire** e2e package is collected together (isolated G14–G17
  still 131 passed)

## Unresolved / out of scope

- `DispatchApprovedV3Queue` is still not an ARC poller / second research brain
- Canonical PromotionPipeline (Assessment→Evidence→Candidate→Verification→FindingProposal) remains open
- Family-level coverage `COVERED` is not auto-emitted after one of N matrix cells (correct)
- Operator-owned vulnerable/secure/deceptive *lab fixtures* for parser deltas are not this pair
- Global maturity flags unchanged

PAIR_4B_4C_QUALIFIED = YES
