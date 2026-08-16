# Data

Data owns the **authoritative persistence spine** for the first future closed research loop.

Spine:

```
Program
→ AuthorizationSource
→ ResearchRun
→ IssuedBudget
Hypothesis / Experiment
→ WorkerResult
→ Observation
+ AuditEvent
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
- Observation is not a vulnerability.
- IssuedBudget is immutable after insert (0 = no allowance).
- AuditEvent is append-only reconstructive history, not Evidence and not a log substitute.
- JSONB is only for untrusted/extensible WorkerResult bags and typed Observation/Audit payloads. It is not scope, authorization, Approval, Evidence, Finding, or budget authority.
- Connection URLs come from the environment (`RESEARCH_OS_DATABASE_URL` / `RESEARCH_OS_TEST_DATABASE_URL`). Use `postgresql+psycopg://…`. Passwords are not logged.

Python records here are **not** language-neutral architectural contracts. Worker wire truth remains `contracts/`.
