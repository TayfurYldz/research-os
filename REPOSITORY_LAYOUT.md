# Research OS — Repository Layout

This document describes the **actual repository tree**, **package boundaries**, and **import rules**.

It does not replace `.cursor/rules/research-os.mdc`, `PROJECT_STRUCTURE.md`, `DOMAIN_MODEL.md`, `TECHNICAL_REQUIREMENTS.md`, or `TECHNICAL_DECISIONS.md`.

It does not choose frameworks, ORM, API stack, workflow product, secrets product, observability vendor, container runtime, or companion stores.

---

## Tree

```
research-os/
├── src/research_os/          # Python control-plane package (Decision 001)
│   ├── core/
│   ├── research/
│   ├── data/
│   ├── tools/
│   ├── platform/
│   └── interface/
├── contracts/                # Language-neutral contracts (not Python classes)
├── workers/                  # Side-effect runtimes (out of the control-plane package)
│   └── python/
├── integrations/             # Replaceable adapters (not imported by Core/Research)
│   └── strix/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   └── e2e/
├── scripts/
├── docs/
└── var/artifacts/            # Local artifact *byte* adapter (Decision 006); not SoR
```

Constitutional design docs stay at the **repository root**. Do not move them into `docs/`.

---

## Why this split

| Location | Why |
|---|---|
| `src/research_os/` | Control plane in Python: Core, Research, Data access, Tools contracts, Platform **ports**, Interface |
| `contracts/` | Language-neutral schemas/contracts so Workers/Integrations are not Python-locked |
| `workers/` | Out-of-process execution (Decisions 005, 014). May be Python now; other languages later |
| `integrations/` | Concrete adapters. Core and Research **must not** import these |
| `var/artifacts/` | First artifact **byte** store adapter (local filesystem). Identity/hash stay in PostgreSQL |

Workers and Integrations are **not** subpackages of `research_os`. That keeps “do not import concrete Integrations from Core/Research” visible in the tree.

---

## Package boundaries (`src/research_os`)

### `core`

Highest-trust control logic: `request → policy → scope → budget → execution`, Approval semantics, Finding promotion **contract**.

Must not: side effects, tool/provider SDKs, Integration/Platform **implementations**, model-specific logic, declaring targets authorized from LLM output.

Must not depend on `research`.

### `research`

Proposals only: Hypothesis, Experiment plans, Evidence **proposals**, Candidate/Verification/FindingProposal logic.

Must not: execute, change Core decisions, import Integrations or concrete Platform adapters, treat model output as fact/Evidence/Finding.

May depend on Core **contracts**, not on Interface.

### `data`

Persistence of domain records and Artifact **metadata/reference**. PostgreSQL is the SoR (Decision 003). Research Memory is a **read model**, not truth (Decision 009).

Must not: promotion decisions, leaking ORM/SQL dialect into Core/Research domain contracts, storing secret **values** (Decision 013).

Artifact **bytes** are not this package’s default store (Decision 006).

### `tools`

Capability **contracts** (HTTP, browser, shell, recon, …). No side effects. No vendor implementations.

### `platform`

**Ports** only for this slice: orchestration coordination (Decision 004), secrets (013), observability (012), artifact bytes (006), isolation primitives (014).

Must not: own policy, own Evidence/Finding, select Temporal/Redis/Vault/Docker here.

Concrete adapters, when written later, still must not be imported by Core/Research.

### `interface`

Operator/API/CLI/Human Review **surfaces**. Phase A: application/API boundary + minimal CLI + minimal Human Review (Decision 011). No framework chosen.

Must not: own Approval semantics, bypass Core, write PostgreSQL authority directly, collapse AI recommendation into judgment.

---

## Allowed dependency direction

```
interface → research → core → (tools | data | platform) *contracts*
```

Concrete implementations:

- `workers/`
- `integrations/`
- later Platform adapters

These implement contracts; they are not imported by `core` or `research`.

Trust (not the same as imports): Core > Research > Interface/orchestration callers. Workers and Integrations are lower trust. Model output and WorkerResult remain untrusted until the documented transitions.

---

## `contracts/`

Language-neutral. Serialization/validation strategy is still an open technical question (`TECHNICAL_REQUIREMENTS.md`).

Intended contents later: Worker job/result, ModelPort, SecretReference, authorization request/decision, Artifact locator (opaque), observability correlation fields.

Not Python modules. Not vendor SDKs.

---

## `workers/`

Only layer that may perform side effects, and only after Core authorization.

- In-process Workers: **test doubles only** (Decision 005).
- First tool-execution environment: Kali/WSL **adapter location**, not architecture.
- Must not write SoR, self-authorize, widen scope, or change budget.
- WorkerResult is untrusted until Transition A.

`workers/python/` is the first **runtime** location, not a commitment that all Workers stay Python.

---

## `integrations/`

Replaceable connectors. `integrations/strix/` is a **reserved adapter slot**. Strix is optional, not Research OS, not Core, not ModelPort owner (Decisions 005, 008, 015).

Core/Research must not import `integrations/`.

---

## `tests/`

| Tree | Intent |
|---|---|
| `unit/` | Layer-local tests (especially Core invariants) |
| `contract/` | Language-neutral contract fixtures vs Core/Research/Worker boundaries |
| `integration/` | PostgreSQL, local Worker process, filesystem artifact adapter — when those exist |
| `e2e/` | Operator → authorization → WorkerResult → Transition A → Human Review → Approval — later |

No test framework is chosen in this document.

---

## `var/artifacts/`

Decision 006 first adapter: local filesystem bytes. Opaque locators only in SoR. Not Evidence. Not committed as domain truth. Windows paths must not enter Domain/Core contracts.

---

## Explicitly not in this layout

- API framework, web framework
- workflow/queue/broker product
- cache/vector/graph/search product
- secrets or observability vendor
- container/Kubernetes manifests as architecture

Packaging (`pyproject.toml`, `uv.lock`) and the PostgreSQL adapter (SQLAlchemy 2 Core, Alembic) now exist. They are not Domain/Core architecture. ORM is not used.

---

## Import rules (enforced later by tests, not by this file)

1. `core` does not import `research`, `interface`, `integrations`, or `workers`.
2. `research` does not import `interface`, `integrations`, or `workers`.
3. `core` and `research` do not import concrete Platform adapters.
4. Secret **values**, provider SDKs, and Strix clients do not appear in `core` or `research`.
5. Models are not authorization principals.
