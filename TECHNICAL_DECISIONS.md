# Research OS — Technical Decisions

This file records explicit technical decisions.

It does not replace `.cursor/rules/research-os.mdc`, `PROJECT_STRUCTURE.md`, `DOMAIN_MODEL.md`, or `TECHNICAL_REQUIREMENTS.md`.

Decisions must stay inside those documents. A language choice does not choose a framework, database, orchestrator, broker, or provider.

---

# Decision 001 — Primary Programming Language

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Confidence:** MEDIUM

Primary language for the first implementation of Core, Research, Data access, Platform control-plane code, and Interface/application logic:

**Python**

Python is the primary first-implementation language.

That does **not** mean:

- every Worker must be Python
- every Integration must be Python
- performance-critical components must stay Python

Core/Research contract boundaries stay language-independent.

No web framework, CLI framework, ORM, database, orchestrator, or serialization format is chosen here.

Windows + Cursor and Kali/WSL are current development context. They are used only to check portability/integration. They are not the reason Python is selected.

This decision must remain valid even if deployment later moves entirely to Linux or remote workers.

---

## Gate then differentiate

`TECHNICAL_REQUIREMENTS.md` decision-driver order is not changed. Correctness and authorization/security boundaries are not ranked below simplicity.

### Stage 1 — Mandatory gates

A language is eliminated if it cannot support:

- correctness
- authorization/security boundaries
- durable state integrity
- auditability
- explicit contracts

Python, TypeScript/Node.js, Go, and Rust can all pass Stage 1. None is eliminated for lack of capability.

Go provides stronger compile-time enforcement for some correctness/security properties.

Python meets the same gates when the constraints in this decision are enforced:

- explicit domain boundaries
- language-neutral schemas
- runtime validation
- tests
- static analysis where practical

### Stage 2 — Differentiators among viable options

Among languages that pass Stage 1:

- developer simplicity
- iteration speed
- ecosystem fit
- maintainability
- operational simplicity

The Python vs Go difference is a Stage 2 difference, not a Stage 1 failure of Go.

---

## Language-neutral contracts

Cross-boundary contracts are not Python classes as architectural truth.

Contracts must be:

- language-neutral
- explicit
- versionable
- machine-validatable
- serializable/transport-neutral in principle

Python types/classes may be one implementation representation of those contracts.

A later Go Worker, Rust Worker, or TypeScript integration must be able to implement the same boundaries.

No serialization format is chosen here.

---

## Python

### Strengths

- Faster Research/domain iteration on a provenance-heavy model (Program, Evidence, Candidate, FindingProposal, lifecycles).
- Richer LLM tooling ecosystem for untrusted structured proposals.
- More convenient experimentation for a single developer.
- Lower first-implementation friction.
- Less initial glue for common security/AI workflows (wrappers and examples around CLI tools and model clients).
- Workers in another language remain possible because Core must talk to contracts, not in-process tools.

### Weaknesses

- Fewer compiler-enforced guarantees than Go, TypeScript, or Rust.
- Weaker default concurrency for CPU-bound work (GIL); mixed I/O/CPU in the control plane needs care.
- Long-running process hygiene (memory growth, dependency drift) needs explicit operational care.
- Easy to bury Core policy in scripts or tool helpers if constraints are not enforced.
- Runtime errors that a compiler would reject can reach execution if schemas/tests are thin.

### Project-specific fit

- Passes Stage 1 if documented Core constraints are enforced.
- Wins Stage 2 for this project’s first implementation: Research/domain iteration, LLM experimentation convenience, and lower single-developer glue.
- Python’s advantage is **not** unique capability. Go can call model/provider APIs, exec tools, and run the control plane without Python.

### Risks

- Core invariants (DEFAULT DENY, budget immutability, Transition A vs B) weaken if boundaries are informal.
- Packaging/deployment:
  - interpreter/version consistency
  - dependency pinning
  - host vs WSL environment drift
  - native dependency complications
  - reproducible environment creation
  - deployment artifact consistency
- These packaging concerns are later technical decisions; no package manager is chosen here.
- LLM client libraries can pull Core/Research toward vendor-shaped APIs unless providers stay behind replaceable ports.
- If deterministic normalization/ingestion (Transition A) becomes CPU-heavy or throughput-critical, that component may move behind a language-neutral contract to Go, Rust, or another runtime. This primary-language decision does not block that.

---

## TypeScript / Node.js

### Strengths

- Excellent static contract ergonomics.
- Strong application/dashboard ecosystem.
- Good async I/O model for a control plane that waits on model calls and worker results.
- Cross-platform on Windows and Linux is solid.
- Capable of calling model APIs and executing subprocess tools; it is not “weak for backend.”

### Weaknesses

- Security/research Python ecosystem is a weaker match for first-phase Worker/tool adapters.
- External CLI/security-tool integration has less operator ergonomics than Python.
- Research/AI experimentation libraries are capable but less convenient than Python for this domain.
- Runtime and packaging (Node version, native addons) add operational surface.

### Project-specific fit

- Passes Stage 1, with especially strong contract ergonomics.
- Not primary because Stage 2 research/security-tool and AI-experimentation fit is weaker than Python for this project’s first loop.
- A later dashboard/Interface in TypeScript remains possible and is not decided here.

### Risks

- Using TypeScript as primary does not require a Python sidecar. It would cost more glue for common security/AI workflows than Python.

---

## Go

### Strengths

- Stronger compile-time guarantees.
- Simpler deployment artifact (static binary).
- Predictable long-running service behavior.
- Strong concurrency primitives.
- Lower runtime operational complexity.
- Good fit for Core/policy/control-plane components.
- Good subprocess and network execution support.
- Can call model/provider APIs directly.
- Can execute subprocess-based tools.
- Can integrate with Strix through contracts/adapters.
- Can implement the entire control plane without Python.

### Weaknesses

- Slower first-loop Research/domain iteration for this project’s current team/context.
- Less convenient AI/research experimentation ecosystem.
- More implementation ceremony for a rapidly evolving Research domain.
- Security-tool wrapping is mostly “exec the binary,” with fewer high-level examples than Python.

### Project-specific fit

- Passes Stage 1. Strongest of the four as a pure control-plane language.
- Not selected as primary because of Stage 2: slower Research/domain iteration and less convenient AI/security-workflow experimentation.
- Go is not missing capability. Python is chosen because it also satisfies mandatory gates **if the documented constraints are enforced**, and it is more productive for the first Research OS implementation.

### Risks

- If chosen as primary, delivery of the hypothesis → experiment → WorkerResult → Evidence admission loop would likely be slower, not impossible.
- Ad-hoc helper scripts in another language would still be a discipline problem, as with Python.

---

## Rust

### Strengths

- Strongest memory and type safety among the candidates.
- Excellent isolation/performance potential.
- Useful future Worker/runtime candidate.
- Explicit types and enums express authorization/state machines well.

### Weaknesses

- Highest iteration cost and complexity for one developer on a large domain model.
- Development velocity is the lowest of the four for v1.
- Ecosystem friction for Research/LLM experimentation.
- Everyday control-plane iteration on mixed Windows/Linux hosts is heavier.

### Project-specific fit

- Passes Stage 1.
- Not primary for first implementation because of iteration cost, complexity, velocity, and Research/LLM ecosystem friction.
- Appropriate later for a Worker/runtime if isolation or throughput triggers appear.

### Risks

- Delivery stall; temptation to over-abstract.
- Control-plane memory safety does not replace Worker isolation or Core policy.

---

## Comparison Matrix

Scores are 1 (worse project fit) to 5 (better project fit) for this project’s first implementation. Higher is always better.

| Criterion | Python | TypeScript / Node.js | Go | Rust | Why |
| --- | --- | --- | --- | --- | --- |
| 1. correctness | 3 | 4 | 4 | 5 | All four can implement invariants. Go/TS/Rust get more compile-time help. Python relies on schemas, tests, and analysis. |
| 2. security boundary implementation | 3 | 3 | 4 | 5 | Boundaries are architectural. Go/Rust make accidental in-process sharing harder. Python/TS rely more on process isolation plus constraints. |
| 3. explicit / machine-validatable contracts | 3 | 5 | 4 | 5 | TS has the best contract ergonomics. All four can validate language-neutral schemas. Python’s compiler will not. |
| 4. domain model expressiveness | 5 | 4 | 3 | 3 | Nested lifecycles and optional provenance iterate fastest in Python. |
| 5. testability | 4 | 4 | 4 | 4 | All four can unit-test Core/Research. |
| 6. AI / LLM ecosystem convenience | 5 | 4 | 3 | 2 | Convenience, not capability. Go/TS can call model APIs. Python has richer experimentation libraries. |
| 7. security-tool wrapping convenience | 5 | 3 | 4 | 3 | All can exec CLI tools. Python has more existing wrappers/examples. Go’s subprocess support is strong. |
| 8. local/remote worker portability | 4 | 4 | 5 | 3 | Any language can talk to replaceable workers. Go binaries travel cleanly. This row is not a Kali-mandates-Python score. |
| 9. subprocess / external tool integration | 4 | 3 | 5 | 4 | Go and Python are both strong at subprocess control. |
| 10. async / concurrency model | 3 | 4 | 5 | 4 | Go is simplest for mixed concurrency. Python is weaker for CPU-bound control-plane work. |
| 11. long-running control-plane suitability | 3 | 4 | 5 | 4 | Go is built for this. Python works with operational care. |
| 12. cross-platform Windows/Linux development | 4 | 4 | 5 | 3 | Portability check only. Go is simplest to ship across hosts. |
| 13. library ecosystem convenience | 5 | 4 | 4 | 3 | Python reduces first-loop glue for research/AI workflows. |
| 14. observability support | 4 | 4 | 5 | 4 | All can emit structured telemetry. Go’s long-running service culture is strongest. |
| 15. developer simplicity | 5 | 4 | 4 | 2 | Stage 2. One developer, local first: Python has the lowest coordination cost. |
| 16. implementation speed | 5 | 4 | 3 | 1 | Stage 2. First Evidence/FindingProposal loop is fastest in Python. |
| 17. maintainability | 3 | 4 | 5 | 4 | Unchecked Python degrades. Go stays readable. TS stays maintainable if types stay strict. |
| 18. performance | 3 | 3 | 4 | 5 | Not a Stage 1 differentiator. Workers may move later. |
| 19. operational simplicity | 3 | 3 | 5 | 4 | Higher is simpler operations. Go’s single binary scores highest. Python/TS need a managed runtime. |
| 20. future move of hot components | 5 | 4 | 4 | 3 | Language-neutral contracts make Python-primary + later Go/Rust workers straightforward. |

No additional language was added.

---

## Decision

**ACCEPT WITH CONSTRAINTS**

**Primary language: Python**

Python is selected because it satisfies the mandatory architecture/security gates and provides the best current first-implementation productivity for Research OS.

Go remains a credible alternative, especially for Core/control-plane/runtime components.

Go is not rejected for missing capability. It can call model/provider APIs, execute subprocess tools, integrate Strix through adapters, and implement the entire control plane without Python.

Python’s v1 advantage is Stage 2:

- faster Research/domain iteration
- richer LLM tooling ecosystem
- more convenient experimentation
- lower single-developer implementation friction
- less initial glue for common security/AI workflows

The decision is ACCEPT WITH CONSTRAINTS rather than unconditional ACCEPT because Python provides fewer compiler-enforced guarantees and carries packaging/concurrency risks.

This is not “Python because AI,” “Python because Windows/Kali,” or “simplicity outranks security.”

---

## Constraints

Python is the primary first-implementation language for Core, Research, Data access, Platform control-plane logic, and application/Interface code.

Workers and Integrations may be another language. Performance-critical or isolation-critical components may move behind language-neutral contracts (Transition A / WorkerResult). They must not be inlined into Core.

Until a later recorded decision splits them, Core and Research stay in the primary language **and** must obey:

- public boundaries validated
- no raw dict-shaped domain contracts at critical boundaries
- explicit state transitions
- no hidden mutable global state
- no policy logic inside scripts
- no subprocess calls from Core/Research
- no provider/tool SDK dependency in Core/Research
- tests for domain invariants
- static analysis/type checking where practical
- runtime validation at trust boundaries

No library or framework is named here.

Python types are not architectural contracts. Contracts remain language-neutral.

Python does not create vendor lock-in by itself. Lock-in appears only if Core/Research depend on a specific provider SDK or tool. That remains forbidden.

---

## Rejected Alternatives

- **Go:** Credible Stage 1 option and often stronger for Core/control-plane compile-time guarantees, deployment artifact, concurrency, and long-running behavior. Not primary today because of slower first-loop Research/domain iteration, less convenient AI/research experimentation, and more ceremony for a rapidly evolving Research domain—while Python still meets mandatory gates under the constraints above.
- **TypeScript / Node.js:** Excellent static contract ergonomics, strong application/dashboard ecosystem, good async I/O, and a capable backend. Not primary because security/research-tool and Research/AI experimentation ergonomics are a weaker Stage 2 fit than Python. Not rejected as “weak for backend.”
- **Rust:** Strongest memory/type safety and a strong future Worker/runtime candidate. Not primary because of iteration cost, complexity, velocity, and Research/LLM ecosystem friction for first implementation.

---

## Revisit Triggers

Reopen this decision only with measured evidence in these categories (no numeric thresholds invented):

- repeated Core invariant bugs despite validation/tests
- control-plane concurrency bottleneck
- CPU-bound deterministic ingestion / Transition A becoming throughput-critical
- memory pressure in the long-running control process
- deployment/packaging instability (interpreter drift, pinning, host vs WSL, native deps, irreproducible environments)
- worker throughput constrained by the control plane rather than by tool/network budget
- isolation requirements that favor another runtime
- cross-platform runtime drift
- operational burden exceeding expected simplicity

If Transition A becomes CPU-heavy or throughput-critical, that component may move behind a language-neutral contract to Go/Rust/another runtime without reversing Python as the primary control-plane language unless other triggers also fire.

---

## Confidence

**MEDIUM**

Python satisfies Stage 1 with constraints and wins Stage 2 for first-implementation productivity. Confidence is not HIGH because Python provides fewer compiler-enforced guarantees than Go and carries packaging/concurrency risks. Go remains the leading alternative if revisit triggers appear.

---

# Decision 002 — Primary Data Strategy / Database Paradigm

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Confidence:** MEDIUM

Primary data strategy for the first implementation:

**Relational primary system of record, with rebuildable read models and optional companion stores later.**

This is a paradigm decision. It does not choose a database product, ORM, cache, vector store, graph product, object store, or search product.

It does **not** mean:

- AssetRelation exists → a graph database is required
- flexible metadata → a document database is required
- AuditEvent / immutable Evidence exist → the whole domain must be event-sourced
- AI exists → a vector database is required
- artifacts exist → an object store is required immediately
- relational primary → all data lives in one relational product forever
- a companion store is a second source of truth
- a companion index may override the System of Record
- flexible JSON/schemaless payload may hold authority truth
- Evidence, AuditEvent, or recorded Approval may be edited or rewritten in place
- relational paradigm → a specific database product

---

## System of Record vs read models vs companions

### System of Record

The single authoritative strategy for domain truth.

Authoritative here: Program, AuthorizationSource, ScopeRule, ResearchRun, Budget, Asset, AssetRelation, Observation, Hypothesis, Experiment, WorkerResult (durable untrusted capture), Artifact identity/reference and integrity/lifecycle metadata, Evidence, Candidate, Verification records, FindingProposal, Finding, Approval, Snapshot, ChangeEvent, AuditEvent.

WorkerResult is durable capture, not Observation/Evidence/Finding truth. Research Memory is not in this set.

### Read models

Rebuildable views over the System of Record: Research Memory retrieval, dashboard views, temporal slices, search projections.

A read model that cannot be rebuilt from the System of Record is a design error.

### Companion stores

Later, optional capabilities for full-text search, semantic/vector retrieval, graph acceleration, analytics, or artifact bytes.

Every derived companion index/read model must be rebuildable from the authoritative System of Record. This includes:

- search indexes
- semantic/vector indexes
- graph projections
- dashboard projections
- Research Memory projections
- temporal/materialized read models

A companion store never becomes authoritative truth automatically. If it disagrees with the System of Record, the companion is corrected or rebuilt. The System of Record is not changed to match the companion. The companion is never the authoritative conflict winner.

**Exception:** Artifact bytes may sit outside this rebuild-from-SoR rule because artifact byte-storage topology is a separate technical decision. Artifact metadata, reference, and provenance remain authoritative in the System of Record.

Artifact byte-storage topology/product is **not** decided here. Semantic/vector, search, graph companion, and analytics strategies are **not** decided here.

---

## Gate then differentiate

`TECHNICAL_REQUIREMENTS.md` decision-driver order is not changed.

### Stage 1 — Mandatory gates

A strategy is eliminated if it cannot support:

- domain integrity
- authorization/security consistency
- durable authoritative truth
- auditability/provenance
- explicit lifecycle semantics

Especially: Approval and Finding creation must not contradict; Evidence provenance must hold; Audit history must be reconstructable; Transition A and Transition B must remain distinct.

### Stage 2 — Differentiators among viable options

- developer simplicity
- operational simplicity
- query ergonomics
- evolution
- future extensibility
- performance profile

---

## Immutability model

Not every record is immutable.

**Mutable lifecycle records** (current state, with history via AuditEvent / new rows where needed):

- ResearchRun
- Experiment
- Hypothesis belief/status
- Candidate lifecycle
- FindingProposal lifecycle

**Append / immutable-oriented records** (do not rewrite in place as truth):

- WorkerResult raw capture
- Artifact integrity metadata
- Evidence
- AuditEvent
- historical Snapshot
- recorded Approval decision

Evidence, AuditEvent, and recorded Approval decision:

- must not rewrite history via in-place mutation
- must add a new record/event when a correction is required
- must keep the old record as history

In-place mutation of Evidence, AuditEvent, or recorded Approval is a failed invariant.

This invariant must later be enforced by store-level constraints, application tests, and persistence rules. How it is enforced, and which database feature is used, is not chosen here.

The primary paradigm must make both kinds natural: constrained updates for lifecycles, and insert-only new records for Evidence, AuditEvent, recorded Approval, and historical Snapshots. A strategy that can only do one of these poorly fails Stage 1 or pays a large Stage 2 tax.

### Flexible metadata

Flexible/schemaless metadata fields may be used only for secondary/extensible attributes.

They must not authoritatively embed:

- authorization state
- scope authority
- approval state
- lifecycle state
- promotion state
- budget authority
- finding acceptance state
- evidence identity/provenance
- core policy decisions

Those fields must be modeled as explicit first-class domain fields/records.

Flexible metadata must never become a second hidden domain schema.

---

## Consistency boundaries

These transitions must be representable as one authoritative decision, or as an explicit, auditable two-phase protocol with a single source of truth. Product-level isolation levels are not chosen here.

1. **AuthorizationSource + ScopeRule** — effective scope is Core-evaluated; stored rules and source state must not silently diverge.
2. **ResearchRun + Budget consumption** — remaining budget and run state must not disagree after an authorized execution.
3. **Experiment lifecycle** — execution states (EXECUTION_SUCCEEDED / FAILED / BLOCKED / CANCELLED / BUDGET_EXHAUSTED) must not be collapsed into Hypothesis outcomes.
4. **Transition A** — Observation and/or Artifact metadata created from a WorkerResult without Evidence promotion.
5. **Evidence admission (Transition B)** — Observation/Artifact exist first; Evidence is a separate admitted record.
6. **Candidate lifecycle** — only Candidate state is authoritative; Verification records are episodic proposals.
7. **Verification process records** — append/episodic; they do not commit Candidate state by themselves.
8. **Candidate VALIDATED → FindingProposal** — proposal cannot exist without VALIDATED.
9. **Human Review → Core Approval** — Approval is the decision record; FindingProposal APPROVED is the same event’s domain view, not a second authority.
10. **Approval → Finding creation** — Finding exists only after Core Approval APPROVE. If Approval is recorded and Finding insert fails, the System of Record must not present an approved proposal as an accepted Finding. Prefer one atomic decision that writes Approval + Finding together, or a recorded incomplete-promotion state that is retryable and auditable. Silent split-brain is forbidden.
11. **AuditEvent** — append-oriented; corrections are new events.
12. **Snapshot / ChangeEvent** — historical; ChangeEvent is derived fact only when the comparator is deterministic.

Partial failure of (10) is the sharpest test: transactional multi-record update where one decision touches Approval and Finding, or an explicit recovery record. This is why “one System of Record that can update multiple related records together” is a Stage 1 concern.

---

## Relational primary

### Strengths

- Natural fit for distinct, linked domain records and integrity constraints.
- Transactional consistency for authority transitions (Approval + Finding, run + budget, VALIDATED + FindingProposal).
- Lifecycle/state columns plus constraints can encode legal transitions without making every change an event.
- Provenance as explicit links (run, source, artifact reference, evidence set), not only nested blobs.
- Joins and indexing support historical Snapshot/ChangeEvent queries and audit reconstruction.
- Mature schema-migration culture at the paradigm level (not a product choice).
- Flexible metadata can exist as constrained structured fields plus limited schemaless payload for **secondary** attributes only, without switching the System of Record to document-primary. Authority, lifecycle, promotion, budget, approval, finding acceptance, evidence identity/provenance, and policy decisions stay first-class fields/records.
- Research Memory can read this store; it need not copy truth.

### Weaknesses

- Deep/recursive graph traversal (AssetRelation, attack-surface walks) can become awkward if it dominates the workload.
- Semantic retrieval is not native; that is a companion trigger, not a reason to abandon the SoR.
- Large analytics or event/snapshot volumes may later need companions.
- Poor modeling of sparse/evolving fields can make tables cumbersome; that is a modeling failure, not an automatic document-DB requirement.

### Project-specific fit

- Passes Stage 1 for this domain’s many distinct concepts and multi-record authority transitions.
- Graph-shaped AssetRelation can be stored as relation records in a relational SoR; graph-shaped domain ≠ graph-primary SoR.
- Does not, by itself, choose PostgreSQL, SQLite, or any other product.

### Risks

- Treating JSON/flexible columns as an unbounded second schema, or embedding authorization, lifecycle, approval, promotion, budget, or evidence identity in schemaless payload.
- Putting Research Memory or search indexes in the SoR as if they were truth.

---

## Document primary

### Strengths

- Flexible evolving records and natural aggregates (for example a Candidate document with nested notes).
- Easy local variation of metadata shape.
- Some implementations can transact; this evaluation does not claim “document stores cannot transact.”

### Weaknesses

- Authority transitions cross aggregates: Approval, FindingProposal, Candidate, Evidence, ResearchRun. Document-primary modeling pushes either huge documents or multi-document transactions that recreate relational integrity by hand.
- Provenance is relational (many-to-many Evidence ↔ Candidate, Artifact ↔ Observation). Nested copies duplicate truth or lose links.
- Invariant enforcement (VALIDATED before FindingProposal; Evidence required for Finding) is easier to weaken when documents are the unit of write.
- Duplication and divergent nested copies are a real paradigm risk, not a product insult.

### Project-specific fit

- Useful for some aggregates; weak as the *only* System of Record for this authority-heavy domain.
- Flexible metadata is a real need; it does not require document-primary SoR.

### Risks

- Candidate/Finding/Approval consistency becomes an application-level distributed transaction across documents.
- Research Memory projections drift from nested copies that cannot be rebuilt cleanly.

---

## Graph primary

### Strengths

- AssetRelation, provenance walks, attack-surface exploration, and relationship-heavy authorization questions map well to graph traversal.
- Explicit edges can make “inferred vs observed vs derived” visible as edge types.

### Weaknesses

- System-of-record lifecycle transactions, structured audit rows, and state-machine-heavy entities are not what graph-primary stores optimize as the *only* SoR.
- Schema/evolution, local simplicity, and operational overhead are typically worse for a single developer than a relational SoR plus later graph acceleration.
- Append-oriented Evidence/Audit and Approval→Finding atomicity are less natural as graph-only writes.

### Project-specific fit

- Strong as a *companion* if relationship traversal dominates.
- Not Stage 1–best as the sole System of Record. Graph-shaped queries can be answered from relational relation records until a trigger says otherwise.

### Risks

- Confusing traversal convenience with authoritative lifecycle semantics.
- Dual-writing graph + tables from day one without a single SoR.

---

## Event-sourced primary

### Strengths

- Append-only history, explicit transitions, temporal reconstruction, and strong audit narratives.

### Weaknesses

- Projections become the working model; debugging and event-schema evolution are expensive for one developer.
- Ad-hoc querying of “current Candidate state” depends on projections that can lag or drift.
- Event/model drift: forgotten events, poisoned replays, versioned payloads.
- Eventual consistency of views fights “Approval recorded iff Finding exists” unless the SoR *is* the event log *and* projections are strictly derived—which is a large operational bet.

### Project-specific fit

- **AuditEvent and immutable Evidence do not require event-sourcing the whole domain.** They require append/immutable *records* inside the SoR.
- Audit trail ≠ event sourcing. Research OS needs reconstructable audit and immutable Evidence, not a mandatory event log as the only truth.

### Risks

- Building Research Memory as a projection farm that is mistaken for truth.
- Single-developer burden of replay, upcasters, and “which projection is current.”

---

## Polyglot-from-start

Relational + graph + vector + object + event stores from day one.

### Strengths

- Each workload could use a specialized engine later.

### Weaknesses

- Synchronization, which store is truth, operational and local-dev burden, and migration cost are high before any measured trigger.
- Source-of-truth ambiguity is a Stage 1 hazard: companions start being treated as authoritative.
- Conflicts with preferred first-implementation simplicity and “do not introduce a distributed plane until topology requires it.”

### Project-specific fit

- Fails Stage 2 badly; risks failing Stage 1 via split-brain (search/graph/vector vs SoR).
- Not selected. Companions remain allowed *later*, when triggered.

### Risks

- Dual writes; Research Memory or vector index becoming a shadow database.

---

## Relational primary + optional companions later

### Strengths

- One Stage 1 System of Record for integrity, transactions, provenance links, lifecycles, and audit rows.
- Read models (including Research Memory) stay rebuildable.
- Companions can be added for graph acceleration, search, semantic retrieval, analytics, or artifact bytes without promoting them to truth.
- Avoids premature polyglot cost while not forbidding later stores.

### Weaknesses

- Until companions exist, some graph walks, full-text, or semantic queries may be slower or clumsier.
- Requires discipline: do not sneak a second SoR into a “cache,” and do not treat companion indexes as conflict winners.

### Project-specific fit

- Matches mandatory gates and single-developer first implementation.
- Matches “search/vector/graph may later exist as companion capabilities.”
- Artifact bytes remain a separate open decision; only Artifact metadata/reference is in this SoR.

### Risks

- Delaying a companion too long after a real trigger (traversal, search, byte volume).
- Overloading the relational SoR with blobs or search indexes that should have become companions.

---

## Comparison Matrix

Scores are 1 (worse project fit) to 5 (better project fit). Higher is always better. Stage 1 weighs more than Stage 2.

| Criterion | Rel. primary | Doc. primary | Graph primary | Event-sourced primary | Polyglot-from-start | Rel. + companions later | Why |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. domain integrity | 5 | 3 | 3 | 3 | 2 | 5 | Many distinct concepts need constrained records. Documents/graphs/events can, but integrity is easier to scatter. |
| 2. transactional consistency | 5 | 3 | 3 | 3 | 2 | 5 | Approval+Finding and run+budget need one SoR transaction (or explicit recovery). Polyglot splits writes. |
| 3. authority-transition correctness | 5 | 2 | 3 | 3 | 2 | 5 | Cross-entity promotions are the hard case. Document aggregates and multi-store writes fight this. |
| 4. provenance representation | 5 | 3 | 4 | 4 | 3 | 5 | Links as first-class records. Graph/events can represent provenance; documents tend to nest/copy. |
| 5. lifecycle/state-machine representation | 5 | 3 | 3 | 4 | 3 | 5 | Current state + legal transitions. Events encode transitions well but need projections for “now.” |
| 6. append-oriented history support | 4 | 3 | 3 | 5 | 4 | 4 | Event-sourced wins append-only. Relational can insert-only Evidence/Audit without event-sourcing everything. |
| 7. immutable Evidence/Audit semantics | 4 | 3 | 3 | 5 | 3 | 4 | Same: events excel at immutability; relational insert-only rows are enough for this domain. |
| 8. relationship modeling | 4 | 2 | 5 | 3 | 4 | 4 | Graph is strongest for edges. Relational relation tables are enough until traversal dominates. |
| 9. graph-like traversal capability | 3 | 2 | 5 | 3 | 4 | 4 | Graph primary / later companion. Relational-only is weaker if walks dominate; “later” raises this. |
| 10. historical/snapshot querying | 4 | 3 | 3 | 5 | 3 | 4 | Snapshots/ChangeEvents as records. Event replay can reconstruct; ad-hoc relational querying is simpler on a record SoR. |
| 11. flexible metadata support | 3 | 5 | 3 | 3 | 4 | 4 | Document-primary is most flexible. Relational+companions can add constrained flexible fields without changing SoR. |
| 12. schema evolution | 4 | 4 | 3 | 2 | 2 | 4 | Event schemas and multi-store schemas are the hardest to evolve. |
| 13. query expressiveness | 5 | 3 | 4 | 2 | 3 | 5 | Ad-hoc joins and filters over current + historical records. Event logs need projections first. |
| 14. indexing | 4 | 4 | 3 | 2 | 3 | 4 | Record stores index well. Event-primary indexes usually sit on projections. |
| 15. analytical querying | 4 | 3 | 3 | 2 | 4 | 4 | Analytics may later leave the SoR; starting polyglot is not required. |
| 16. single-developer simplicity | 5 | 4 | 2 | 2 | 1 | 5 | One SoR. Event-sourcing and polyglot are the heaviest. |
| 17. operational simplicity | 5 | 4 | 3 | 2 | 1 | 5 | One primary process/store class until a trigger. |
| 18. local development simplicity | 5 | 4 | 2 | 2 | 1 | 5 | One paradigm locally; companions optional. |
| 19. testability | 5 | 3 | 3 | 2 | 2 | 5 | Invariants and transitions testable against one SoR. Projections/multi-store tests explode. |
| 20. migration/evolution safety | 4 | 3 | 3 | 2 | 2 | 4 | One schema story. Event upcasters and multi-store migrations are costlier. |
| 21. future companion-store interoperability | 4 | 3 | 3 | 3 | 5 | 5 | Polyglot-from-start “has” companions already but without a clean SoR. Rel+later is the intended path. |
| 22. avoidance of vendor lock-in | 4 | 3 | 3 | 3 | 2 | 4 | Paradigm ≠ product. More stores → more product coupling. |
| 23. avoidance of premature polyglot cost | 5 | 4 | 3 | 3 | 1 | 5 | Inverse of starting with many stores. Higher = less premature cost. |
| 24. truth independent of Research Memory | 5 | 3 | 3 | 2 | 2 | 5 | Memory must remain a read model. Event/polyglot/document copies easily become shadow truth. |

No extra paradigm was added.

---

## Decision

**ACCEPT WITH CONSTRAINTS**

**Primary data strategy:** Relational primary System of Record, with rebuildable read models, and optional companion stores later.

This passes Stage 1: distinct domain records, multi-record authority transitions (especially Approval → Finding), provenance links, mixed mutable lifecycles and append-oriented Evidence/Audit, without treating Research Memory as truth.

It wins Stage 2 for a single developer: one authoritative paradigm, local/operational simplicity, query ergonomics, and a clear extension path.

It is not selected because “relational means Postgres,” nor because graph/document/events are incapable. Document-primary and graph-primary fail as *sole* SoR on authority-transition and lifecycle/audit shape. Event-sourced primary overfits audit/Evidence immutability. Polyglot-from-start creates source-of-truth ambiguity before any trigger.

The decision is ACCEPT WITH CONSTRAINTS because graph traversal, semantic retrieval, full-text, analytics, and large artifact bytes are real possible later workloads, and because flexible metadata must not dissolve relational invariants.

---

## Constraints

- **System of Record:** relational-paradigm store of authoritative domain records. Not a product name.
- **Authoritative data:** the domain concepts listed above, including WorkerResult as untrusted durable capture and Artifact *metadata/reference*, not automatically artifact bytes.
- **Read model:** rebuildable projection (Research Memory, UI, search views). Not a second truth.
- **Companion store:** may not gain authority. Every derived companion index/read model must be rebuildable from the System of Record (search, semantic/vector, graph, dashboard, Research Memory, temporal/materialized views). On drift, the companion is corrected or rebuilt; the SoR is not rewritten to match it. The companion is never the authoritative conflict winner. Artifact bytes may be exempt from rebuild-from-SoR because their topology is a separate decision; Artifact metadata/reference/provenance stay in the SoR.
- **Evidence/Audit/Approval immutability:** Evidence, AuditEvent, and recorded Approval decision must not rewrite history in place. Corrections are new records; old records remain. In-place mutation of Evidence/Audit/recorded Approval is a failed invariant. Enforcement mechanism (store constraints, tests, persistence rules) is not chosen here.
- **Flexible metadata:** secondary/extensible attributes only. Must not authoritatively hold authorization, scope, approval, lifecycle, promotion, budget, finding acceptance, evidence identity/provenance, or core policy decisions. Those are first-class domain fields/records. Flexible metadata is not a hidden second schema.
- **Cross-store consistency:** if a companion exists, the System of Record is source of truth; companions are derived. No dual-write as two SoRs.
- **Artifact bytes:** out of scope for this decision (open: topology/product).
- **Graph/vector/search:** out of scope as products; allowed later as non-authoritative companions when revisit triggers fire.
- Do not map one domain concept to one table as a requirement; preserve distinct records and links.
- Do not put Research Memory, vector indexes, or search indexes in the role of System of Record.
- FindingProposal APPROVED remains the domain view of Core Approval, not a separate store of authority.

---

## Rejected alternatives

- **Document primary:** Flexible aggregates help evolving metadata, but Candidate/Finding/Approval/Evidence provenance crosses aggregates. Integrity and multi-record authority would be reimplemented by hand; duplication risk is high.
- **Graph primary:** Strong for AssetRelation and provenance walks. Weak as the only SoR for state machines, structured audit, Approval→Finding atomicity, and single-developer operations. Graph-shaped domain ≠ graph-primary SoR.
- **Event-sourced primary:** Strong append/audit story. AuditEvent + immutable Evidence do **not** require event-sourcing the whole domain. Projection, replay, and query cost fail Stage 2; views can drift from authority.
- **Polyglot-from-start:** Specialized engines help later workloads. Starting with several stores splits truth, sync, and local operations before a measured need.
- **Relational-only forever (no companions allowed):** Not chosen as a hard ban. Companions remain optional later. The selected strategy is relational primary **plus** companions when triggered—not a freeze on all future stores.

---

## Revisit Triggers

Reopen or extend (usually by adding a companion, not by replacing the SoR) with measured evidence in these categories. No numeric thresholds invented.

- relationship traversal dominates workload
- semantic retrieval becomes a core retrieval path
- full-text search demand exceeds primary-store capability
- analytics volume becomes operationally expensive on the SoR
- event volume or snapshot volume becomes a specialized workload
- primary-store query bottlenecks despite indexing/modeling
- write throughput limits authority transitions
- storage growth (especially bytes vs metadata)
- read-model rebuild cost
- cross-program analysis that the SoR cannot answer without harming operational simplicity
- schema migration pain that a different *product* might ease without changing paradigm
- operational complexity of the primary store itself

Adding a companion under these triggers does not by itself reverse relational primary as System of Record.

---

## Open questions after this decision

Still unresolved; not answered here:

- specific database product
- artifact byte-storage topology/product
- semantic/vector strategy
- search strategy
- graph companion strategy
- analytics strategy
- retention policy
- backup/restore strategy
- schema migration tooling
- data encryption implementation

---

## Confidence

**MEDIUM**

Relational primary plus later companions is the only candidate that clearly passes Stage 1 for this authority/provenance domain and Stage 2 for one developer, without forbidding graph/search/vector/bytes later.

Confidence is not HIGH because graph-shaped traversal and flexible metadata are real, product choice is still open, and a badly modeled relational SoR could recreate document-shaped invariant loss inside “flexible” columns. Revisit triggers exist so companions can be added without pretending the SoR must never change shape.
