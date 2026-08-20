# Research OS Operations Notes

## SD-G8 — Coverage Debt

### Scope

SD-G8 builds a deterministic, LLM-free coverage-debt matrix that tells the
operator where the hunt is incomplete:

- **Coverage Debt Core** (`research_os.research.coverage`): `CoverageCell`,
  `CoverageMatrix`, and `compute_coverage_debt(graph, registry, hypotheses_view)`.
  The matrix is indexed by `(node_canonical_key, identity_id, family_id)`.
- **Identity-agnostic boundary**: `HypothesisRecord` does not carry identity, so
  SD-G8 treats a hypothesis as covering all identity cells of its
  `(node, family)` pair. Per-identity binding is scheduled for SD-G9.
- **Scope partition**: only `IN_SCOPE` nodes produce debt cells.
  `UNKNOWN`/`OUT_OF_SCOPE` nodes are emitted as `NOT_APPLICABLE` and do not
  contribute to `total_debt`.
- **Determinism**: the matrix hash is computed from a canonical, sorted JSON
  serialization of all cells; permutations of the input produce the same hash.
- **Persistence**: `coverage_debt_snapshot` stores only
  `matrix_hash + cell_counts + total_debt`; the full matrix remains rebuildable
  from the ledger.

### Coverage States

| State | Meaning |
|-------|---------|
| `NOT_APPLICABLE` | Node is not an active hunt target (`UNKNOWN`/`OUT_OF_SCOPE`). |
| `UNTESTED` | No hypothesis exists for the cell. |
| `HYPOTHESIZED` | Hypothesis exists but has not passed V1. |
| `V1_PASSED` | Static scope/precondition/budget checks passed. |
| `V2_PASSED` | Passive/yielded evidence confirmed the hypothesis. |
| `V3_QUEUED` | Approved for active experiment (still pending execution). |
| `COVERED` | Hypothesis fully validated; no debt for this cell. |

### Registry Integration

- `CoverageDebtView` loads the latest enabled version of each `hunter_family`
  row (append-only versioning: higher `version` wins).
- `families_for_node` evaluates node kind + edge preconditions against the
  graph; only applicable families open cells.
- Hypothesis progress is read from `hypothesis` + `audit_event` tier events
  (`HYPOTHESIS_TIER_V1_PASSED`, `HYPOTHESIS_TIER_V2_PASSED`,
  `HYPOTHESIS_TIER_V3_QUEUED`, and rejection events).

### Operator Visibility

- CLI: `research-os coverage --research-run-id <id>` prints total debt,
  per-family debt, per-state counts, top-10 nodes, and the matrix hash.
- Optional persistence: `CoverageDebtView.execute(..., persist=True)` writes a
  `coverage_debt_snapshot` record and returns the generated `snapshot_id`.

### Runbook

- `GATE_08_STATUS` stays `PENDING` until the independent architect audit seals
  the gate.
- Full suite commands are the same as SD-G7.

## SD-G9 — HunterScore Scheduler + Identity Binding

### Scope

SD-G9 closes the SD-G8 identity-agnostic boundary and adds a deterministic
priority queue so the operator can see what the system would hunt next:

- **Identity binding**: `HypothesisRecord` and `HuntV3QueueRecord` now carry an
  `identity_id` column (nullable for legacy rows). `GenerateHuntHypotheses`
  produces one hypothesis per `(node, identity, family)` tuple. Nodes without
  explicit identities use `ANONYMOUS`.
- **Identity expansion cap**: per node, expansion is capped at
  `MAX_IDENTITIES_PER_NODE = 8` to prevent combinatorial noise. When the cap is
  hit, an `IDENTITY_EXPANSION_CAPPED` audit event is written and the remaining
  identities stay `UNTESTED` for future cycles.
- **HunterScore core** (`research_os.research.scheduler`): deterministic score
  for every debt cell. Score components:
  - `state_weight`: `UNTESTED > HYPOTHESIZED > V1_PASSED > V2_PASSED > V3_QUEUED > COVERED`.
  - `family_success_bonus`: a bounded historical prior from supported/falsified
    hypothesis assessments. The prior is capped so one historically successful
    family cannot dominate the whole coverage matrix.
  - `family_exploration_bonus`: low-history or missing-history families receive
    a small deterministic exploration bump so novel families are not starved.
  - `freshness_bonus`: latest node activity, not first-seen age, drives hunt
    freshness. `first_seen_at` remains audit context; `latest_activity_at`
    handles old assets that changed recently.
  - `budget_suitability_bonus`: when the daily LLM budget is exhausted,
    V3-bound cells (`V2_PASSED`, `V3_QUEUED`) are penalized and cheap-path cells
    receive a small bonus.
- **Explainability**: every `HunterScore` carries a component breakdown
  (`explanation` tuple) so the ranking is never a black box.
- **Scheduler use case**: `RunHuntScheduler` rebuilds the coverage-debt matrix,
  scores all debt cells, selects the top N, and writes a
  `HUNT_SCHEDULE_RECOMMENDED` audit event. It does not write to the V3 queue.
- **Cycle intake**: `RunHuntCycle` can optionally consume a schedule; the V1/V2/V3
  tier gates and the `IN_SCOPE` V3 enqueue lock remain unchanged.

### Determinism Guarantees

- Same graph + registry + ledger + budget view + reference time always yields the
  same ranked list.
- Tie-break is deterministic: descending score, then ascending
  `(node_canonical_key, identity_id, family_id)`.

### Operator Visibility

- `RunHuntScheduler` writes `HUNT_SCHEDULE_RECOMMENDED` events with
  `matrix_hash`, `recommended_count`, and the top cells with their scores and
  state.
- The schedule can be consumed by `RunHuntCycle` for automated execution or kept
  as a recommendation only.
- SD-G9 seal includes starvation/lock-in regression tests proving bounded family
  prior, low-history exploration, and latest-activity freshness.

### Runbook

- `GATE_09_STATUS = "PASS"`.
- Seal evidence (2026-08-20): `1450 passed, 9 skipped, 44 warnings, 53 subtests
  passed` via full `pytest` against the local PostgreSQL integration database.
- Required commands:
  ```bash
  source .venv/bin/activate
  bash scripts/start_wsl_test_postgres.sh
  python -m pytest tests/integration/test_sd_g9_hunterscore_scheduler.py -q
  python -m pytest tests/unit tests/contract -q
  python -m pytest tests/integration -q
  python -m pytest tests/e2e -q
  python -m pytest -q
  ```

## SD-G10 — Independent Validator + Severity Engine + Circuit Breaker

### Scope

SD-G10 starts the attack-period validation/economy layer after HunterScore:

- **Independent validator**: required V1/V2/V3 tiers must pass before downstream
  admission. Missing tiers fail closed. `V3_QUEUED` is not a validator PASS.
- **Severity engine**: severity is downstream of validator PASS and IN_SCOPE
  status. It maps internal `P0`-`P3` to platform-style Bugcrowd/HackerOne
  labels, but does not write severity into Hypothesis, Observation, Evidence,
  Candidate, or early FindingProposal rationale.
- **Family circuit breaker**: rejected/inconclusive telemetry can throttle a
  family, but the breaker must never disable or delete a family.

### Runbook

- `GATE_10_STATUS = "PASS"`.
- SD-G10 is not old infrastructure `GATE 10 — Runtime / Strix Boundary
  Integrity`.
- Current P1 domain tests:
  ```bash
  python -m pytest tests/unit/research/validation tests/unit/test_maturity.py -q
  ```
- P1 evidence (2026-08-20): `1461 passed, 9 skipped, 53 subtests passed` via
  full `pytest`; Alembic deprecation warnings removed with `path_separator = os`.
- P2 application integration evidence (2026-08-20):
  - `SubmitFindingProposal` rejects security candidates without append-only
    validator tier PASS evidence through V3.
  - Diagnostic-only proposals stay exempt from the security validator gate.
  - Rejections write `FINDING_PROPOSAL_VALIDATION_REJECTED` audit events and
    return `REJECTED_VALIDATION_NOT_PASSED`.
  - Focused checks: `131 passed` for Gate14-Gate17 e2e, `31 passed` for
    SD-G10 finding-admission unit/integration coverage.
  - Full suite: `1465 passed, 9 skipped, 53 subtests passed`.
- P3/P4/P5 seal evidence (2026-08-20):
  - `ScoreFindingSeverity` writes severity decisions only to append-only audit
    events, never into Hypothesis, Observation, Evidence, Candidate, or early
    FindingProposal records.
  - `EvaluateFamilyCircuitBreaker` reads family telemetry from the append-only
    ledger and can only `ALLOW` or `THROTTLE`; it never disables/deletes a
    family.
  - PostgreSQL SD-G10 integration covers V1/V2 missing, V3 queued, deterministic
    severity scoring, out-of-scope/validation-missing non-scoring, and
    throttle-without-disable telemetry.
  - Focused SD-G10 checks: `29 passed`.
  - Affected SD-G7/SD-G10/Gate14-Gate17 checks: `167 passed`.
  - Full suite: `1470 passed, 9 skipped, 53 subtests passed`.

## SD-G11 — Production Executor Fabric

### Scope

SD-G11 starts the Attack Muscle production executor fabric. This is **not** old
infrastructure `GATE 11 — Runtime Routing Integrity`, and it is **not** G21
browser/application-state maturity.

Current P1 slice:

- `BuildExecutorReplayManifest` reads persisted Experiment, ExecutionAttempt,
  WorkerResult, and Observation rows without redispatching a Worker.
- It produces a canonical replay manifest plus SHA-256 hash.
- Raw result, diagnostics, artifact descriptors, and observation payloads are
  represented by redacted digests only.
- Replay class is explicit: `DETERMINISTIC_REPLAY`,
  `ENVIRONMENT_SENSITIVE`, `HUMAN_REVIEW_REQUIRED`, or `NOT_REPLAYABLE`.
- Browser and stateful side-effect outputs are not treated as deterministic
  replay.

Current P2 slice:

- `BuildExecutorReplayBundle` wraps the replay manifest with a deterministic
  bundle hash.
- Durable ExperimentPlan rows are represented as request-template fingerprints;
  raw arguments are not copied into the bundle.
- WorkerResult response bodies, diagnostics, control signals, and artifact
  descriptors are represented by digests only.
- Screenshot/trace/response artifact presence is retained through descriptor
  kind + digest metadata.
- Replay controls fail closed: no automatic redispatch, Core authorization
  required, redirect reauthorization required, and human review required for
  high side-effect replay classes.

### Runbook

- SD-G11 status remains `PENDING`.
- G21 remains `PENDING`; local Chromium browser checks passed, but cgroup
  containment skipped without delegation and required mode fails closed.
- P1 evidence (2026-08-20): `6 passed` for replay manifest unit coverage plus
  PostgreSQL G19 ledger integration.
- P2 evidence (2026-08-20): `9 passed` for replay manifest, replay bundle, and
  PostgreSQL G19 ledger integration.
- Affected checks (2026-08-20): `35 passed, 5 skipped`.
- Full suite (2026-08-20): `1474 passed, 9 skipped, 53 subtests passed`.

## SD-G7 — ImpactGraph

### Scope

SD-G7 makes every impact claim in a FindingProposal traceable to a chain of
proof artifacts from the ledger. A chain without proofs cannot be admitted.

- **ImpactChain core** (`research_os.research.impact`): `ImpactNode`,
  `ImpactEdge`, and `ImpactChain` with structural validation and a
  demonstrated-capability scope rule.
- **Admission integration**: `SubmitFindingProposal` rejects proposals whose
  `impact_claims` reference a missing chain, an invalid chain, or a chain whose
  claimed impact kinds exceed what the referenced proofs actually demonstrate.
- **Persistence**: `impact_chain`, `impact_chain_node`, and `impact_chain_edge`
  tables store chains append-only; `finding_proposal.impact_chain_ids` links
  proposals to their chains.

### Impact Kinds and Demonstrated Capabilities

Simple (union) mapping:

| Demonstrated capability | Allowed impact kinds |
|-------------------------|----------------------|
| `READ_OTHER_OBJECT` | `DATA_READ`, `AUTH_BYPASS` |
| `WRITE_OTHER_OBJECT` | `DATA_WRITE`, `STATE_CORRUPTION` |
| `WORKFLOW_TRANSITION_WITHOUT_AUTH` | `STATE_CORRUPTION`, `AUTH_BYPASS` |
| `AUTHENTICATED_AS_USER` | `AUTH_BYPASS` |
| `PRIVILEGE_ESCALATION_EVIDENCE` | `AUTH_BYPASS` |
| `OAST_CALLBACK_RECEIVED` | `EXTERNAL_CALLBACK` |

Composite (AND) requirements:

| Impact kind | Required capability sets |
|-------------|--------------------------|
| `ACCOUNT_TAKEOVER_PATH` | `{AUTHENTICATED_AS_USER, PRIVILEGE_ESCALATION_EVIDENCE}` OR `{AUTHENTICATED_AS_USER, CROSS_ACCOUNT_SESSION_ASSUMPTION}` |

Unknown capabilities contribute nothing (fail-closed empty set).

### Validation Rules

1. Every `ImpactNode` must reference at least one resolvable `proof_id`.
2. Every `proof_id` must exist in the ledger (`evidence`, `observation`, or
   `experiment`) and belong to the same `research_run_id` as the chain.
3. The chain must be acyclic and every edge must connect nodes inside the chain.
4. The node's `impact_kind` must be in the allowed set derived from its proofs'
   demonstrated capabilities (simple union + composite AND rules).
5. All node `scope_ref`s must stay within the same program/run boundary.
6. `SubmitFindingProposal` rejects any `impact_claims` whose registered chain
   belongs to a different research run than the proposal (cross-run provenance
   is not allowed).

### Use Cases

- `RegisterImpactChain`: persists a validated chain; performs structural
  validation + run-binding check (proofs must resolve within the chain's run).
- `SubmitFindingProposal`: rejects chains registered under a different run,
  re-validates the chain structurally and against demonstrated capabilities,
  then persists the proposal with `impact_chain_ids`.

### Runbook

- `GATE_07_STATUS` stays `PENDING` until the independent architect audit seals
  the gate.
- Full suite commands are the same as SD-G6.

## SD-G6 — Mutation Engine + OAST Core

### Scope

SD-G6 adds the attacker's planning teeth while keeping every tooth inside the
scope muzzle:

- **Mutation Engine** (`research_os.research.mutation`): deterministic
  variation generation from observed `HTTP_OPERATION` / `EXACT_PATH` nodes.
- **OAST Core** (`research_os.research.oast`): out-of-band callback token
  lifecycle for blind-vulnerability proof-of-concepts.
- **Rate-limit enforcement**: `program_policy.rate_limit_profile` is enforced by
  `ExecutePlannedExperiment` before any Core execution decision.

### Mutation Families

| Family | Rule | Description |
|--------|------|-------------|
| `param_pollution` | duplicate_param / array_param | Duplicate or array-style query parameters. |
| `type_juggling` | type_juggling | Numeric/boolean/float-like string values. |
| `boundary_value` | boundary | Boundary values for numeric/identifier parameters. |
| `auth_header_variation` | auth_header | Authorization and forwarding header variants. |
| `method_override` | override | Method override via header or query parameter. |
| `content_type_confusion` | content_type | Content-Type confusion for mutating requests. |
| `id_or_traversal` | traversal | Path traversal / identifier manipulation candidates. |

All variants are plans only; execution still flows through the existing
`capability → envelope → approval` gate. Variants are confined to
`IN_SCOPE` nodes; `UNKNOWN` and `OUT_OF_SCOPE` nodes produce no variants.

### Audit Payload Rules

- Each variant's `to_public_summary()` produces a size-bounded payload
  (≤ 2 KB total) with no secrets, no full response bodies, and no raw token
  values.
- Forbidden argument keys: `token`, `secret`, `password`, `api_key`,
  `private_key`, `session`, `cookie`.

### OAST Token Lifecycle

1. `AdmitOastCallback` expects the token to exist in `oast_token` table.
2. The callback timestamp is checked against `expires_at`.
3. Expired callbacks are rejected (`OAST_TOKEN_EXPIRED`) but still audited.
4. Valid callbacks are persisted as `sensor_observation` records with
   `sensor_id = "oast.loopback"` and `epistemic_status = UNTRUSTED_EXTERNAL`.
5. `AdmitSensorObservations` then admits the observation as a `DiscoveryFact`
   with `source_status = UNTRUSTED_EXTERNAL`, preserving the epistemic boundary.

### Rate-limit Enforcement

- `RateLimitProfile` is stored in `rate_limit_profile` table.
- `ProgramResearchContext.policy.rate_limit_profile` exposes it to dispatch.
- `ExecutePlannedExperiment._check_rate_limit` counts authorized attempts in the
  rolling window and returns `RATE_LIMIT_DENIED` before Core execution.
- Clock is injected; production code never calls `datetime.now()` directly.

### Live Infrastructure Boundary

- All OAST tests use the `LoopbackOastPort` fixture; live internet callbacks are
  forbidden in tests.
- Real OAST callback infrastructure (HTTP ingress, token DNS, etc.) is a
  separate operational track and is not opened by this gate.

### Runbook

- To run the full SD-G6 test suite on Kali with real PostgreSQL:
  ```bash
  source .venv/bin/activate
  python -m pytest tests/unit tests/contract -q
  python -m pytest tests/integration -q
  python -m pytest tests/e2e -q
  ```
- `GATE_06_STATUS` stays `PENDING` until the independent architect audit seals
  the gate.
