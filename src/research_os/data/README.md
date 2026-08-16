# Data

Data owns the **authoritative persistence spine** for the first future closed research loop.

Spine:

```
Program
→ AuthorizationSource
→ ResearchRun
→ IssuedBudget
Hypothesis / Experiment
→ ExecutionAttempt (durable intended Worker invocation)
→ WorkerResult
→ Observation
+ AuditEvent
+ ResearchReasoningRecord (append-only Generator/Falsifier provenance; not Hypothesis truth)
```

This is **not** a database copy of DOMAIN_MODEL.md.

## Owns

- persistence records and ports (Python implementation types, not wire contracts)
- PostgreSQL adapter (`postgres/`) using SQLAlchemy 2 Core + psycopg 3
- synchronous Unit of Work (explicit commit, otherwise rollback)
- Alembic-reviewed schema history

## Does not own

- Core authorization / ExecutionDecision
- Worker execution
- Evidence admission authority (still an open domain decision — no Evidence table)
- Candidate / Finding / Approval persistence
- ScopeRule matcher storage
- model routing, graphs, vectors

## Rules

- Core and Research must not import SQLAlchemy, psycopg, or Alembic.
- Workers must not write the SoR or import these repositories.
- ORM / SQLModel are not used. Table objects are not Domain entities.
- `metadata.create_all()` is not application startup.
- WorkerResult is UNTRUSTED EXECUTION OUTPUT. Inserting it does not create Observation or Evidence.
- Transition A (Application) is the only path that may persist Observation from a completed Worker invocation.
- Observation is not a vulnerability.
- `research_reasoning` is append-only untrusted reasoning provenance. It is not Observation, Evidence, or Hypothesis truth.
- WorkerResult stores first-class request-envelope provenance (`request_id`, correlation, capability/action, authorization decision reference, budget reference). `request_id` is unique (idempotency). Correlation is not JSON-only.
- IssuedBudget is immutable after insert (0 = no allowance).
- AuditEvent is append-only reconstructive history, not Evidence, not a log substitute, and not a dispatch queue.
- ExecutionAttempt is durable dispatch coordination for one intended Worker invocation. It is not Evidence and not a WorkerResult. `request_id` is unique.
- JSONB is only for untrusted/extensible WorkerResult bags and typed Observation/Audit payloads. It is not scope, authorization, Approval, Evidence, Finding, or budget authority.
- Connection URLs come from the environment (`RESEARCH_OS_DATABASE_URL` / `RESEARCH_OS_TEST_DATABASE_URL`). Use `postgresql+psycopg://…`. Passwords are not logged.
- Integration tests require an explicit `RESEARCH_OS_TEST_DATABASE_URL`. They never default to the application URL, never infer `PG*` variables, and refuse SQLite, `postgres`/`template*` catalogs, and a database named `research_os`. The test database name must contain `test`. Tests `TRUNCATE CASCADE` that database only.

Phase A local test cluster (existing WSL PostgreSQL binaries, user-space data dir, no sudo, not Docker architecture):

```
python scripts/start_wsl_test_postgres.py
$env:RESEARCH_OS_TEST_DATABASE_URL = "postgresql+psycopg://research_os_test@127.0.0.1:55432/research_os_test"
uv run python -m unittest discover -s tests/integration -v
```

Python records here are **not** language-neutral architectural contracts. Worker wire truth remains `contracts/`.
