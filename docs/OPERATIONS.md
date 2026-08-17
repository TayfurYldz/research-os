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

Each configuration is probed independently:

1. NOT_INSTALLED — executable missing
2. INSTALLED / VERSION_KNOWN — `codex --version` succeeded
3. AUTH_READY — `codex login status` exit 0
4. DIAGNOSTIC_READY / MODELPORT_COMPATIBLE — request-consuming `codex exec --ignore-user-config --ephemeral --sandbox read-only -m <model>`
5. BENCHMARK_COMPATIBLE — AUTH_READY and that model's request-consuming exec succeeded

Compatibility is not inferred across Codex configurations. Discovering two configs is not GATE 04B PASS.

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

## Maturity

- ARCHITECTURE_VALIDATED: architecture package complete
- DIAGNOSTIC_E2E_VALIDATED: yes after Gate 12/13 PASS on real PostgreSQL, process crash/restart, and clean install. Not live-model validation.
- LIVE_MODEL_VALIDATED: no while GATE 04B is PENDING
- SECURITY_RESEARCH_VALIDATED: no until authorized real-world research is proven
- PRODUCTION_READY: no until operational and live-research gates that have not passed actually pass
