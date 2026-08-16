# Research OS — Implementation Plan

Roadmap only. No business logic, products, or frameworks are selected here.

Follow `.cursor/rules/research-os.mdc`, `PROJECT_STRUCTURE.md`, `DOMAIN_MODEL.md`, `TECHNICAL_REQUIREMENTS.md`, and `TECHNICAL_DECISIONS.md`.

Decision-driver order remains: correctness → authorization/security → durability → audit/provenance → recoverability → simplicity → testability → …

---

## Locked context (do not reopen in code)

| Decision | Lock |
|---|---|
| 001 | Python control plane; Workers/Integrations may differ; language-neutral contracts |
| 002 | Relational SoR; rebuildable read models; companions non-authoritative |
| 003 | PostgreSQL SoR; not Research Memory; not default artifact bytes |
| 004 | Hybrid orchestration; engine **product deferred** |
| 005 | Mixed topology; Worker contract; Kali/WSL first **tool** Worker; no mandatory broker |
| 006 | Artifact metadata/hash in SoR; bytes behind port; local FS first |
| 007 | No dedicated cache product in v1 |
| 008 | ModelPort; provider **deferred**; no live multi-model router |
| 009 | No vector in v1; Research Memory = structured/text over SoR |
| 010 | Staged deploy; Phase A local Control Plane + local PostgreSQL + Kali/WSL Worker |
| 011 | Staged Interface; no full dashboard required in v1; UI frameworks **deferred** |
| 012 | ObservabilityPort; structured logs first; vendors **deferred** |
| 013 | SecretPort; values never in Domain/prompts/AuditEvent; product **deferred** |
| 014 | Process/OS boundary; in-process = fakes; containers **not** required |
| 015 | Identity classes; operator id for audit/Approval; authn ≠ authz; no IAM product |
| 016 | JSON Schema Draft 2020-12 canonical contracts; Python classes are not contract truth |
| 017 | False-positive suppression; signal ≠ Evidence ≠ Finding; INCONCLUSIVE valid; confidence deferred |
| 018 | Realistic novelty N1/N2/growing N3; N4 not promised; Research Brain in Research, not Core |
| 019 | PEP 621 pyproject.toml; Hatchling; uv installer/lock (replaceable); Python >=3.11 |
| 020 | SQLAlchemy 2 Core + psycopg 3 + Alembic; sync Data adapter; no ORM; no SQLite-as-Postgres |
| 021 | Canonical schemas stay `contracts/`; first local transport = one-shot JSON stdin/stdout; jsonschema runtime validation (local URN, no network); `WorkerInvocationOutcome` ≠ `WorkerResult` |
| 022 | Explicit Application layer owns use-case coordination; not authority; no concrete adapters |
| 023 | Transition A: COMPLETED+valid WorkerResult only; trusted-request normalizer registry; request_id idempotency; WorkerResult+Observation+AuditEvent one UoW |

---

## Standing invariants (every slice)

- DEFAULT DENY. Core authorizes; Workers execute; Data persists.
- WorkerResult untrusted until Transition A. Evidence only via Transition B.
- Finding only after Human Review and Core-recorded Approval.
- Finding never from model output, scanner signal, WorkerResult, or confidence score alone (Decision 017).
- Interface does not own Approval. Models are not principals.
- PostgreSQL wins vs companions, logs, traces, metrics, caches, vector indexes (none in v1).
- Secret **values** never logged or stored as Domain.

---

## Phase A — first working implementation

Matches Decision 010 Phase A and Decision 011 Phase A.

### Slice A0 — Layout (this commit)

Repository tree, package boundaries, empty ports. **Done when this layout exists.** No runtime.

### Slice A1 — Worker execution contracts

Canonical JSON Schema Draft 2020-12 files under `contracts/v1/` (Decision 016).

**A1 wire contracts (Worker execution boundary only):**

- CorrelationContext
- ExecutionBudget
- SecretReference
- WorkerRequest
- WorkerResult
- ReauthorizationRequest

This slice does **not** define authorization request/decision wire contracts. Those belong in Core (A2) as domain/authority model; a cross-process/wire contract is added later only if that boundary is actually needed.

This slice does **not** define Artifact identity/reference/hash wire contracts. Artifact domain metadata is designed in A3 (Data) and/or A4 (artifact byte port) once that boundary is clear.

**Verify:** `python scripts/check_contracts.py` (contract lint / structural checks, not a Draft 2020-12 semantic validator). `$ref` values are canonical URNs, not filesystem paths. No extra wire contracts “because the old roadmap listed them.”

### Slice A2 — Core (no I/O)

Authorization, scope, budget **policy**, Approval **semantics**, Finding promotion **contract**. In-memory tests only.

Authorization request/decision remain Core domain/authority model in this slice. They become separate `contracts/` wire schemas only if a real cross-process boundary requires them.

**Verify:** missing AuthorizationSource or ambiguous scope → DENY or REQUIRE_HUMAN_REVIEW. LLM-shaped input cannot authorize. No subprocess, no SDKs.

### Slice A3 — Persistence spine (PostgreSQL)

**Data access (Decision 020):** SQLAlchemy 2 Core + psycopg 3 + Alembic, synchronous Data adapter, explicit Unit of Work. **No ORM. No SQLModel.** SQLite is not a PostgreSQL substitute.

A3 implements a **minimum authoritative persistence spine**, not the complete domain schema:

Program → AuthorizationSource → ResearchRun → IssuedBudget → Hypothesis → Experiment → WorkerResult → Observation, plus AuditEvent.

**Deliberately deferred** until their domain semantics are ready (do not invent them as JSON authority):

- ScopeRule matcher definitions (grammar/normalization not locked)
- Evidence (Evidence admission authority is still an open domain question)
- Candidate, Verification, FindingProposal, Finding, Approval
- Snapshot, ChangeEvent, graphs, vectors, model routing

Artifact identity/reference/hash as a **wire** contract is not part of A1. Decide that boundary here and/or in A4 (byte port) when the cross-process need is real.

**Verify:** Alembic upgrade is the schema path (`create_all` is not startup). Core/Research import no SQLAlchemy/psycopg/Alembic. WorkerResult insert does not create Observation or Evidence. IssuedBudget is immutable after insert; 0 is no allowance. AuditEvent is append-only. Integration tests run only when `RESEARCH_OS_TEST_DATABASE_URL` is set.

**A3 PostgreSQL validation debt:** skipped integration tests are **PENDING, not PASS**. Before the first E2E vertical research loop is accepted, `tests/integration` against a real PostgreSQL URL **must** pass. Do not install Docker automatically. If `RESEARCH_OS_TEST_DATABASE_URL` is absent, report PENDING.

### Slice A4 — Minimal out-of-process Worker runtime (Decision 021)

Prove the execution boundary, not a scanner:

```
canonical WorkerRequest
  → WorkerPort
  → LocalProcessWorkerAdapter (argv, no shell)
  → one-shot child process
  → isolated diagnostic Worker
  → WorkerInvocationOutcome (optional canonical WorkerResult)
```

- First local transport: JSON over stdin/stdout; stderr diagnostics. **Not** architecture. Not HTTP/broker/RPC.
- One-request-per-process is the **first implementation**, not permanent topology.
- Runtime Draft 2020-12 validation via `jsonschema` over local URN `$id`. No network schema fetch. `scripts/check_contracts.py` remains structural lint.
- `WorkerInvocationOutcome` ≠ `WorkerResult`. Crash/timeout/invalid JSON do not fabricate a WorkerResult.
- Production capability: `diagnostic.echo` only. Test-only failure modes live in fixture programs, not the production registry.
- Worker lives in `workers/python/`. It does not import Core/Data/PostgreSQL and does not write the SoR.
- This slice does **not** persist WorkerResult, run Transition A, or produce Observation/Evidence/Candidate/Finding.

Original roadmap items that remain later Platform work (not this A4): SecretPort product, ObservabilityPort vendor, artifact byte adapter, orchestration engine.

**Verify:** unit + `tests/contract` + `scripts/check_contracts.py`. Core/Research import neither `subprocess` nor `local_process_worker`. Worker imports neither `research_os` nor SQLAlchemy/psycopg. Correlation mismatch is fail-closed. Bounded stdout/stderr.

### Slice A6-lite — Transition-A spine (Decisions 022–023)

valid COMPLETED Worker invocation → Application `IngestCompletedWorkerInvocation` → deterministic `diagnostic.echo` normalizer → Observation persistence.

- Application layer owns the use case. Core/Research/Platform/Interface do not.
- Only COMPLETED + valid WorkerResult may ingest. Transport failures are not WorkerResult rows.
- BLOCKED/EXECUTION_FAILED diagnostic results may persist WorkerResult with `NO_OBSERVATION`.
- Idempotency identity is `request_id` (unique). Payload-equal distinct requests are not collapsed.
- Alembic revision `a6_001_transition_a_provenance` adds envelope columns. Do not rewrite `a3_001`.
- No Evidence, Candidate, Finding, scanner, or Research Brain.

**Verify:** unit + contract + architecture. PostgreSQL integration when `RESEARCH_OS_TEST_DATABASE_URL` is set; otherwise PENDING.

### Next planned slices (not implemented here)

### Slice A7-lite — Hypothesis / Experiment feedback

One minimal Hypothesis → Experiment → authorized Worker → ingested Observation feedback cycle.

### FIRST VERTICAL RESEARCH LOOP GATE

Requires A3 PostgreSQL integration tests **actually passing**, plus A4 runtime + A6-lite + A7-lite. Proves the control loop, not vulnerability discovery.

### Slice A5 — Research (proposals)

Hypothesis / Experiment **plan** / Evidence **proposal** / Candidate / FindingProposal. ModelPort **fake** adapter in tests.

**Verify:** Research cannot create Finding. Model output stays UNTRUSTED STRUCTURED PROPOSAL. Full A5 does not block proving the minimal control loop.

### Slice A6 — Interface Phase A

Application/API **boundary** (no API framework chosen until a later decision) + minimal CLI + minimal Human Review that submits Approval to Core.

**Verify:** UI/CLI cannot write Findings into PostgreSQL. Operator identity on Approval (Decision 015).

### Slice A7 — Kali/WSL tool-Worker adapter slot (after A4)

First **local diagnostic** Worker runtime is delivered in A4. Remaining A7 work is the Kali/WSL **tool** environment adapter when a real (still replaceable) tool Worker is justified — not a recon framework, not Strix-as-architecture.

**Verify:** out-of-process; crash does not kill Core; no SoR writes from Worker; redirect → stop → Core re-eval; correlation id present.

### Slice A8 — Transition B (after A6-lite Observation ingest)

A6-lite persists Observation. Remaining: Artifact metadata/bytes via port, then **separate** Evidence admission (Transition B).

**Verify:** no Evidence at Observation ingest. Artifact attachment ≠ Evidence.

### Slice A9 — First Human Review loop

FindingProposal → Interface review → Core Approval → Finding. AuditEvent for the decision.

**Verify:** no Finding without Approval. Logs are not the audit authority (Decision 012).

---

## Phase B — replaceable Workers and dashboard

- Same Worker contract → authenticated remote Worker **when needed** (not now).
- Interface Phase B: web dashboard (**framework still a later decision**).
- ModelPort: one real adapter when a provider is chosen (Decision 008 product still deferred).
- `integrations/strix/` only if explicitly adopted as a replaceable adapter.

---

## Phase C — production topology if justified

Distributed Control Plane/Workers, object-store artifact adapter, external secrets manager, observability backend, stronger isolation — **each requires a decision revisit**. No Kubernetes-by-default.

---

## Explicitly later / not this roadmap’s job

- API framework, web framework
- Temporal/Celery/Prefect, brokers, Redis
- Vector/graph/search products
- Embedding pipeline
- Full observability platform
- Docker/Kubernetes as architecture
- Multi-model live routing

---

## Suggested test order

1. `tests/unit/` — Core deny/allow, promotion contract, immutability rules
2. `tests/contract/` — WorkerResult and authorization message shapes
3. `tests/integration/` — PostgreSQL transactions; filesystem artifact adapter
4. `tests/e2e/` — one authorized run through Human Review

---

## Definition of “first working implementation”

A single operator can:

1. Record Program + AuthorizationSource + ScopeRules
2. Start a ResearchRun under Core
3. Dispatch an authorized Worker job
4. Ingest WorkerResult (Transition A)
5. Admit Evidence (Transition B) only as a separate step
6. Open a FindingProposal
7. Record Human Review as Core Approval
8. Persist a Finding only after that Approval

All of that uses this repository layout, PostgreSQL as SoR, and no extra product mandated by this plan.

Research Brain (target/state model, invariant mining, differential engine, exploration policy) is **not** required for this first working implementation. It is later Research work (Decisions 017–018), not Core.

---

## Vertical-slice gate (after A3 spine exists)

After the minimum persistence, Worker, orchestration, and Research pieces exist, prove an **end-to-end control loop** before broad horizontal schema expansion:

```
Program
→ AuthorizationSource
→ ResearchRun
→ Hypothesis
→ Experiment
→ Core ExecutionDecision
→ WorkerRequest
→ Worker
→ WorkerResult
→ Transition A
→ Observation
→ Research feedback
```

This gate does **not** claim vulnerability discovery. It proves the research control loop. It is **not** implemented in A3 or A4.

**Hard prerequisite:** A3 PostgreSQL integration tests must PASS against `RESEARCH_OS_TEST_DATABASE_URL`. Skipped tests are PENDING.

---

## Research Brain (future Research capability — not Core)

Not a Phase A slice. Not a Core module. Not a graph/database product. Not required to declare the first working implementation done.

When Research Brain is designed, it must be architecturally capable of:

- persistent target / state model (capability, not a schema in this plan)
- invariant hypotheses (hypothesis ≠ fact)
- differential reasoning (anomaly ≠ vulnerability)
- independent verification (Decision 017; not a required second model vendor in v1)
- counter-hypothesis / disconfirming evidence
- negative evidence that stays **context-bound**

It must not reduce to “ask the LLM for vulnerability ideas” or `LLM → tool → LLM`.

Exploration remains Core-authorized: no scope, budget, or side-effect bypass.

---

## Advanced Research (later than first working implementation)

After the first Human Review loop exists and metrics can be read from the SoR:

- chain search (N2)
- temporal prioritization
- exploration vs exploitation policy (no frozen weights)
- novelty / information-gain factors (conceptual; no fake formula)
- duplicate reduction (duplicate semantics still an open domain question)
- empirical calibration of claims (Decision 018 anti-hype metrics)

These stay in **Research** (plus Data records and ObservabilityPort aggregates). Do not move them into Core.
