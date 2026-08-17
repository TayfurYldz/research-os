# Operations

Diagnostic operational helpers. This is not a DBA product and not a claim that Research OS is production-ready for autonomous security research.

## PostgreSQL

Application database (operator status HEALTHY comes from this URL only):

- `RESEARCH_OS_DATABASE_URL`

Isolated test database (reported separately as `TEST_POSTGRESQL`; never preferred over the application URL):

- `RESEARCH_OS_TEST_DATABASE_URL` (must contain `test`; SQLite is not a substitute)

Commands:

```
python scripts/research_os_db.py ping --test
python scripts/research_os_db.py version --test
python scripts/research_os_db.py migrate --test
```

Backup/restore remain operator procedures against PostgreSQL. Do not silently delete evidence-linked artifacts or SoR rows.

Connection health is `SELECT 1` only. Credentials and userinfo passwords are not logged or rendered.

## Operator status

```
python scripts/research_os_status.py status
```

or, after install, from any working directory:

```
research-os status
```

Output includes POSTGRESQL (application DB), TEST_POSTGRESQL (if configured), Worker, Model Runtimes, Strix, Auth, Orchestrator, Budget ledger, Reconciliation, Observability, GATE 04B, and maturity flags. It must not print secrets.

Worker HEALTHY requires a real diagnostic protocol probe (spawn → valid request → schema + correlation → clean exit). Codex `--version` is INSTALLED/VERSION_KNOWN only. `SUBSCRIPTION_OAUTH` is `NOT_IMPLEMENTED`. GATE 04B remains PENDING until ≥2 `BENCHMARK_COMPATIBLE` live ModelRuntime configurations actually execute a comparable run. Scripted baselines and Strix do not count.

## Codex readiness ladder

Documented CLI only. Tokens are not scraped. Codex is not auto-installed.

Multiple Codex CLI ModelRuntime configurations share one authenticated executable/session.
Models are operational configuration, not architecture.

```
RESEARCH_OS_CODEX_MODELS=codex-cli-terra=gpt-5.6-terra,codex-cli-gpt55=gpt-5.5
```

or a model list that derives stable IDs:

```
RESEARCH_OS_CODEX_MODELS=gpt-5.6-terra,gpt-5.5
```

Optional executable override: `RESEARCH_OS_CODEX_EXECUTABLE`. Duplicate or empty entries fail closed.

Current diagnostic defaults (overrideable): `codex-cli-terra` → `gpt-5.6-terra`, `codex-cli-gpt55` → `gpt-5.5`.

`research-os status` and ordinary `--discover` are **PASSIVE**. They may run `codex --version` and `codex login status` only. They must not run `codex exec` and must not consume model quota. Passive AUTH_READY is not `BENCHMARK_COMPATIBLE` and does not populate `available_model_configurations`.

Explicit live probe (consumes model quota; independent per configured model):

```
python scripts/run_research_benchmark.py --discover --live-probe
```

Each configuration is probed independently:

1. NOT_INSTALLED — executable missing
2. INSTALLED / VERSION_KNOWN — `codex --version` succeeded
3. AUTH_READY — `codex login status` exit 0
4. DIAGNOSTIC_READY / MODELPORT_COMPATIBLE — explicit LIVE `codex exec --ignore-user-config --ephemeral --sandbox read-only -m <model>`
5. BENCHMARK_COMPATIBLE — AUTH_READY and that model's request-consuming exec succeeded in this LIVE probe

Compatibility is not inferred across Codex configurations. Passive discovery and discovering two configs are not GATE 04B PASS. Usage-limit stderr maps to `RATE_LIMITED`, not a research-quality failure.

## Strix readiness

Executable/version is not HEALTHY. Sandbox/docker dependency must be ready. Harmless diagnostic ping only. No auto-install. Strix is not a Research OS ModelRuntime.

## Source export

```
python scripts/export_source.py --output dist/research-os-source.tar.gz
research-os export-source --output dist/research-os-source.tar.gz
```

Excludes `.git`, `.venv`, caches, coverage, runtime artifacts, and known credential/session files. Optional `--include-untracked-source` adds explicitly selected untracked source files only. Emits a SHA-256 manifest. Does not delete the developer's `.git` or `.venv`.

## Clean install

Mandatory for final GATE 13 PASS:

```
python scripts/clean_install_smoke.py
```

Builds a wheel (`python -m build` or `uv build`), installs it into an empty venv, changes CWD to an unrelated temp directory, then runs `research-os status`, `ContractValidator()`, local diagnostic Worker probe, development benchmark fixture load, and runtime discovery with no repository root on `sys.path`. If neither build backend is available, the script exits `VALIDATION_PENDING` (code 3) instead of fabricating PASS.

## Gate validation commands

```
python -m compileall src tests scripts
python -m unittest discover -s tests/unit -q
python -m unittest discover -s tests/contract -q
python -m unittest tests.unit.test_architecture_boundaries -q
python scripts/run_research_benchmark.py --baseline GOOD_BASELINE --single-run-legacy
python -m unittest discover -s tests/integration -q
python scripts/clean_install_smoke.py
```

GATE 12/13 are PASS only after those suites actually run with 0 required skips. Do not fabricate PASS.

## GATE 14 — local security-research E2E

**GATE 14 status: PASS** (2026-08-17).

Validation environment:

- Kali Linux
- real PostgreSQL
- dedicated `RESEARCH_OS_TEST_DATABASE_URL`
- Alembic head `a18_001_http_auth_class`
- `python -m unittest tests.e2e.test_gate14_security_lab`
- 19 E2E tests OK
- 0 skipped
- controlled localhost HTTP lab only
- no Codex / LLM / Strix

Proves: controlled authorized local security-research pipeline E2E for HTTP authorization differential / BOLA semantics.

Does **not** prove autonomous vulnerability discovery quality, real-world bug bounty performance, multi-model live validation, production readiness, or broad security-research validation. Do not set `SECURITY_RESEARCH_VALIDATED` or `PRODUCTION_READY`. GATE 04B remains PENDING.

```
python -m unittest tests.e2e.test_gate14_security_lab
```

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, the suite must SKIP, never fabricate PASS.

## GATE 15 — security ground-truth / false-positive benchmark

**GATE 15 status: PASS** (2026-08-17).

Authoritative environment:

- Kali Linux
- dedicated real PostgreSQL test database
- `RESEARCH_OS_TEST_DATABASE_URL`
- Alembic head `a18_001_http_auth_class`
- GATE 14 regression: 19 OK, 0 skipped
- GATE 15 ground-truth benchmark: 21 OK, 0 skipped
- localhost-only security ground-truth lab
- no Codex / LLM / Strix

GATE 14 is a single controlled security-semantics E2E. GATE 15 is a multi-scenario ground-truth / false-positive benchmark on the same `http.authorization.differential` pipeline. GATE 04B is live model comparison. These gates do not imply each other.

GATE 15 proves only: controlled multi-scenario ground-truth / false-positive security benchmark passed for HTTP authorization differential semantics.

Preserved benchmark guarantees:

- true BOLA validated
- independent verification required
- `false_finding = 0`
- secure / public / delegated / shared cases produced no Finding
- deceptive 200 / insufficient evidence produced no Finding
- contradictory verification did not VALIDATE
- timeout became INCONCLUSIVE
- redirect boundary was not crossed
- out-of-scope target did not reach Worker
- Human/Core approval remained mandatory
- no ground-truth leakage

Does **not** prove autonomous vulnerability discovery quality, real-world bug bounty performance, multi-model live validation, production readiness, or broad security-research validation. Do not set `SECURITY_RESEARCH_VALIDATED` or `PRODUCTION_READY`. GATE 04B remains PENDING.

```
python -m unittest tests.e2e.test_gate15_security_ground_truth
```

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, the suite must SKIP, never fabricate PASS.

## GATE 16 — workflow / state-transition authorization

**GATE 16 status: PASS** (2026-08-17).

Authoritative environment:

- Kali Linux
- dedicated real PostgreSQL test database
- `RESEARCH_OS_TEST_DATABASE_URL`
- Alembic head `a19_001_http_state_class`
- GATE 14 regression: 19 OK, 0 skipped
- GATE 15 regression: 21 OK, 0 skipped
- GATE 16 workflow/state-transition benchmark: 34 OK, 0 skipped
- localhost-only synthetic workflow lab
- no Codex / LLM / Strix
- no external network

GATE 14 = single BOLA E2E.
GATE 15 = BOLA false-positive ground truth.
GATE 16 = second vulnerability class: workflow/state-transition authorization + cross-class discrimination.

These gates do not imply live model validation or production readiness.

GATE 16 proves only: controlled workflow/state-transition authorization semantics plus cross-class discrimination against `HTTP_AUTHORIZATION_DIFFERENTIAL`.

Capability: `http.state_transition` (GET/POST, 127.0.0.1, exact origin, redirects disabled). Classification: `HTTP_STATE_TRANSITION_AUTHORIZATION`.

Does **not** prove autonomous vulnerability discovery quality, real-world bug bounty performance, multi-model live validation, production readiness, or broad security-research validation. Do not set `SECURITY_RESEARCH_VALIDATED` or `PRODUCTION_READY`. GATE 04B remains PENDING.

```
python -m unittest tests.e2e.test_gate16_state_transition_security
```

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, the suite must SKIP, never fabricate PASS.

## GATE 17 — autonomous multi-hypothesis research selection

**GATE 17 status: PASS** (2026-08-17).

Authoritative environment:

- Kali Linux
- dedicated real PostgreSQL test database
- `RESEARCH_OS_TEST_DATABASE_URL`
- authoritative tested commit `48d807d`
- GATE 14 regression: 19 OK, 0 skipped
- GATE 15 regression: 21 OK, 0 skipped
- GATE 16 regression: 34 OK, 0 skipped
- GATE 17 autonomous research-selection benchmark: 57 OK, 0 skipped
- repo-wide: unit 586 OK, contract 2 OK, architecture 15 OK, integration 112 OK
- no Codex / LLM / Strix
- no external network
- no migration
- 0 `psycopg.Connection` ResourceWarnings

GATE 14 = single controlled BOLA security E2E.
GATE 15 = BOLA ground-truth / false-positive benchmark.
GATE 16 = workflow/state-transition security semantics + cross-class discrimination.
GATE 17 = autonomous multi-hypothesis research selection + adaptive closed-loop experiment choice.
GATE 04B = live model comparison.

These gates do not imply one another.

GATE 17 proves only: Controlled local multi-hypothesis closed-loop research selection and adaptive experiment choice were validated against the dedicated real PostgreSQL test database with truth-blind benchmark execution.

Hidden ground truth may grade results; it must not steer execution or promotion.

It does **not** prove general autonomous vulnerability discovery, real-world bug bounty performance, live model quality, broad security-research validation, or production readiness. Do not set `LIVE_MODEL_VALIDATED`, `SECURITY_RESEARCH_VALIDATED`, or `PRODUCTION_READY`. GATE 04B remains PENDING.

```
python -m unittest tests.e2e.test_gate17_autonomous_research_selection
```

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, the suite must SKIP, never fabricate PASS.

## GATE 18 — offensive substrate foundation

**GATE 18 status: PASS** (2026-08-17).

Authoritative environment:

- Kali Linux
- dedicated real PostgreSQL test database
- `RESEARCH_OS_TEST_DATABASE_URL`
- authoritative tested commit `241e901fb2c6730ee293cca71942de45d3796282`
- Alembic head `a20_001_capability_plan_binding`
- migration round-trip: a19 → a20, a20 → a19, a19 → a20
- GATE 14 regression: 19 OK, 0 skipped
- GATE 15 regression: 21 OK, 0 skipped
- GATE 16 regression: 34 OK, 0 skipped
- GATE 17 regression: 57 OK, 0 skipped
- repo-wide: unit 627 OK, contract 2 OK, architecture 20 OK, integration 117 OK
- no Codex / LLM execution
- no external-network research
- no `psycopg` ResourceWarning observed

Canonical Worker capability registry contains only `diagnostic.echo`, `http.authorization.differential`, and `http.state_transition`. Codex remains ModelPort. Strix remains Integration. Neither compiles into a Worker ExperimentPlan. Core independently checks capability/action/version/fingerprint/risk. The Worker independently rejects mismatched definitions. Legacy NULL plans are never silently fingerprint-backfilled. Scope remains exact-host / default-deny / fail-closed for ambiguity. Redirects require reauthorization.

GATE 14 = single controlled BOLA security E2E.
GATE 15 = BOLA ground-truth / false-positive benchmark.
GATE 16 = workflow/state-transition security semantics + cross-class discrimination.
GATE 17 = autonomous multi-hypothesis research selection + adaptive closed-loop experiment choice.
GATE 18 = typed per-action capability/risk/scope/execution binding that is Core-verified, durable across restart, and Worker-rejected on definition mismatch.
GATE 04B = live model comparison.

These gates do not imply one another.

GATE 18 PASS means Research OS can transform an admitted research intent into a typed, per-action capability-bound and scope-evaluated experiment whose risk level and capability definition are independently verified by Core, durably bound across restart, and independently rejected by the Worker if its executable definition does not match.

It does **not** prove autonomous vulnerability discovery, broad security-research capability, real-world bug bounty performance, live model quality, production readiness, crawler/browser/recon capability, or XBOW/Edra parity. Do not set `LIVE_MODEL_VALIDATED`, `SECURITY_RESEARCH_VALIDATED`, or `PRODUCTION_READY`. GATE 04B remains PENDING.

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, PostgreSQL-required suites must SKIP, never fabricate PASS.

## GATE 19 — authorized HTTP substrate

**GATE 19 status: PASS** (2026-08-17).

Implementation commit: `95c88bc`

Authoritative tested HEAD: `b442a672a7df86482d0f5a60eb156483b691d44c`

Authoritative environment:

- Kali Linux
- dedicated real PostgreSQL test database
- `RESEARCH_OS_TEST_DATABASE_URL`
- no SQLite substitution
- no skipped tests treated as PASS
- Alembic head `a21_001_session_context`
- GATE 04B remains PENDING
- no live model validation
- no G21 implementation
- repo-wide: unit 676 OK, contract 2 OK, architecture 22 OK, integration 120 OK
- explicit G18 plan binding: 5 OK
- explicit G19 HTTP transaction: 2 OK
- GATE 14 regression: 19 OK, 0 skipped
- GATE 15 regression: 21 OK, 0 skipped
- GATE 16 regression: 34 OK, 0 skipped
- GATE 17 regression: 57 OK, 0 skipped
- only Alembic `path_separator` DeprecationWarning remains; no production-behavior failure

GATE 19 PASS means Research OS can construct and execute typed, capability-bound, Core-authorized general HTTP experiments using bounded request methods, paths, queries, headers and bodies, while preserving exact scope evaluation, redirect reauthorization, capability fingerprint enforcement and Worker execution bounds.

GATE 19 does **not** prove:

- autonomous endpoint discovery
- crawler/recon capability
- browser automation
- arbitrary internet HTTP
- broad vulnerability discovery
- real-world bug bounty performance
- production readiness

Current limitations:

- loopback HTTP substrate only
- no HTTPS breadth claim
- no crawler
- no automatic endpoint discovery
- no browser state
- HTTP transaction does not by itself imply vulnerability semantics

Do not set `LIVE_MODEL_VALIDATED`, `SECURITY_RESEARCH_VALIDATED`, or `PRODUCTION_READY`. GATE 04B remains PENDING. GATE 20 remains PENDING at this closure.

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, PostgreSQL-required suites must SKIP, never fabricate PASS.

## GATE 20 — identity authentication session

**GATE 20 status: PASS** (2026-08-17).

Implementation commit: `e574306`

Authoritative tested HEAD: `b442a672a7df86482d0f5a60eb156483b691d44c`

Authoritative environment:

- Kali Linux
- dedicated real PostgreSQL test database
- `RESEARCH_OS_TEST_DATABASE_URL`
- no SQLite substitution
- no skipped tests treated as PASS
- Alembic head `a21_001_session_context`
- GATE 04B remains PENDING
- no live model validation
- no G21 implementation
- repo-wide: unit 676 OK, contract 2 OK, architecture 22 OK, integration 120 OK
- explicit G18 plan binding: 5 OK
- explicit G19 HTTP transaction: 2 OK
- explicit G20 identity/session: 1 OK
- GATE 14 regression: 19 OK, 0 skipped
- GATE 15 regression: 21 OK, 0 skipped
- GATE 16 regression: 34 OK, 0 skipped
- GATE 17 regression: 57 OK, 0 skipped
- only Alembic `path_separator` DeprecationWarning remains; no production-behavior failure

GATE 20 PASS means Research OS can establish and isolate authenticated sessions for explicitly configured identities and execute authorized HTTP experiments under the correct identity/session context without storing raw credential or session material in the authoritative research state.

GATE 20 does **not** prove:

- autonomous account discovery
- browser authentication
- arbitrary authentication mechanisms
- durable session-secret recovery after restart
- autonomous vulnerability discovery
- real-world bug bounty performance
- production readiness

Current limitations:

- `HTTP_FORM_LOGIN` is the bounded supported auth profile
- session material is process-local/non-durable
- missing session secret after restart requires reauthentication
- session ID alone is not authority
- raw password/cookie/token is not stored in SoR
- no browser login
- no G21 behavior

Do not set `LIVE_MODEL_VALIDATED`, `SECURITY_RESEARCH_VALIDATED`, or `PRODUCTION_READY`. GATE 04B remains PENDING. GATE 19 remains PASS.

If `RESEARCH_OS_TEST_DATABASE_URL` is unset, PostgreSQL-required suites must SKIP, never fabricate PASS.

## Maturity

- ARCHITECTURE_VALIDATED: architecture package complete
- DIAGNOSTIC_E2E_VALIDATED: yes after Gate 12/13 PASS on real PostgreSQL, process crash/restart, and clean install. Not live-model validation.
- LIVE_MODEL_VALIDATED: no while GATE 04B is PENDING
- SECURITY_RESEARCH_VALIDATED: no; GATE 14/15/16/17/18/19/20 PASS cover controlled local pipeline, ground-truth, cross-class, adaptive research-selection, capability/risk/scope substrate, bounded authorized HTTP transaction, and identity/session isolation validation, not broad or real-world security-research validation
- PRODUCTION_READY: no until operational and live-research gates that have not passed actually pass
- GATE 14: PASS (2026-08-17, Kali, dedicated PostgreSQL, 19 E2E OK / 0 skipped)
- GATE 15: PASS (2026-08-17, Kali, dedicated PostgreSQL, GATE14 regression 19 OK / 0 skipped, GATE15 21 OK / 0 skipped)
- GATE 16: PASS (2026-08-17, Kali, dedicated PostgreSQL, GATE14 19 OK / 0 skipped, GATE15 21 OK / 0 skipped, GATE16 34 OK / 0 skipped)
- GATE 17: PASS (2026-08-17, commit 48d807d, Kali, dedicated PostgreSQL, GATE14 19 OK / 0 skipped, GATE15 21 OK / 0 skipped, GATE16 34 OK / 0 skipped, GATE17 57 OK / 0 skipped)
- GATE 18: PASS (2026-08-17, commit 241e901fb2c6730ee293cca71942de45d3796282, Kali, dedicated PostgreSQL, Alembic head a20_001_capability_plan_binding, unit 627 OK, contract 2 OK, architecture 20 OK, integration 117 OK, GATE14 19 OK / 0 skipped, GATE15 21 OK / 0 skipped, GATE16 34 OK / 0 skipped, GATE17 57 OK / 0 skipped)
- GATE 19: PASS (2026-08-17, implementation 95c88bc, authoritative tested HEAD b442a672a7df86482d0f5a60eb156483b691d44c, Kali, dedicated PostgreSQL, Alembic head a21_001_session_context, unit 676 OK, contract 2 OK, architecture 22 OK, integration 120 OK, GATE14 19 OK / 0 skipped, GATE15 21 OK / 0 skipped, GATE16 34 OK / 0 skipped, GATE17 57 OK / 0 skipped)
- GATE 20: PASS (2026-08-17, implementation e574306, authoritative tested HEAD b442a672a7df86482d0f5a60eb156483b691d44c, Kali, dedicated PostgreSQL, Alembic head a21_001_session_context, unit 676 OK, contract 2 OK, architecture 22 OK, integration 120 OK, GATE14 19 OK / 0 skipped, GATE15 21 OK / 0 skipped, GATE16 34 OK / 0 skipped, GATE17 57 OK / 0 skipped)
