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

---

# Decision 003 — Specific Primary Database Product

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 002 — Primary Data Strategy (relational primary System of Record; rebuildable read models; optional companions later)

This decision selects the **concrete primary database product** for that System of Record.

It does **not** select:

- ORM / data-access library
- schema migration tooling
- connection pooling
- cache / ephemeral store
- vector, graph, or search products
- artifact **byte** storage product
- CDC / event-projection product
- orchestrator
- replication / HA topology
- backup/restore **implementation**
- encryption implementation

Those remain later decisions.

Python is the locked first-implementation language (Decision 001). The database product must expose **language-neutral client protocols/interfaces**. A mature Python client ecosystem exists for that primary language. This database decision is **not** Python-locked. No driver or client library is selected here. Contracts remain language-neutral.

---

## Decision

**ACCEPT WITH CONSTRAINTS**

The primary System of Record for Research OS v1 is **PostgreSQL**.

PostgreSQL is the durable store for Program, AuthorizationSource, ScopeRule, ResearchRun, Budget, Asset, AssetRelation, Observation, Hypothesis, Experiment, WorkerResult metadata/reference, Artifact metadata/reference, Evidence, Candidate, Verification records, FindingProposal, Finding, Approval, Snapshot, ChangeEvent, and AuditEvent.

It is **not** Research Memory.  
It is **not** the default artifact byte store.  
It is **not** a graph, search, or vector product.  
JSONB / document-shaped columns, if used at all, are **secondary/extensible attributes only**. They do not replace first-class fields for authorization, scope, lifecycle, promotion, budget, approval, finding acceptance, evidence identity/provenance, or core policy state (Decision 002).

PostgreSQL is **not** selected because other candidates are incapable of being a relational System of Record. Multiple products can satisfy the mandatory Stage 1 gates. PostgreSQL is selected because it offers the strongest **combined project fit** after those gates are satisfied.

---

## Why this decision exists

Decision 002 locked the **paradigm**: relational primary SoR.

This decision locks the **product** that must actually:

- commit Approval + Finding together, or neither
- commit Budget reservation/decrement with ResearchRun/execution start, or neither
- keep Evidence, AuditEvent, and recorded Approval from being rewritten in place
- hold first-class authority and lifecycle fields under constraints
- feed later rebuildable companions without becoming those companions

Choosing “relational” without a product would leave the first implementation without a durable store. Choosing a product because it is popular, distributed, embedded, or JSON-capable would violate the domain.

---

## Candidates considered

Serious relational candidates only:

1. **PostgreSQL**
2. **MySQL / MariaDB** (related family; not treated as identical products)
3. **SQLite**
4. **CockroachDB**

No additional candidate was added. Document databases, wide-column stores, and “Postgres-compatible” cloud forks were not evaluated as separate products; they would either reopen Decision 002 or add vendor lock-in without changing the relational question.

---

## Project facts that drive product choice

- Authority and lifecycle fields are first-class.
- Flexible metadata is secondary only.
- Evidence / AuditEvent / recorded Approval must not mutate in place.
- Approval → Finding and ResearchRun + Budget consumption must be consistent.
- Transition A and Transition B stay separate.
- Provenance is relationship-dense.
- AssetRelation may be graph-shaped; a graph companion remains optional later (Decision 002). Recursive SQL does **not** make a graph store unnecessary, and does **not** make recursive SQL a domain dependency.
- Historical / snapshot querying matters.
- Companions later are rebuildable from this SoR.
- First implementation is one developer.
- Local development matters.
- Production topology is **not** chosen.
- Current context is Windows + Cursor; Kali/WSL is the initial tool-integration environment. Windows is **not** the production architecture driver.
- Database product must remain replaceable in principle; Core/Research must not embed product-specific types or SQL dialects in domain contracts.

---

## Stage 1 — Mandatory gates

A product that fails a Stage 1 gate is **not** a viable **production** System of Record candidate.

Multiple candidates can satisfy these mandatory gates.

PostgreSQL, MySQL/MariaDB, and CockroachDB can all be viable production relational systems of record **in principle**.

SQLite may satisfy durability and transactional correctness in an **embedded/local** role, but is weaker for the expected shared/networked multi-process production control-plane role.

PostgreSQL is selected primarily because it gives the best combined project fit **after** the mandatory gates are satisfied — not because it is the only product that can pass them.

| Gate | Meaning for this project |
|---|---|
| Transactional correctness | Multi-row, multi-table commits with rollback on partial failure |
| Authority consistency | AuthorizationSource / ScopeRule / ResearchRun / Budget can be updated without split-brain vs companions |
| Durable SoR suitability | Survives process restart as the source of truth for control-plane records |
| Provenance / audit support | Append-oriented Evidence / AuditEvent / Approval history can be stored and queried |
| Integrity constraints | PK / FK / UNIQUE / NOT NULL / CHECK (or equivalent) on first-class fields |
| Linux production viability | Can run as a Linux service later without rewriting the SoR |
| Language-neutral client interoperability | Product exposes language-neutral client protocols/interfaces; it is not a Python library or Python-locked store |

Python client maturity is a **Stage 2** concern, not a Stage 1 gate. No driver is selected here.

### Gate results

| Product | Stage 1 | Note |
|---|---|---|
| **PostgreSQL** | **Pass** | Viable production relational SoR: transactions, constraints, durable shared server, Linux service, language-neutral clients |
| **MySQL 8+ / recent MariaDB** | **Pass** | Viable production relational SoR family. InnoDB transactions and foreign keys are real. Integrity **can** be preserved. Constraint/query **ergonomics** are Stage 2, not a Stage 1 failure |
| **SQLite** | **Pass as embedded/local; not the production SoR role** | Durable ACID in-process. Weaker for shared/networked multi-process production control plane, remote workers, and HA/replication as a service. Not eliminated for lack of correctness |
| **CockroachDB** | **Pass** | Serious production candidate at Stage 1. Distributed operational cost, latency, and single-developer burden are Stage 2, not a correctness failure |

Stage 1 does **not** pick the winner. It only establishes which products are capable enough to compare.

---

## Consistency boundaries (conceptual)

These are **not** schema or API designs. They test whether the product’s transactional model can hold the domain.

| Operation | What must not happen | PostgreSQL | MySQL / MariaDB | SQLite | CockroachDB |
|---|---|---|---|---|---|
| 1. Scope / Authorization updates | Partial ScopeRule write vs Program/AuthorizationSource | Single transaction | Single InnoDB transaction | Local transaction; poor concurrent writers | Distributed transaction |
| 2. ResearchRun creation | Run row without required authorization snapshot/reference | Same | Same | Same locally | Same, higher latency |
| 3. Budget decrement / reservation | Budget changed but execution never started, or execution started without budget | Same atomic unit | Same | Same locally; lock contention under workers | Same; clock/latency caveats |
| 4. Experiment lifecycle | Status change without required fields | Constraints + txn | Constraints + txn (ergonomics differ) | Constraints + txn | Constraints + txn |
| 5. Transition A Observation / Artifact metadata | Interpretation or Evidence in the same write | App + txn; product does not invent Transition B | Same | Same | Same |
| 6. Evidence admission | Evidence without Observation/Artifact basis, or in-place rewrite of prior Evidence | Insert + FK + no UPDATE policy | Insert + FK | Insert + FK if enabled | Insert + FK |
| 7. Candidate lifecycle | Illegal status jump | CHECK / constrained status | ENUM/CHECK (MySQL CHECK is newer) | CHECK | CHECK |
| 8. Candidate VALIDATED → FindingProposal | Proposal without VALIDATED Candidate | Txn + FK | Txn + FK | Txn + FK | Txn + FK |
| 9. Human Review → Approval | Approval without review outcome | Txn | Txn | Txn | Txn |
| 10. Approval + Finding creation | **Approval recorded, Finding missing** (or reverse) | **One transaction** | **One transaction** | **One local transaction** | **One transaction** (distributed cost) |
| 11. Append-only AuditEvent | In-place rewrite | Insert-only grants/triggers possible; not automatic | Same idea | Same idea; enforcement is process-local | Same idea |
| 12. Immutable Evidence history | UPDATE/DELETE of admitted Evidence | Preventable by privilege + modeling | Preventable by privilege + modeling | Preventable locally | Preventable |
| 13. Snapshot / ChangeEvent | History rewritten | Append tables | Append tables | Append tables | Append tables |

**Partial-state examples:**

- Approval committed, Finding not created → all four **can** prevent this **if** the application uses one transaction. PostgreSQL and InnoDB MySQL/MariaDB are the realistic **shared-server** answers. SQLite can atomically commit locally but not as a multi-process networked SoR. CockroachDB can atomically commit across nodes at operational and latency cost this project does not have yet.
- Budget decremented, execution never started → same: product must offer multi-statement transactions; **application** must put both writes in one transaction. No product auto-implements Budget policy.

Immutability of Evidence, AuditEvent, and recorded Approval is a **domain requirement**, not a built-in feature of any candidate:

- in-place history rewrite is forbidden
- correction is a **new record**, not an overwrite
- store-level enforcement is a later decision
- tests for that enforcement are later

Exact grants, triggers, row-level policies, or application-only checks are **not** chosen here.

---

## Immutability support (capability, not implementation)

Required: Evidence, AuditEvent, and recorded Approval history are not rewritten in place.

| Capability | PostgreSQL | MySQL / MariaDB | SQLite | CockroachDB |
|---|---|---|---|---|
| Append-oriented tables | Yes | Yes | Yes | Yes |
| Column constraints on first-class fields | Strong | Adequate (MySQL 8 CHECK; MariaDB differs) | Strong if FKs enabled | Strong |
| Privilege to deny UPDATE/DELETE | Mature GRANT/REVOKE | Mature | File + limited user model | Role-based |
| Transactional insert of Approval+Finding+AuditEvent | Yes | Yes (InnoDB) | Yes locally | Yes, distributed |

No candidate provides domain immutability by existing. All production passers can support append-oriented modeling plus privileges. Exact store-level enforcement and tests are later. That is **capability**, not a selected implementation.

---

## Flexible metadata

Secondary attributes may need a flexible column.

| Concern | PostgreSQL | MySQL / MariaDB | SQLite | CockroachDB |
|---|---|---|---|---|
| Flexible payload | JSONB | JSON (semantics differ; MariaDB JSON is not MySQL JSON) | JSON1 | JSON |
| Indexing metadata | Mature (without requiring a named extension in this decision) | Possible; historically less ergonomic | Weaker | Possible |
| Schema discipline still required | Yes — JSONB does **not** authorize document-shaped SoR | Yes | Yes | Yes |
| Abuse risk | **High if used for authority fields** | High | High | High |

**JSON support does not mean this project may treat PostgreSQL as a document database.** Flexible metadata is **secondary only**. Authorization, scope, lifecycle, promotion, budget, approval, finding acceptance, evidence identity/provenance, and core policy state remain first-class columns. This decision does **not** require JSONB, and does **not** require any extension.

---

## Future read models (ergonomics only)

Later projections may include Research Memory, search, graph, semantic/vector, dashboards, temporal views.

PostgreSQL is a conventional **source** for rebuild/export: stable rows, SQL snapshots, WAL-based tooling later. That does **not** select CDC, Debezium, LISTEN/NOTIFY, or logical replication as products.

MySQL/MariaDB binlog is also a known projection source. SQLite is a weak CDC/source-of-projections story for a multi-service control plane. CockroachDB changefeeds exist; they would couple operations to a distributed product this project does not need.

No companion product is selected.

---

## Local development vs production roles

Current environment: Windows + Cursor; Kali/WSL workers later. Production topology unselected.

| Role | PostgreSQL | MySQL / MariaDB | SQLite | CockroachDB |
|---|---|---|---|---|
| Windows local run | Installer, WSL, or container — workable, not zero-service | Similar | **Zero-service** | Heavy (cluster) |
| Linux production | Native, mature | Native, mature | File; not the shared server SoR | Native, heavier |
| Test isolation | Separate database/schema per suite (tooling later) | Same | **Best** file-per-test | Awkward locally |

Windows support is **not** the primary driver. This PostgreSQL selection is **not** Windows-specific, **not** Kali-specific, and **not** Python-specific. Local PostgreSQL is an operational advantage for development; Windows + Cursor and Kali/WSL do **not** determine production architecture.

SQLite wins local friction and is the strongest **local/embedded** alternative. It is not selected as the production SoR. Using SQLite locally and PostgreSQL in production would create **two dialects** and a false sense that production behavior was tested. This decision therefore selects **one** primary product for the SoR, including local development against that product. SQLite as an optional test double remains an **open question**, not a selected dual-SoR strategy.

---

## Candidate evaluations

### PostgreSQL

**Fit:** Strongest **Stage 2** combined fit among Stage 1 production passers, for a provenance-heavy relational SoR with one developer and later Linux production.

It is not selected because MySQL/MariaDB or CockroachDB cannot be production systems of record. Those products pass Stage 1.

It is selected because this domain has:

- many first-class relational records
- authority-sensitive multi-record transitions
- provenance-heavy joins
- lifecycle/state modeling
- historical queries
- recursive relationship queries
- flexible secondary metadata needs
- single-developer operational constraints

and PostgreSQL offers the strongest combined fit across those needs without forcing a distributed or polyglot architecture in v1.

**Strengths that matter here (not popularity):**

- Transactional semantics for Approval+Finding and Budget+Run
- Integrity/constraint **ergonomics** for first-class authority/lifecycle fields
- Relational + recursive query power for provenance and AssetRelation **without** making a graph store forbidden or required
- JSON-like payloads available for **secondary** metadata only
- Mature indexing, ad-hoc SQL, backup/restore, observability
- Language-neutral client protocols/interfaces, with a mature Python client ecosystem for the locked primary language — the product is not a Python database
- Runnable locally and on Linux; that local runnability is an advantage, not a Windows/Kali architecture decision. Production HA remains a later topology decision

**Risks (accepted, constrained):**

- More operational surface than SQLite (a process/service vs a file)
- **Extension temptation** and accidental lock-in if Core/Research absorb product-specific features
- JSONB **misuse** recreating a document SoR
- No automatic horizontal distribution — acceptable because scale is not a current requirement
- Schema discipline is still the application’s job

This decision does **not** require, name, or depend on specific extensions.

### MySQL / MariaDB

**Fit:** Strongest **production** alternative. Viable Stage 1 production relational SoR family. Not selected because Stage 2 project fit is weaker than PostgreSQL, not because the family cannot preserve integrity.

**Not identical products.** MySQL 8 and MariaDB have diverged (JSON type, sequences, optimizer, system versioning, privilege details). Hosting familiarity and replication lore are real. For Research OS they are one **family of alternatives**, not two independent winners.

**Why it is strong:**

- mature relational engine family
- production-proven
- replication and hosting ecosystem
- transactional correctness (InnoDB)
- broad tooling

**Why it is not as good a fit as PostgreSQL for this project right now:**

- provenance-heavy / constraint-heavy domain: query and integrity **ergonomics** are less attractive than PostgreSQL’s
- complex relational / recursive query ergonomics are a weaker project fit
- choosing it provides **no clear simplicity advantage** over PostgreSQL for this project
- MySQL vs MariaDB JSON and dialect split would be extra lock-in inside a second-choice family

MySQL/MariaDB are **not** “bad.” They are **not** unable to preserve integrity. InnoDB can commit Approval+Finding. This domain is more than generic OLTP hosting familiarity, so Stage 2 prefers PostgreSQL at similar operational cost.

### SQLite

**Fit:** Strongest **local/embedded** alternative. Excellent local development, embedded ACID, fast tests, zero-service setup. Not selected as the **primary production SoR**.

**Why it is strong:**

- excellent local development
- embedded ACID
- fast tests
- zero-service setup
- recursive CTEs and language-neutral clients
- tiny operational surface

**Why it is not the production SoR:**

- shared remote control-plane deployment
- multiple writers / processes
- networked service expectations
- HA / replication topology
- future remote workers

Writer serialization is a **project-fit** mismatch for a shared control plane, not evidence that SQLite is a toy or that its transactions are fake.

**Role split:** SQLite is **not** appropriate as the primary **production** System of Record. It is **more appropriate as a local test/dev / embedded capability** (and possibly a later optional test double). That capability is **not** selected here, to avoid a dual-database strategy in v1.

### CockroachDB

**Fit:** Serious Stage 1 **production** candidate. Correct **class** (distributed relational) for a later scale/HA world. Wrong **time** for v1.

**Strengths:** horizontal scale, resilience, familiar SQL, serializable-by-default story. Distributed does **not** automatically score higher, and does **not** fail correctness.

**Why not v1 (Stage 2):**

- distributed-system operational cost
- higher conceptual and operational complexity
- latency and distributed transaction semantics
- single-developer burden (local cluster)
- no current horizontal-scale requirement
- compatibility is “Postgres-like,” not a promise that PostgreSQL features and ops transfer

CockroachDB is **not** rejected because it is distributed, and **not** rejected because it fails correctness. It is not selected because this project does not yet need that operational class.

---

## Comparison matrix

Scores: **5 = better project fit**, **1 = worse project fit**. High is always better. Totals are **not** the decision.

**PG** = PostgreSQL. **MY** = MySQL 8 / MariaDB family (score reflects the weaker of the two where they diverge). **LT** = SQLite. **CR** = CockroachDB.

| # | Criterion | PG | MY | LT | CR | Short rationale |
|---|---|---:|---:|---:|---:|---|
| 1 | Transactional correctness | 5 | 5 | 4 | 5 | All four are ACID in their intended role. SQLite 4 is **shared/networked SoR fit**, not “fake transactions.” Production servers are Stage 1 capable. |
| 2 | Integrity constraints | 5 | 4 | 4 | 4 | All can enforce PK/FK/CHECK (or equivalent). PG scores higher on **ergonomics** for this constraint-heavy domain, not exclusive capability. MySQL CHECK arrived later; that is Stage 2. |
| 3 | Multi-record atomic transitions | 5 | 4 | 4 | 4 | All can COMMIT Approval+Finding; PG is the default shared-server choice. SQLite not shared. CR costlier. |
| 4 | Concurrency behavior | 4 | 4 | 2 | 4 | PG/MySQL MVCC for concurrent writers. SQLite writer lock. CR concurrent but distributed. |
| 5 | Explicit lifecycle/state modeling | 5 | 4 | 4 | 4 | All can store status columns; PG constraints/enums/CHECK are the strongest habit fit. |
| 6 | Append-oriented records | 4 | 4 | 4 | 4 | All support insert-only tables; none are ledgers by default. |
| 7 | Immutable-record enforcement potential | 4 | 4 | 3 | 4 | All can model append-only tables. PG/MySQL/CR have conventional shared-server privilege models. SQLite enforcement is process-local. Exact mechanism not chosen. |
| 8 | Provenance/query support | 5 | 4 | 4 | 4 | PG SQL/CTE/window depth. Others adequate. |
| 9 | Relationship/query expressiveness | 5 | 4 | 4 | 4 | Same pattern. Recursive SQL ≠ graph product. |
| 10 | Recursive/graph-like traversal | 4 | 3 | 4 | 3 | PG/SQLite recursive CTEs are capable; not a graph DB. MySQL recursive CTE exists, less central. CR Postgres-like with limits. |
| 11 | Historical/snapshot query ergonomics | 4 | 3 | 3 | 3 | History tables + SQL: PG nicest. No product selected as a temporal database. |
| 12 | Structured + flexible metadata | 4 | 3 | 3 | 4 | JSONB is capable **and** easy to abuse. MySQL/MariaDB JSON split is a trap. Score is capability with discipline, not a document mandate. |
| 13 | Schema evolution | 4 | 3 | 2 | 4 | PG ALTER is mature. SQLite ALTER is limited. MySQL online DDL has caveats. |
| 14 | Migration safety | 4 | 3 | 2 | 3 | Transactional DDL habits favor PG. Tooling is a later decision. SQLite migrations are awkward. CR schema changes are a different ops model. |
| 15 | Indexing | 5 | 4 | 3 | 4 | PG strongest general + JSON-secondary indexing **if** used. Not an extension decision. |
| 16 | Ad-hoc querying | 5 | 4 | 4 | 4 | SQL everywhere; PG/ecosystem nicest for provenance exploration. |
| 17 | Analytical query capability | 4 | 3 | 2 | 3 | SoR is not a warehouse. PG can feed later analytics; SQLite least. |
| 18 | Local development simplicity | 3 | 3 | 5 | 1 | SQLite wins. PG/MySQL need a service. CR cluster is worst. |
| 19 | Windows development support | 3 | 4 | 5 | 2 | SQLite trivial. MySQL Windows installs are common. PG via WSL/installer/container. Not the decision driver. |
| 20 | Linux deployment support | 5 | 5 | 3 | 4 | PG/MySQL native servers. SQLite is a file, not the production SoR shape. CR runs on Linux at higher cost. |
| 21 | Python ecosystem maturity | 5 | 5 | 5 | 4 | Stage 2. Mature Python **clients** exist; none of these products is Python-locked. No driver is selected. CR uses PG-wire with compatibility gaps. |
| 22 | Backup/restore maturity | 5 | 4 | 3 | 3 | PG dump/basebackup lore is strongest for a future Linux SoR. SQLite = file copy + WAL care. |
| 23 | Observability/tooling maturity | 5 | 4 | 2 | 3 | PG/MySQL as servers. SQLite has little server ops story. |
| 24 | Operational simplicity | 3 | 3 | 5 | 1 | SQLite simplest. PG/MySQL similar single-node cost. CR heaviest. |
| 25 | Single-developer suitability | 4 | 4 | 5 | 2 | SQLite easiest locally; not the production SoR role. One PG or MySQL instance is acceptable. CR is a heavier ops class. |
| 26 | Future scale headroom | 4 | 4 | 1 | 5 | CR wins scale we do not have. SQLite has none. PG vertical + later replicas. |
| 27 | Replication / HA options | 4 | 4 | 1 | 5 | Options exist for PG/MySQL/CR; **none selected**. SQLite has no HA story. |
| 28 | Companion-store interoperability | 4 | 4 | 2 | 4 | SQL dump/replica/CDC-later. SQLite is a poor projection source for a control plane. CDC not chosen. |
| 29 | Portability / vendor lock-in risk | 4 | 4 | 5 | 3 | SQL portability if we avoid product features. CR and PG extensions are lock-in paths. SQLite dialect is small but production-wrong. |
| 30 | Maturity/stability | 5 | 5 | 5 | 4 | Three are decades-old production classes. CR is mature enough as distributed SQL; heavier than this v1 needs. |

**Reading the matrix:** Scores are **project fit**, not exclusive capability. PostgreSQL, MySQL/MariaDB, and CockroachDB can all pass Stage 1 as production relational SoRs. SQLite scores high on local/embedded columns and lower on shared/networked production-role columns. CockroachDB scores high on scale/HA this project does not need. MySQL/MariaDB tracks PostgreSQL as a production relational server and trails on Stage 2 ergonomics for this provenance/constraint-heavy domain. PostgreSQL wins on **combined Stage 2 fit**, not by being the only gate passer.

---

## Stage 2 — Differentiators (among Stage 1 production passers)

Stage 1 established capability. Stage 2 chooses the product.

Compared as production SoRs: PostgreSQL vs MySQL/MariaDB vs CockroachDB.

SQLite is the strongest **local/embedded** alternative and is scored in the matrix; it is not the production SoR role being chosen here.

| Differentiator | Winner | Why |
|---|---|---|
| Integrity / constraint ergonomics | PostgreSQL | Strongest habit fit for first-class authority/lifecycle fields. MySQL/MariaDB can enforce integrity; ergonomics are less attractive for this domain |
| Complex relational query ergonomics | PostgreSQL | Provenance joins, window functions, ad-hoc SQL depth |
| Provenance-heavy schema fit | PostgreSQL | Many distinct related records plus historical/append tables |
| Recursive relationship querying | PostgreSQL | Recursive CTEs are capable here; they do not make a graph companion forbidden or required, and are not a domain dependency |
| Flexible secondary metadata support | PostgreSQL | JSON-like payloads exist for **secondary** attributes only. JSON does not authorize a document SoR. MySQL vs MariaDB JSON divergence is extra risk |
| Migration maturity | PostgreSQL | Mature ALTER habits. Tooling is a later decision. SQLite ALTER is limited (embedded role) |
| Single-developer operations | PostgreSQL ≈ MySQL; not CR | One instance is enough. CR adds distributed ops with no current scale requirement. SQLite is simpler locally but is not this role |
| Local development | PostgreSQL among production servers; SQLite if the job were embedded | Local PG is an advantage, not a Windows/Kali/Python architecture. Dual SQLite+PG dialects are avoided in v1 |
| Python interoperability | PostgreSQL ≈ MySQL ≈ SQLite | Mature Python **clients** exist. Product choice is not Python-locked. No driver selected. CR is PG-wire-like with gaps |
| Future companion-store integration | PostgreSQL ≈ MySQL | Conventional SQL source for later rebuildable projections. CDC not chosen. SQLite is a weaker projection source for a control plane |
| Operational maturity | PostgreSQL ≈ MySQL | Both are production-proven single-node classes. CR is mature as distributed SQL and heavier than this v1 needs |

PostgreSQL wins Stage 2 as the strongest **combined** fit. MySQL/MariaDB remains the strongest production alternative. CockroachDB remains a later-scale production class, not a v1 need.

---

## Constraints (accepted with the product)

1. **Authoritative SoR role.** PostgreSQL holds first-class domain records and metadata/references. Companions never win conflicts (Decision 002).
2. **Flexible metadata bound.** JSON/JSONB (or equivalent) only for secondary/extensible attributes. Flexible fields **must not** replace first-class columns for authorization, scope, lifecycle, promotion, budget, approval, finding acceptance, evidence identity/provenance, or core policy state. JSON support is **not** permission to use a document model.
3. **Immutability requirement.** Evidence, AuditEvent, and recorded Approval history must not be rewritten in place. Correction is a **new record**. Store-level enforcement and tests are later decisions; exact mechanism is not chosen here.
4. **Transaction boundaries.** Approval + Finding (+ related AuditEvent) commit together or not at all. Budget reservation/decrement + the execution start they authorize commit together or not at all. Transition A and Transition B remain separate transactions/workflows, not separate databases.
5. **Companion-store authority prohibition.** Research Memory, search, graph, vector, cache, and artifact **bytes** are not this product’s job by default.
6. **No product-specific domain logic in Core/Research.** Domain contracts stay language- and vendor-neutral. PostgreSQL types, SQL dialect, and extensions must not leak into Core/Research as the domain model.
7. **Product features are not domain dependencies.** Recursive queries, JSONB, LISTEN/NOTIFY, advisory locks, inheritance, or any extension may be used later in **Data** only if a future decision allows them. They are not part of this accept.
8. **Replaceability.** A future move off PostgreSQL must remain theoretically possible: portable schema concepts, no Core/Research `VARCHAR`/`JSONB`/OID leakage into contracts.

Artifact **bytes** remain a later storage decision. WorkerResult/Artifact **metadata and references** stay in PostgreSQL.

---

## Strongest alternatives (not selected)

These are capable products in their roles. They are not selected as the v1 primary production SoR.

### Strongest production alternative — MySQL / MariaDB

Not selected as the primary product. Remains the leading **production** alternative if PostgreSQL operational or ecosystem facts change.

**Why it is strong:** mature relational engine family; production-proven; replication/hosting ecosystem; transactional correctness; broad tooling.

**Why it is not as good a fit as PostgreSQL right now:** provenance-heavy / constraint-heavy query and integrity **ergonomics** are less attractive; complex relational/recursive query ergonomics are a weaker project fit; choosing it provides no clear simplicity advantage over PostgreSQL for this project.

Not described as “bad.” Not described as unable to preserve integrity.

### Strongest local/embedded alternative — SQLite

Not selected as the primary **production** System of Record. Remains the leading **local/embedded** alternative (and an open question as a possible later test double).

**Why it is strong:** excellent local development; embedded ACID; fast tests; zero-service setup.

**Why it is not the production SoR:** shared remote control-plane deployment; multiple writers/processes; networked service expectations; HA/replication topology; future remote workers.

Not described as a toy. Not described as lacking real transactions.

### CockroachDB — not selected for v1

A serious Stage 1 production candidate. Not selected because of distributed-system operational cost, higher conceptual/operational complexity, latency/distributed transaction semantics, single-developer burden, and no current horizontal-scale requirement.

Not rejected because distributed systems “fail correctness.” Not rejected merely “because distributed.”

---

## Revisit triggers

Revisit this product (not automatically switch) if:

- write contention on the SoR becomes a measured bottleneck
- sustained concurrent control-plane load exceeds a single-node PostgreSQL comfort zone **as observed**
- horizontal scale is a **requirement**, not a preference
- HA / failover is a **requirement** (then topology, not necessarily a new product)
- cross-region is a **requirement**
- storage growth of metadata (not artifact bytes) stresses backup/restore
- query latency on provenance/history becomes user-visible
- analytical workload grows enough to need a replica or warehouse **companion**
- backup/restore or migration **pain** is operational, not theoretical
- operational burden of PostgreSQL exceeds the benefit vs a simpler store **and** production SoR needs have actually shrunk (unlikely)
- the primary DB is the bottleneck after indexing/schema work
- distributed worker topology requires a different consistency/deployment story

No numeric thresholds. Companions (Decision 002) remain the first response to graph/search/vector/analytics pressure, not an automatic CockroachDB migration.

---

## Open questions after this decision

Intentionally unanswered:

- ORM / data-access strategy
- schema migration tooling
- connection pooling strategy
- backup/restore implementation
- replication / HA topology
- encryption implementation
- artifact byte storage product
- cache / ephemeral store
- graph / search / vector companions
- CDC / event projection mechanism
- whether tests may use SQLite as a double
- whether JSONB is used at all, and how it is indexed
- exact immutability enforcement (grants vs triggers vs application-only)

---

## Confidence

**MEDIUM**

PostgreSQL is selected because it offers the strongest combined Stage 2 fit for this domain after multiple products pass Stage 1. MySQL/MariaDB remains a viable production SoR family. CockroachDB remains a viable distributed production class without a current scale need. SQLite remains a strong local/embedded store, not the production SoR.

Confidence is not HIGH because production topology, HA, backup implementation, and schema/JSONB discipline are still unchosen, and a poorly constrained PostgreSQL schema could still bury authority in JSON. Revisit triggers exist so the product can change if load or topology actually appears.

---

# Decision 004 — Workflow / Orchestration Strategy

**Status:** ACCEPT WITH CONSTRAINTS (strategy) / DEFER (product)  
**Date:** 2026-08-16  
**Depends on:** Decision 002 (relational primary System of Record); Decision 003 (PostgreSQL as that SoR)

This decision selects the **orchestration strategy**: how long-lived research flows are coordinated.

It does **not** select:

- a queue / broker product
- Worker communication protocol (HTTP, RPC, gRPC, etc.)
- cache / ephemeral store
- deployment model (Docker, Kubernetes, cloud)
- a concrete workflow-engine or task-queue product

Python is the locked first-implementation language (Decision 001). Orchestration contracts must remain **language-neutral**. This decision is **not** Python-locked. Platform remains the owner of orchestration *capability*; Core, Research, and Data must not depend on a concrete orchestrator (PROJECT_STRUCTURE.md).

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**PRODUCT: DEFER**

Research OS v1 uses a **hybrid orchestration strategy**:

| Layer | Role |
|---|---|
| **PostgreSQL** | Authoritative **domain** System of Record |
| **Platform orchestration** | Durable **coordination** only (timers, retries, pending work, waits, progress) |
| **Workers** | Replaceable **execution** runtimes; produce untrusted WorkerResult |
| **Core** | Authorization, policy, scope, budget, and recorded Approval authority |

This is an architectural split, not a product choice. A durable workflow **engine** (Temporal-class), a task queue, Prefect-style pipelines, and a custom PostgreSQL-backed state machine are **evaluated below and not selected**.

The first implementation of the Platform orchestration contract may be local/in-process and may persist coordination records that are **not** domain truth. Introducing a named orchestration product requires a later decision.

---

## Why this decision exists

The domain has long-lived flows:

ResearchRun → Hypothesis → Experiment → Authorization → Worker execution → WorkerResult → Transition A → Evidence Admission → Verification → Candidate lifecycle → FindingProposal → Human Review → Approval → Finding

Also true:

- Workers can crash; hosts can restart
- remote Workers may exist later (not required now)
- Human Review can leave work pending for a long time
- retries, timeouts, cancellation, and duplicate-safe execution are needed
- authorization/scope must be re-checked after redirects or newly discovered targets
- budgets are immutable Core-issued limits; orchestration cannot change them
- **execution state is not domain truth**
- authoritative domain state is PostgreSQL
- a workflow engine cannot be a truth source
- orchestration cannot own Domain/Core authority

`TECHNICAL_REQUIREMENTS.md` makes **domain SoR + durable WorkerResult** survive restart a hard recoverability requirement. Exact mid-step workflow resume and specific replay semantics are **preferred**, not hard, and do not choose an orchestrator.

Choosing “just call Workers from the app” without separating coordination from domain state would eventually bury retries, waits, and dispatch flags inside Experiment/FindingProposal rows. Choosing a durable engine as truth would violate Core and Decision 003.

---

## Three states (must stay separate)

### Domain state (authoritative truth)

PostgreSQL System of Record: Program, AuthorizationSource, ScopeRule, ResearchRun, Budget, Experiment lifecycle, WorkerResult records, Observation/Artifact metadata, Evidence, Candidate, Verification records, FindingProposal, Finding, Approval, Snapshot, ChangeEvent, AuditEvent.

Human approval **is** a Core-recorded Approval (and the derived FindingProposal view). It is **not** a workflow wait flag.

### Orchestration state (coordination only)

Timers, retries, pending activities, waiting-for-signal, workflow/progress cursors, dispatch leases.

Orchestration state is **never**:

- authorization truth
- Evidence truth
- Finding truth
- Research Memory truth
- Budget policy
- Approval truth

If orchestration state is lost and PostgreSQL remains, domain truth remains. Coordination may need to be reconstructed from domain records plus untrusted WorkerResult. That reconstruction must re-enter through Core (authorization/scope/budget), not through “the workflow said so.”

### Worker state (ephemeral execution)

In-process tool/runtime details. WorkerResult re-enters the system as **UNTRUSTED EXECUTION OUTPUT**. Durable WorkerResult ≠ trusted fact. Workers cannot self-authorize, determine scope, or change budget.

---

## Candidates considered (strategies)

1. **Plain application orchestration** — in-process state machine, database-backed domain state, manual retries
2. **Job queue + persisted domain state** — background jobs, queue dispatch, DB as truth, orchestration logic in the application *(queue product not chosen)*
3. **Durable workflow engine as the strategy** — workflow persistence, retries, timers, wait-for-event/approval, activities, replay/durable-execution semantics as the primary coordination model
4. **Hybrid** — durable coordination for long-lived orchestration; Workers remain replaceable execution; PostgreSQL remains domain SoR; Core remains authority

No additional strategy class was added (pure event-sourcing orchestrators, Kubernetes-only controllers, or “the LLM drives the loop” are out of scope and would violate architecture).

---

## Stage 1 — Mandatory gates

A strategy that cannot preserve these is not viable, even if it is operationally simple.

| Gate | Meaning |
|---|---|
| Core authority preservation | Orchestration dispatches work Core already allowed; it cannot authorize, widen scope, or change budget |
| Domain SoR remains PostgreSQL | Orchestrator failure must not rewrite or replace domain truth |
| Workflow state ≠ domain truth | Timers/retries/waits are not Evidence, Finding, Approval, or authorization |
| Human approval is Core-recorded | Interface presents review; Core records Approval; workflow wait is not Approval |
| Retry side-effect safety | Retries must not silently duplicate Worker side effects; duplicate-safe / correlation is required as a capability |
| Redirect / new target re-evaluation | Discovered or redirected targets require Core re-evaluation before continued execution |
| Worker cannot self-authorize | Execution stays behind Core-issued authorization and immutable budget limits |
| Language-neutral Platform contract | Core/Research/Data depend on orchestration *capability*, not a product or Python-only library |

### Gate results

Multiple strategies can satisfy Stage 1 **if constrained**. None is the only capable option.

| Strategy | Stage 1 | Note |
|---|---|---|
| **Plain application orchestration** | **Pass, with a coordination gap** | Domain truth can live in PostgreSQL. Long-lived waits/retries/crash recovery of *coordination* become custom code. Does not fail Core authority by existing |
| **Job queue + persisted domain state** | **Pass, with collapse risk** | Viable if the queue is never treated as truth. Orchestration semantics still live in application code; drift vs domain lifecycle is the hazard |
| **Durable workflow engine (as the strategy)** | **Pass only as coordination** | Capable of durable timers, waits, retries, crash recovery of coordination. **Fails Stage 1 if** workflow history is treated as authorization, Approval, Evidence, or Finding. Not rejected for “being distributed” or “being durable” |
| **Hybrid** | **Pass** | Encodes the required split: coordination vs SoR vs Workers vs Core. Does not by itself select Temporal or any product |

Stage 1 does **not** pick the winner. Hybrid is selected because it is the best **combined project fit after** the gates, not because the others cannot coordinate a process.

---

## Consistency boundaries (conceptual)

These are not APIs. They test whether the strategy can hold the domain.

| Flow | Must not happen | Implication for orchestration |
|---|---|---|
| Experiment start | Worker runs without Core authorization | Orchestration may only dispatch an already-authorized request |
| Budget | Budget decremented but execution never started, or execution started without budget | Domain transaction stays in PostgreSQL (Decision 003). Orchestration must not have a second budget |
| Redirect / new asset | Worker continues onto an unauthorized target | Stop; Core re-evaluation; new authorization. Workflow progress is not a scope grant |
| Transition A | Evidence or interpretation created at WorkerResult ingest | Orchestration can trigger ingest; it cannot admit Evidence |
| Transition B | Evidence admitted as a side effect of retry/replay | Evidence admission is a separate, auditable domain transition |
| Human Review | Approval exists only as a workflow wait, or Finding created from workflow signal | Core Approval in PostgreSQL is the decision; Finding creation is the same domain transaction as Decision 003 |
| Retry | Second Worker execution duplicates side effects because a timer fired | Correlation / duplicate-safe policy at the execution boundary; not “the orchestrator said retry, so it is allowed” |
| Engine/app crash | Domain rows rewritten to match a lost workflow | PostgreSQL wins; coordination is rebuilt or abandoned; Core is re-consulted |

**Human approval wait** is primarily a **domain lifecycle** (FindingProposal pending Human Review). A coordinator may *wake* after Core records Approval. It must not *be* the Approval.

---

## Strategy evaluations

### 1. Plain application orchestration

**Fit:** Strongest **local/simple** alternative. Weakest durable-coordination story.

**Strengths:** simplest v1, minimal infrastructure, easy debugging, no extra product, natural local/in-process fit (`TECHNICAL_REQUIREMENTS.md` prefers that until topology justifies more).

**Risks:** retries, timers, crash recovery of in-flight coordination, duplicate execution, and long-lived waits become custom. Temptation to store `retry_count` / `awaiting_workflow` on domain rows, collapsing orchestration into PostgreSQL domain truth.

Not a toy. Not selected as the strategy because this domain’s coordination needs (Worker crash, later remote Workers, timers, duplicate-safe retry, wake-after-approval) would recreate a poor orchestrator inside application code and/or domain tables.

### 2. Job queue + persisted domain state

**Fit:** Serious common-pattern alternative. Not selected as the named strategy because it still leaves orchestration semantics application-owned, and this decision must **not** choose a queue/broker.

**Strengths:** async Worker dispatch, PostgreSQL can remain truth, simpler than an engine, familiar.

**Risks:** retry + domain state-machine drift; waiting/timers/approval still custom; duplicate jobs; treating the queue as durable truth (forbidden); partial “job succeeded, domain write failed.”

A queue can later be an **implementation detail** of Platform dispatch. It is not this decision.

### 3. Durable workflow engine (as the strategy)

**Fit:** Strongest **coordination-capability** class (timers, wait-for-signal, activity retries, crash recovery of orchestration, history). Premature as the v1 strategy if it means adopting an engine now, and dangerous if the engine becomes truth.

**Strengths:** long-running workflows; durable timers; wait-for-external-event; retry/timeout; activity boundaries; workflow history for *coordination* observability.

**Risks:** new infrastructure; operational complexity; replay/versioning mental model; workflow-code constraints; vendor/tool coupling; debugging curve; **product types leaking into Domain/Core**; encoding policy in workflows; human approval living only in a wait state.

Not rejected because durable execution is “wrong.” Not rejected because distributed systems fail correctness. Not selected as the v1 strategy because `TECHNICAL_REQUIREMENTS.md` forbids introducing a distributed communication plane until topology justifies it, and because fashion is not a reason. The **capability class** remains the leading product-family candidate when revisit triggers fire.

### 4. Hybrid

**Fit:** Best combined fit for this architecture.

Durable orchestration = **coordination only**.  
PostgreSQL = **authoritative domain truth**.  
Workers = **execution only**.  
Core = **authorization / policy / budget / Approval**.

This matches PROJECT_STRUCTURE.md: Platform provides orchestration capability; orchestration callers sit below Research; they dispatch work already authorized by Core; Core, Research, and Data must not depend on concrete Platform implementations.

Hybrid does **not** mean “Temporal + PostgreSQL because that is popular.” It means the three-state split is mandatory, and coordination must be allowed to become durable **without** becoming truth.

---

## Comparison matrix

Scores: **5 = better project fit**, **1 = worse project fit**. Totals are **not** the decision. **P** = plain app. **Q** = job queue + DB. **E** = durable engine as the strategy. **H** = hybrid.

| # | Criterion | P | Q | E | H | Short rationale |
|---|---|---:|---:|---:|---:|---|
| 1 | correctness | 3 | 4 | 4 | 5 | All can be correct if constrained. H makes the truth/coordination split explicit. E is correct only if it is not SoR |
| 2 | Core authority preservation | 4 | 4 | 3 | 5 | E scores lower on **temptation** to put policy in workflows, not on inability. H forbids that by role |
| 3 | durable coordination | 2 | 3 | 5 | 5 | P/Q custom. E/H designed for it. H does not require choosing E’s product now |
| 4 | long-running workflows | 2 | 3 | 5 | 5 | Domain lifecycles are long; P stores them in SoR but does not coordinate execution durably |
| 5 | crash recovery | 3 | 3 | 4 | 5 | Hard req is SoR+WorkerResult (all can). Coordination recovery is preferred; H keeps that off the SoR |
| 6 | external event waiting | 2 | 3 | 5 | 5 | P/Q poll or custom. E/H can wait without becoming the event’s meaning |
| 7 | human approval waiting | 3 | 3 | 3 | 5 | Approval is domain/Core. P/Q/E can fake it as a wait. H: wake after Core Approval only |
| 8 | retry semantics | 2 | 4 | 5 | 5 | Capability. Safe retries still need duplicate-safe execution at Worker boundaries |
| 9 | duplicate-safe execution | 2 | 3 | 4 | 4 | No strategy gives this for free. Must be a constraint on all |
| 10 | cancellation | 2 | 3 | 4 | 4 | Engine primitives help; Core/domain must still record cancelled Experiment/Run |
| 11 | timeout handling | 2 | 3 | 5 | 5 | Durable timers are E/H strength. Timeout is not a budget change |
| 12 | budget enforcement compatibility | 4 | 4 | 3 | 5 | Budget stays Core-issued. E temptation to encode remaining budget in workflow memory |
| 13 | remote Worker compatibility | 2 | 4 | 4 | 5 | Not required now. H keeps Workers replaceable. P in-process does not force remote, and must not |
| 14 | observability | 3 | 4 | 5 | 4 | E has workflow history (coordination, not audit truth). Domain audit stays AuditEvent in PostgreSQL |
| 15 | auditability | 4 | 4 | 3 | 5 | AuditEvent/Approval in SoR. E history must not replace AuditEvent |
| 16 | workflow versioning/evolution | 3 | 3 | 3 | 4 | E replay/versioning is powerful and costly. H can start thin and replace the Platform adapter |
| 17 | local development simplicity | 5 | 3 | 1 | 4 | P wins. H stays simple **while product is deferred**. E as v1 strategy loses |
| 18 | single-developer suitability | 5 | 4 | 2 | 4 | Same pattern. E ops are a v1 burden this project does not have yet |
| 19 | operational complexity | 5 | 3 | 1 | 4 | 5 = simpler. H with deferred product avoids E’s cluster. Q adds a broker we are not choosing |
| 20 | vendor lock-in risk | 5 | 3 | 2 | 4 | H is a contract. E products couple replay/SDK. Q couples broker semantics |
| 21 | Python ecosystem | 5 | 4 | 4 | 5 | Stage 2. Clients exist. **Python must not force Celery/Prefect.** H is language-neutral |
| 22 | PostgreSQL independence | 3 | 4 | 4 | 5 | P/Q tend to overload SoR with job fields. H forbids PostgreSQL-as-engine-by-accident |
| 23 | domain truth outside orchestrator | 3 | 3 | 2 | 5 | The differentiator. E fails this in practice unless Hybrid constraints are applied — which is H |
| 24 | testability | 5 | 4 | 3 | 4 | P easiest. E needs time-skipping/test servers. H contract can be faked |
| 25 | future scale | 2 | 3 | 5 | 5 | E/H headroom. Scale is not a current requirement; remote Workers are a revisit trigger |

**Reading the matrix:** Plain wins local simplicity. Queue+DB is a capable dispatch pattern without being chosen as a broker. A durable engine wins coordination primitives and loses v1 ops / truth-temptation. Hybrid wins because this project must have **both** PostgreSQL domain truth **and** durable coordination **without** letting either absorb the other.

---

## Stage 2 — Differentiators

Among Stage 1–viable constrained strategies:

| Differentiator | Winner | Why |
|---|---|---|
| Keep domain truth out of the orchestrator | Hybrid | Explicit roles; E as a *strategy* tends to invert this |
| Long-lived Worker/approval/retry coordination | Hybrid / engine-class | Domain already models FindingProposal wait; execution still needs durable dispatch |
| Single-developer / local first | Plain, then Hybrid-with-deferred-product | Requirements prefer in-process until topology justifies a plane |
| Operational complexity | Plain | Hybrid defers the engine so v1 need not pay Temporal-class ops |
| Remote Worker future | Hybrid | Workers stay replaceable; nothing here forces remote now |
| Replaceability | Hybrid | Platform contract; product later |
| Not fashionable durable-workflow | Hybrid + product DEFER | Engine class is respected and **not** installed as v1 identity |

---

## Product shortlist (evaluated, not selected)

Because the strategy allows a durable coordination layer, these products/classes were compared. **None is chosen.**

| Candidate | Strategy fit | Why not now |
|---|---|---|
| **Temporal** | Best-known fit for durable timers, signals (wake after Core Approval), activity retries, crash recovery of **coordination**, language-neutral SDK, self-host possible | Operational burden, replay/versioning model, local extra server, lock-in if workflow types leak into Domain/Core. Not truth. Not required before remote/long-wait coordination pain is measured. **Not selected because it is fashionable** |
| **Celery-style task queue** | Dispatch/retries; weaker durable wait-for-approval/timers/versioning | This is a **queue pattern**, not a durable workflow engine. Python-centric; Decision 001 must not force it. Queue must not be truth. Broker not chosen here |
| **Prefect-style workflow orchestration** | Fine for data/ML pipelines | Weak fit for Core-gated authorization, Approval→Finding, and WorkerResult trust boundaries. Cloud/tool coupling risk |
| **Custom PostgreSQL-backed state machine** | Tempting for one developer | Highest risk of **PostgreSQL becoming the workflow engine by accident** and of orchestration columns polluting domain records. Allowed later only as a *thin Platform adapter* whose tables are not domain truth — and that would be a new decision |

**PRODUCT FIT:** Temporal is the strongest **future** engine-class candidate for the hybrid coordination role. It is not accepted, not accepted-with-constraints, and not the System of Record. Celery/Prefect are weaker class fits. Custom PG state machine is not selected as the orchestration product.

---

## Constraints (accepted with the strategy)

1. **PostgreSQL remains the authoritative domain SoR.** Orchestration failure must not rewrite domain truth.
2. **Core remains authorization/policy/budget/Approval authority.** Orchestration cannot widen scope, change budget, or authorize Workers.
3. **Workers cannot self-authorize.** They execute Core-issued work and return WorkerResult.
4. **Workflow/coordination state ≠ domain truth.** It is never authorization, Evidence, Finding, Approval, or Research Memory.
5. **Human approval remains Core-recorded Approval** in PostgreSQL (FindingProposal view derived from that). It does not live only in workflow state.
6. **Retries cannot silently duplicate side effects.** Duplicate-safe / correlation / non-retryable classification are required at execution boundaries. Replay-aware execution is preferred (`TECHNICAL_REQUIREMENTS.md`) and does not select an engine.
7. **Redirect or discovered target → Core re-evaluation** before continued execution.
8. **Transition A and Transition B stay separate.** Orchestration may schedule them; it may not merge them into one “workflow step that creates Evidence.”
9. **No product-specific workflow types in Domain/Core/Research.** If an engine is chosen later, adapters live in Platform/Workers. Contracts stay language-neutral.
10. **Python does not choose the orchestrator.** Celery/Prefect convenience is not a reason.
11. **Remote Workers are not forced.** Local/in-process communication remains preferred until topology justifies more.
12. **First implementation of Platform orchestration may be thin** (in-process and/or persisted coordination records that are not domain entities). That is not a silent selection of “custom PostgreSQL workflow engine” or of a broker.
13. **Research Memory is not orchestration and not SoR.**

---

## Hard invariants (any future product)

- PostgreSQL remains authoritative domain SoR
- Core remains authorization authority
- orchestration cannot widen scope
- orchestration cannot change budget
- Worker cannot self-authorize
- workflow state ≠ domain truth
- retries cannot silently duplicate side effects
- redirect/discovered target requires Core re-evaluation
- human approval remains Core-recorded Approval
- workflow engine failure must not rewrite domain truth

---

## Strongest alternatives (not selected as the v1 strategy)

### Strongest local/simple alternative — Plain application orchestration

Not the strategy. Strong for v1 friction. Weak for durable coordination without collapsing waits/retries into domain rows or process memory.

### Strongest dispatch-pattern alternative — Job queue + persisted domain state

Not the strategy. Capable if the queue is not truth. Not chosen because this decision must not select a broker, and because orchestration semantics would remain ad-hoc relative to the required state split.

### Strongest engine-class alternative — Durable workflow engine (Temporal-class)

Not the v1 strategy and **not the product**. Serious coordination capability. Premature operational complexity; truth-temptation; not justified by current topology. Revisit when coordination durability is a measured need.

---

## Revisit triggers

Revisit **product** (not automatically invert the hybrid split) if:

- in-process/thin coordination loses waits, retries, or wake-after-approval in real runs
- duplicate Worker side effects appear under retry
- human-approval turnaround requires durable timers/signals that a thin adapter cannot hold
- remote Worker topology is actually adopted
- crash recovery of **coordination** (not domain SoR) becomes an operational incident class
- workflow versioning/replay is needed as a measured capability
- operational burden of a later engine exceeds its benefit (then stay thin or change product, do not move truth into the engine)

Do not revisit in order to make the orchestrator the SoR.

---

## Open questions after this decision

Intentionally unanswered:

- Temporal vs any other engine
- Celery or any broker/queue product
- Prefect or other pipeline orchestrators
- custom coordination schema on PostgreSQL
- Worker communication protocol
- cache
- deployment topology
- exactly how duplicate-safe Worker execution is implemented
- exactly how wake-after-Approval is delivered to the coordinator

---

## Confidence

**MEDIUM**

The hybrid **split** is the only strategy that matches Core / Platform / Workers / PostgreSQL roles without treating an engine or a queue as truth. Product is deferred because a Temporal-class engine is capable and premature, and because choosing Celery/Prefect/custom-PG-engine would either Python-lock the control plane, select a broker, or turn PostgreSQL into a workflow engine.

Confidence is not HIGH because the first thin Platform adapter is unspecified, remote Workers are future, and a poorly bounded “coordination table” could still pollute domain truth.

---

## Self-audit

| Forbidden reading | Status |
|---|---|
| Orchestrator becomes truth source | **Rejected in constraints.** PostgreSQL is SoR |
| Workflow engine owns Core policy | **Rejected.** Core only |
| Retries bypass side-effect safety | **Rejected.** Duplicate-safe is mandatory; not implemented here |
| Human approval lives only in workflow state | **Rejected.** Core Approval in PostgreSQL |
| PostgreSQL becomes workflow engine by accident | **Rejected as product.** Thin coordination adapter, if used, is not domain truth and is not selected here |
| Queue is durable truth | **Queue not chosen; must not be truth** |
| Remote workers forced before needed | **Explicitly not forced** |
| Product-specific workflow types leak into Domain/Core | **Forbidden; product deferred** |
| Python language decision forces orchestration product | **Rejected.** Celery/Prefect not selected |
| “Durable workflow” chosen only because fashionable | **Rejected.** Strategy is the split; engine product deferred |

**FINAL STATUS: PASS**

---

# Decision 005 — Worker Communication / Topology

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 001 (Python primary; Workers may be another language); Decision 004 (hybrid orchestration; orchestration product deferred)

This decision selects **where Workers run relative to the Control Plane** for the first implementation, and **what communication abstraction** sits between them.

It does **not** select:

- HTTP vs RPC vs gRPC vs any other wire protocol
- a message broker / queue product
- a workflow-engine activity transport (Decision 004 product is deferred)
- a container runtime
- Kubernetes
- a secrets product
- a deployment model (Decision 010)

---

## Decision

**TOPOLOGY: ACCEPT WITH CONSTRAINTS — mixed**

**COMMUNICATION: ACCEPT WITH CONSTRAINTS — mixed transport behind one Worker contract**

**First working implementation:**

| Piece | Where / what |
|---|---|
| Control Plane | Local on the developer host (currently Windows + Cursor). Core, Research, Data access, Interface, and Platform contracts run here |
| Workers | Behind a single language-neutral **Worker contract**. The initial **tool-execution** worker runs in **Kali/WSL**. Local **child-process** workers are allowed for mocks, tests, and non-Kali work. In-process calls are for **test doubles only**, not the isolation story for side-effect Workers |
| Communication | One Worker contract. First implementation uses **local IPC / subprocess** (including the Windows host ↔ Kali/WSL OS-environment boundary). **No mandatory distributed broker.** No workflow-engine transport is selected |
| Future | Same Worker contract → authenticated **remote** Workers over a later-chosen request/response (or other) transport. Broker/engine remain unchosen |

Kali/WSL is the **initial security-tool integration environment**. It is **not** the architecture, **not** a production runtime mandate, and **not** a Control Plane dependency. Research OS must not depend on Kali or Strix (`TECHNICAL_REQUIREMENTS.md`).

Strix is an optional **Integration** a Worker may use. Strix is **not** a Worker, not the Worker contract, and not the topology.

---

## Why this decision exists

Workers are the only side-effect layer. They cannot run without Core authorization, cannot write PostgreSQL domain truth, and return untrusted WorkerResult.

The current developer setup is Windows + Cursor, with Kali/WSL as the expected first place security tools exist. That setup must be **usable** without becoming **permanent architecture**. Remote Workers and a distributed communication plane are future possibilities, not current requirements (`TECHNICAL_REQUIREMENTS.md`: local/in-process communication first; do not introduce a distributed plane until topology justifies it).

A single in-process Worker inside the Control Plane would blur isolation, crash domains, and language-neutrality (Workers may be non-Python). A remote-only topology would be premature. A Kali-only topology would freeze WSL as production. Mixed topology + one contract is the path that keeps Core/Research stable while execution location changes.

---

## Security / trust boundaries

These are different trusts. Authentication is not authorization.

| Boundary | Trust |
|---|---|
| **Control Plane** | Higher trust: Core (authorization/policy/budget/Approval), Research (proposals), Data access to PostgreSQL SoR, Platform contracts |
| **Worker** | **Less trusted than Core.** Executes only Core-issued work. Applies immutable issued budget; cannot change it. Cannot grant itself scope |
| **Transport** | Delivery mechanism. Not domain truth. Message delivery ≠ execution success. Execution success ≠ Evidence. Communication mechanism is not the SoR |
| **Tool / Integration** | Untrusted input (including Strix, Burp, scanner output, web content). Enters as WorkerResult, then Transition A |

A remote Worker that is **authenticated** is still **not authorized** by being on the same network or by presenting a worker identity. Authorization still comes from Core, per request.

Worker identity must be **auditable now** and **authenticated when the Worker is no longer a test double** — including Kali/WSL and any later remote Worker. Identity answers “which worker runtime ran this.” Core answers “was this allowed.”

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Core authority | Worker cannot authorize, widen scope, or change budget |
| WorkerResult untrusted | Output is not Observation/Evidence/Finding until Transition A / later domain transitions |
| No direct Data writes | Worker cannot write authoritative PostgreSQL domain truth |
| Language-neutral Worker contract | Core/Research do not depend on a Worker language, Kali, Strix, or a transport product |
| Transport ≠ truth | Queue/message/request is delivery, not SoR |
| Replaceability | Local → Kali/WSL → remote must not change Domain/Core contracts |
| Current env ≠ architecture | Windows/Kali/WSL must not become production topology |
| Isolation as a property | Process/OS boundary for real side effects; not a container/K8s product choice |

### Topology gate results

Multiple topologies can pass Stage 1 **if constrained**. Mixed is not the only capable option.

| Topology | Stage 1 | Note |
|---|---|---|
| **In-process workers** | **Pass for fakes only** | Viable test doubles. Weak isolation, shared fate with Control Plane, poor fit as the side-effect Worker. Does not fail Core authority by existing |
| **Local child-process workers** | **Pass** | Real process isolation, crashes stay off the Control Plane, language-neutral. Does not by itself reach Kali tools |
| **Local Kali/WSL workers** | **Pass as first tool-execution location** | Fits initial tool environment **behind the contract**. Fails Stage 1 if Kali/WSL *is* the Worker architecture or production runtime |
| **Remote workers over authenticated transport** | **Pass as a future capability** | Required properties (authn, timeout, cancel, correlation) are defined. Selecting remote *now* is Stage 2 premature distribution, not a correctness win |
| **Mixed topology** | **Pass** | One contract; first impl uses child-process + Kali/WSL; remote later. Does not select a broker |

### Communication gate results

| Strategy | Stage 1 | Note |
|---|---|---|
| **A. Direct in-process call** | **Pass for fakes** | Not the side-effect Worker path |
| **B. Local IPC / subprocess** | **Pass** | First-implementation primary. Includes host ↔ WSL as a **local OS-environment** boundary, not a distributed plane |
| **C. Direct request/response transport** | **Pass as future** | Natural remote path. Protocol **not** chosen |
| **D. Queue/broker mediated execution** | **Pass only if never truth** | Not mandatory. Broker product not chosen. Premature as a required plane |
| **E. Workflow-engine activity transport** | **Not available as a choice** | Decision 004 deferred the engine product. Must not sneak-select Temporal/Celery here |
| **F. Mixed transport behind one Worker contract** | **Pass** | Selected. A/B now; C later; D/E remain unchosen and non-mandatory |

---

## Candidate evaluations (topology)

### In-process workers

Simplest debugging. Shared address space with Control Plane. A Worker crash, native tool fault, or hung scan can take down Core. Decision 001 forbids subprocess and tool SDKs in Core/Research; in-process side-effect Workers pull those hazards into the Control Plane process. Allowed as **mocks/fakes**. Not the first real Worker topology.

### Local child-process workers

Serious default isolation story: separate process, timeout/kill, different language possible, filesystem/environment can differ from Control Plane. Does not by itself provide Kali toolchains. Complements Kali/WSL rather than replacing the contract.

### Local Kali/WSL workers

Serious first **tool-execution** location: security tools live there; Windows host is the Control Plane/dev environment. Windows ↔ WSL has environment, filesystem, and tool-availability differences — that is why the Worker is not in-process on Windows. This is still **local** (same developer machine), not remote. Must not make WSL a required production runtime or a Core dependency.

### Remote workers over authenticated transport

Serious future: other hosts, worker pools, authenticated identity, network untrust. Latency, artifact transfer, cancellation, and result size become harder. Not selected for first implementation. `TECHNICAL_REQUIREMENTS.md` forbids introducing that plane until topology justifies it.

### Mixed topology

Selected. Control Plane stays local. Worker **abstraction** exists from day one. First tool-execution worker is Kali/WSL. Child-process workers exist for isolation and tests. Remote is an evolution of the **same contract**, not a new Domain.

---

## Candidate evaluations (communication)

**A** — Direct in-process call: fakes only.

**B** — Local IPC/subprocess: first implementation. No broker. Delivery still ≠ success; the Control Plane records WorkerResult in PostgreSQL after receipt/validation, not because a pipe closed.

**C** — Direct request/response: future remote. Product/protocol deferred. Must support authentication, timeout, retry, cancellation, correlation, auditability (`TECHNICAL_REQUIREMENTS.md` §4).

**D** — Queue/broker: optional later dispatch aid. Not truth. Not mandatory. Not chosen.

**E** — Workflow-engine activity transport: blocked on Decision 004 product DEFER.

**F** — Mixed behind one contract: selected so Core/Research never see Kali vs remote vs child-process.

Correlation id, cancellation, timeout, and duplicate/retry awareness are **contract properties**, not broker properties. They must exist on the Worker contract in the first implementation even with only IPC/subprocess.

Redirect / discovered asset: Worker **stops**, returns through WorkerResult / a re-authorization request, and does not continue until a **new Core decision**. Topology does not grant scope.

---

## Comparison matrix (project fit)

**5 = better project fit.** Totals are not the decision.

**IP** = in-process. **CH** = local child-process. **KW** = Kali/WSL local. **RM** = remote now. **MX** = mixed (selected).

| # | Criterion | IP | CH | KW | RM | MX | Short rationale |
|---|---|---:|---:|---:|---:|---:|---|
| 1 | Core authority preservation | 3 | 4 | 4 | 4 | 5 | All can obey Core if constrained. MX keeps one contract so location cannot become authorization |
| 2 | Worker isolation boundary | 1 | 5 | 4 | 5 | 5 | IP shares fate. CH/KW/RM isolate. MX uses CH+KW first |
| 3 | local development simplicity | 5 | 4 | 3 | 1 | 4 | KW adds WSL friction that the current tool env needs. RM loses |
| 4 | Kali/WSL integration | 1 | 2 | 5 | 3 | 5 | KW is the first tool host. MX includes it without making it the architecture |
| 5 | remote-worker future | 1 | 3 | 3 | 5 | 5 | Same contract. RM-now is premature, not “more future” |
| 6 | authentication capability | 2 | 3 | 3 | 5 | 4 | Local still needs worker **identity**. Remote requires authn. Authn ≠ authz |
| 7 | cancellation | 3 | 4 | 4 | 4 | 4 | Process kill vs remote cancel; contract must support both. No product chosen |
| 8 | retry / duplicate safety | 3 | 4 | 4 | 3 | 4 | Correlation on the contract. Transport redelivery must not mean “run again” |
| 9 | correlation / auditability | 3 | 4 | 4 | 4 | 5 | Worker identity + correlation id + AuditEvent in PostgreSQL, not in the pipe |
| 10 | debugging | 5 | 4 | 3 | 1 | 4 | Local wins. KW is still on-machine |
| 11 | failure isolation | 1 | 5 | 4 | 5 | 5 | Worker crash must not take Core down |
| 12 | artifact / result transfer | 4 | 4 | 3 | 2 | 4 | Local copies first. Remote transfer is a later problem; bytes still not SoR |
| 13 | operational complexity | 5 | 4 | 3 | 1 | 4 | 5 = simpler. MX first impl has no broker |
| 14 | single-developer suitability | 5 | 4 | 4 | 1 | 4 | Matches current Windows + Kali/WSL **context** |
| 15 | portability | 2 | 4 | 2 | 4 | 5 | KW is not portable architecture. MX can drop WSL later |
| 16 | production evolution | 1 | 3 | 2 | 4 | 5 | Path without Domain change |
| 17 | vendor lock-in | 5 | 5 | 4 | 3 | 5 | No broker/K8s/Strix required |
| 18 | observability | 3 | 4 | 4 | 4 | 4 | Worker execution is observable; transport is not the audit log |
| 19 | security boundary clarity | 2 | 4 | 4 | 4 | 5 | Explicit Control Plane vs Worker vs Transport vs Integration |
| 20 | local → remote migration | 1 | 3 | 3 | 5 | 5 | Contract stability is the point of MX |
| 21 | avoiding premature distribution | 5 | 5 | 4 | 1 | 5 | No mandatory broker/remote plane |

Communication strategies (project fit for **first impl + evolution**): A=2 as primary, B=5, C=3 (future), D=2 (premature mandatory), E=1 (product deferred), F=5.

---

## Stage 2 — Why mixed + contract wins

Not because other topologies cannot execute a tool.

This project needs: Core-gated side effects, Kali tools on day one, child-process isolation, no broker, and a later remote Worker **without** rewriting Domain/Core.

- In-process fails isolation and language-neutral Workers.
- Child-process alone misses the stated first tool environment.
- Kali/WSL alone would freeze WSL as architecture.
- Remote now violates local-first and single-developer constraints.
- A broker or workflow-activity bus would select communication/orchestration products this file has deferred.

---

## Constraints

1. **One language-neutral Worker contract.** Core/Research/Data do not know Windows vs WSL vs remote.
2. **Side-effect Workers are out-of-process** relative to the Control Plane (child-process and/or Kali/WSL). In-process is fakes/tests only.
3. **Worker cannot write authoritative PostgreSQL.** WorkerResult is accepted by Control Plane / Data ingest (Transition A), not by the Worker opening the SoR.
4. **WorkerResult remains untrusted** until Transition A. Execution success ≠ Evidence.
5. **Transport is replaceable and is not truth.** Delivery ≠ execution success.
6. **No mandatory distributed broker** in the first implementation.
7. **No workflow-engine activity transport** until Decision 004’s product is decided.
8. **Kali/WSL is an adapter location**, not a Core dependency, not Strix, not production-by-default.
9. **Worker identity** is auditable; **authentication** is required when the Worker is reachable as a service (including later remote). Authentication ≠ Core authorization.
10. **Redirect / new asset:** stop, re-authorization from Core, no continue-on-topology.
11. **Correlation id, cancellation, timeout, duplicate/retry awareness** are contract requirements now.
12. **Immutable issued budget** is applied by Worker/Platform runtime; Worker cannot raise it.
13. **Deployment topology is not domain logic** (see Decision 010).

---

## Strongest alternatives (not selected as the v1 topology)

- **Strongest simple isolation alternative:** local child-process only — misses initial Kali/WSL tool execution unless WSL is smuggled in without a contract.
- **Strongest first-tool-environment snapshot:** Kali/WSL-only — would make WSL look like the architecture.
- **Strongest future plane:** remote authenticated request/response — correct later, premature now.
- **Not selected communication:** mandatory queue/broker; workflow-engine activities.

---

## Revisit triggers

- Concrete need for Workers on another machine (then evaluate C; still no automatic broker)
- IPC/subprocess cannot carry result/artifact size, cancellation, or concurrency
- Duplicate side effects under retry despite correlation ids
- WSL/host boundary becomes an operational blocker (change **adapter**, not Domain)
- Authentication of local workers is insufficient for the actual threat model
- Decision 004 selects an engine whose activity transport is considered (new decision; must not become truth)

---

## Open questions

- Exact IPC mechanism (pipes, localhost sockets, etc.)
- Exact future remote protocol
- Broker yes/no as a later dispatch aid
- Artifact byte movement across WSL/remote
- Worker authentication implementation (not a secrets product choice)

---

## Confidence

**MEDIUM**

The first-implementation shape matches locked requirements (local Control Plane, Worker abstraction, Kali/WSL tool worker, no mandatory broker) without freezing Windows/Kali as architecture. Confidence is not HIGH because the concrete IPC mechanism, WSL authn, and artifact transfer are unchosen, and a sloppy adapter could still let a Worker touch PostgreSQL or treat WSL as Core.

---

# Decision 006 — Artifact Storage Strategy

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 002 (Artifact metadata/reference in SoR; bytes topology open); Decision 003 (PostgreSQL is not the default artifact byte store); Decision 005 (Worker contract; Kali/WSL first tool Worker); Decision 010 (staged local-first deployment)

This decision selects **where artifact bytes live** relative to PostgreSQL, and whether a **byte-store abstraction** exists.

It does **not** select:

- an object/blob product (S3, MinIO, GCS, Azure Blob, etc.)
- a filesystem layout or path convention as domain contract
- a hash-function “product”
- a CDN, backup product, or queue for artifact transfer
- ORM, frontend, or cache product

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**Artifact byte-store abstraction**, with **local filesystem as the first adapter**, **metadata/reference/integrity in PostgreSQL**, and **object/blob storage later only if volume or topology requires it**.

| Concern | Where |
|---|---|
| Artifact **identity**, reference, provenance, kind, lifecycle, integrity metadata (including a content hash) | **PostgreSQL SoR** |
| Artifact **bytes** | **Byte-store adapter** — first implementation: **local filesystem**. Not domain truth |
| Byte **location** | Opaque locator stored in SoR. Location may change. **Identity must not** |

The byte store is not Evidence authority, Finding authority, Research Memory, or Core policy.

If artifact bytes are lost or the filesystem is wiped: **domain truth remains** (identity, provenance, Evidence, Finding, Approval). Missing bytes are a **reproducibility/availability** failure, not a silent rewrite of Findings. Integrity is checked by comparing stored bytes to the SoR hash when bytes are present.

No object-storage **product** is selected.

---

## Why this decision exists

Artifacts include screenshots, browser traces, HTTP captures, files, schemas, logs, code fragments, large WorkerResult payloads, and reproducibility material.

DOMAIN_MODEL.md: Artifact ≠ Evidence; attachment ≠ admission; integrity metadata should be preserved; storage locator is conceptual, not a product.

Decision 002/003: metadata/reference/provenance are SoR; PostgreSQL is **not** the default byte dump; bytes may sit outside the rebuild-from-SoR rule.

`TECHNICAL_REQUIREMENTS.md`: identity, provenance, integrity, and lifecycle metadata are hard; separate large/binary storage is **preferred**, not a mandated product.

Staged local-first deployment and Kali/WSL Workers mean bytes will cross a host/WSL boundary. That transfer must not make the Worker, WSL path, or a bucket into authority.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| SoR holds identity/provenance/integrity | Bytes cannot be the Artifact’s identity |
| Bytes ≠ truth | Byte-store loss must not delete Evidence/Finding/Approval |
| Artifact ≠ Evidence | Storing bytes does not admit Evidence |
| Locator ≠ identity | Moving bytes must not mint a new Artifact id |
| Worker ≠ authority | Remote/Kali Worker sending bytes does not authorize or admit Evidence |
| Portability | Windows path semantics must not enter Domain/Core contracts |
| No premature product | Object store not required to start |

### Strategy gate results

Multiple strategies can store bytes. The selected one is not the only capable store.

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. Bytes in PostgreSQL** | **Pass as capability, fail as default SoR role** | Can store blobs. Turns PostgreSQL into a dump; conflicts with Decision 003 “not the default artifact byte store.” Backup/size risk |
| **2. Local filesystem only (no abstraction)** | **Pass locally, fail as architecture** | Fine for a laptop. Path leakage, Windows vs WSL, and “FS is production” fail the locator≠identity and portability gates if FS *is* the contract |
| **3. Object/blob product in v1** | **Pass as a later adapter** | Premature product and ops. Abstraction is right; selecting a cloud/object product now is Stage 2 failure |
| **4. Hybrid small-in-SoR / large-external** | **Pass weakly** | Two byte homes and a size threshold. Small blobs still dump into PostgreSQL. Threshold becomes a magic constant |
| **5. Byte-store abstraction; FS first; object later** | **Pass** | SoR keeps identity/hash; first adapter is local FS; product deferred; location replaceable |

---

## Candidate evaluations

### 1. Bytes in PostgreSQL

Transactional with metadata; one backup story. Makes the SoR a blob store, inflates backups, weakens streaming/large-binary handling, and contradicts Decision 003. Not selected as the strategy. Tiny inline exceptions are **not** granted here (that would be strategy 4 by stealth).

### 2. Local filesystem without abstraction

Simplest v1 ops. Highest leak risk: `C:\...` / `/mnt/c/...` / WSL paths in domain records; FS becomes truth; later object migration rewrites “identity.” Not selected as the *strategy*; FS **is** allowed as the first **adapter**.

### 3. Object/blob storage in v1

Right long-term *class* for volume and remote Workers. Premature product, extra account/ops, vendor gravity. Not selected now. Remains the leading **future adapter** when revisit triggers fire.

### 4. Hybrid small/large split

Looks pragmatic; splits authority of bytes across SoR and external store; size cutover is arbitrary; complicates integrity and backup. Not needed for first implementation. Rejected as v1 strategy.

### 5. Abstraction + filesystem first + object later

Selected. Matches local-first (Decision 010), Kali/WSL transfer behind the Worker contract (Decision 005), and Decision 002’s byte exception without promoting FS or S3 to SoR.

---

## Comparison matrix (project fit)

**PG** = bytes in PostgreSQL. **FS** = filesystem as the contract. **OB** = object product in v1. **HY** = size-split hybrid. **AB** = abstraction + FS first (selected). 5 = better fit.

| # | Criterion | PG | FS | OB | HY | AB |
|---|---|---:|---:|---:|---:|---:|
| 1 | correctness | 3 | 3 | 4 | 3 | 5 |
| 2 | truth-boundary clarity | 2 | 2 | 4 | 2 | 5 |
| 3 | local simplicity | 4 | 5 | 1 | 3 | 4 |
| 4 | single-developer ops | 4 | 5 | 1 | 3 | 4 |
| 5 | portability | 4 | 1 | 4 | 3 | 5 |
| 6 | Windows/Linux compatibility | 4 | 2 | 4 | 3 | 5 |
| 7 | Kali/WSL integration | 3 | 2 | 3 | 3 | 4 |
| 8 | remote Worker future | 2 | 1 | 5 | 3 | 5 |
| 9 | failure recovery | 3 | 3 | 4 | 3 | 5 |
| 10 | backup/restore implications | 2 | 3 | 3 | 2 | 4 |
| 11 | retention support | 3 | 3 | 4 | 3 | 4 |
| 12 | integrity verification | 4 | 3 | 4 | 3 | 5 |
| 13 | operational burden | 3 | 5 | 1 | 2 | 4 |
| 14 | testability | 4 | 4 | 2 | 3 | 5 |
| 15 | migration path | 2 | 1 | 3 | 2 | 5 |
| 16 | scalability | 2 | 2 | 5 | 3 | 4 |
| 17 | vendor lock-in | 4 | 5 | 2 | 3 | 5 |
| 18 | security boundary | 3 | 3 | 4 | 3 | 5 |
| 19 | rebuildability | 2 | 2 | 3 | 2 | 4 |
| 20 | avoiding premature infrastructure | 4 | 5 | 1 | 3 | 5 |

Bytes are **not** rebuildable from SoR (Decision 002 exception). Rebuildability here means: metadata/provenance survive; a new byte adapter can be attached using the same identity/hash; companions/Research Memory are not the byte store.

---

## Conceptual integrity, retention, transfer

**Integrity:** PostgreSQL stores integrity metadata including a **content hash**. The byte adapter stores opaque bytes. On read, bytes are verified against the SoR hash. Hash mismatch = untrusted/corrupt bytes, not a new Finding. Exact hash algorithm is an open implementation detail, not a product.

**Stable reference:** Artifact id in SoR. Locator is a replaceable pointer (URI/key), never a Windows path in Domain/Core.

**Dedup:** Optional later using the hash. Not required in v1. Dedup must not merge distinct provenance records.

**Deletion / retention authority:** Domain lifecycle in PostgreSQL (and Core policy if retention is a control rule). The byte adapter **executes** byte deletion when the domain says so. The filesystem/object store must not be the retention policy owner. Supersede = **new Artifact** (DOMAIN_MODEL.md), not in-place byte rewrite of an identity.

**Immutable bytes:** In-place overwrite of stored bytes for an existing Artifact identity is forbidden. Correction = new Artifact + new hash.

**Kali/WSL / remote Workers:** Worker produces raw material. Control Plane accepts it through the Worker contract, writes bytes via the **byte-store adapter**, writes metadata/hash via Data/PostgreSQL at Transition A. The Worker never writes SoR or “becomes” the store. Future remote transfer is the same ingest path; protocol remains unchosen (Decision 005).

**Streaming / large binaries:** Adapter concern. PostgreSQL is not required to stream blobs.

**Backup:** SoR backup is Decision 003 (implementation open). Byte-store backup is separate and may lag; missing bytes must not be “repaired” by deleting Evidence.

---

## Constraints

1. **Metadata/reference/provenance/integrity in PostgreSQL.** Bytes elsewhere (first: local FS adapter).
2. **Byte-store abstraction exists now** as a Data/Platform capability. **Product does not.**
3. **Identity ≠ location.** Relocating bytes does not change Artifact id.
4. **Byte loss ≠ truth loss.** Evidence/Finding/Approval remain. Availability of raw material may degrade.
5. **Artifact ≠ Evidence.** Bytes and attachments never skip Transition B.
6. **No object-storage product in this decision.**
7. **Local filesystem is the first adapter, not production architecture** and not a Domain path contract.
8. **Windows/WSL paths must not leak into Core/Research contracts.**
9. **Workers (including remote later) do not gain authority by shipping bytes.**
10. **In-place mutation of bytes for an existing identity is forbidden.**
11. **Retention/deletion policy is not the bucket/FS lifecycle UI.**
12. **Research Memory is not the byte store.**

---

## First implementation / future evolution

**First implementation:** Control Plane uses a byte-store **port**. Adapter writes/reads a local filesystem. PostgreSQL stores id, provenance, hash, opaque locator, lifecycle. Tests may use a temp directory adapter. No S3/MinIO required.

**Future:** Same port; object/blob adapter if size, remote Workers, or backup/topology require it. Hybrid size-split remains unselected unless a later decision justifies it.

---

## Strongest alternatives (not selected)

- **Strongest single-store alternative:** PostgreSQL bytes — rejected as default dump.
- **Strongest local-ops alternative:** filesystem-as-contract — rejected as architecture.
- **Strongest scale alternative:** object store in v1 — premature product.

---

## Revisit triggers

- Artifact volume or size makes local FS backup/ops painful **as observed**
- Remote Workers make a local disk adapter insufficient (still the same port)
- Need for multi-host byte access that is not “Worker uploads to Control Plane”
- Integrity/hash verification incidents
- Retention/deletion cannot be executed safely on FS
- Pressure to put blobs back into PostgreSQL (treat as a smell, not a silent revert)

---

## Open questions

- Exact hash algorithm
- Filesystem directory layout (adapter-private)
- Object product when triggered
- Cross-WSL copy mechanism (Worker contract, not Domain)
- Dedup policy
- Byte-store backup/restore implementation

---

## Confidence

**MEDIUM**

The split (SoR metadata/hash vs replaceable bytes) is required by Decisions 002/003 and the domain model. Filesystem-first matches staged local deployment without selecting S3. Confidence is not HIGH because hash algorithm, WSL transfer, and backup of bytes are unchosen, and a leaky locator could still freeze Windows paths.

---

# Decision 007 — Cache / Ephemeral State Strategy

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 003 (PostgreSQL SoR); Decision 004 (orchestration state ≠ domain truth; orchestration product deferred); Decision 005 (local-first Workers)

This decision selects whether the first implementation needs a **dedicated cache**, and what ephemeral state is allowed.

It does **not** select Redis, Memcached, key-value products, CDN, ORM query-cache settings, or a frontend cache.

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**No dedicated cache product and no cache Platform abstraction in the first implementation.**

**Answer:** A separate cache product is **not** required for the first implementation.

| Kind | Allowed in v1? |
|---|---|
| Dedicated cache product (Redis-class) | **No** |
| Cache port/abstraction as a Platform capability | **Not yet** — would invite a product-shaped hole |
| In-process, recomputable, process-local memoization / request scratch | **Yes**, if loss cannot change authorization, budget, Evidence, Finding, Approval, or Candidate lifecycle |
| PostgreSQL as a “cache” | **No** — SoR is not an ephemeral store; orchestration coordination records are Decision 004, not cache |
| Distributed cache from the start | **No** |

Cache / ephemeral state is **never** authoritative for: authorization, scope, budget, Evidence, Finding, Approval, Candidate lifecycle, Research Memory truth, or WorkerResult history.

If cache or in-process memory is lost: **authoritative domain state must remain** in PostgreSQL. Loss must not be a correctness incident.

---

## Why this decision exists

Default is not to add infrastructure. First implementation is single-developer, local Control Plane, local PostgreSQL, mixed local/Kali Workers (Decisions 005/010). There is no measured read-latency, session-fan-out, or multi-Control-Plane problem that a cache would solve.

A cache that stores “allowed scope” or “remaining budget” becomes a second SoR. Decision 002 already forbids sneaking a second SoR into a “cache.”

Decision 004 already separated **orchestration state** (timers, retries, waits) from domain truth. That is not Redis. Do not re-home it here.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Cache ≠ SoR | Cache miss/loss cannot drop Program, Approval, Evidence, Budget authority, etc. |
| No authz/budget cache-as-truth | Serving an allow/deny or remaining budget from cache as authority fails |
| Rebuildable / recomputable | Anything cached must be reconstructible from SoR or is disposable |
| No premature distributed cache | Not justified by current topology |
| Orchestration ≠ cache | Decision 004 coordination is not this decision |

### Candidate results

| Candidate | Stage 1 | Note |
|---|---|---|
| **1. No dedicated cache in v1** | **Pass** | SoR + Worker contract suffice. Selected |
| **2. In-process memory cache** | **Pass if strictly ephemeral** | Allowed as process-local acceleration, not as a product strategy |
| **3. PostgreSQL-backed ephemeral state** | **Fail as cache strategy** | Pollutes SoR or creates unofficial orchestration tables. Use Decision 004 for coordination |
| **4. Cache abstraction, no product** | **Pass later, not now** | A port without a need becomes Redis-shaped. Add when a trigger exists |
| **5. Distributed cache from start** | **Fail v1 fit** | Extra consistency, invalidation, ops. Premature distribution |

---

## Candidate evaluations

### 1. No dedicated cache (selected)

Correctness-preserving default. Local PostgreSQL and in-process Control Plane do not need a side cache for the first Evidence/FindingProposal loop. Invalidation complexity stays zero.

### 2. In-process ephemeral

Acceptable for: memoizing **recomputable** derived views, request-scoped scratch, test fixtures, maybe **recomputable** rate-limit counters that fail closed (deny/retry) rather than fail open.

Unacceptable for: authorization decisions, remaining budget, Evidence, “is this Finding accepted,” WorkerResult history, Research Memory.

Multi-process: in-process memory is **not** shared. That is fine until a revisit trigger says shared ephemeral is needed — then design a cache **port**, still not necessarily a product, and still not truth.

### 3. PostgreSQL as ephemeral cache

Looks convenient; becomes undeletable “cache tables” next to Approval. Mixing TTL rows with immutable Evidence is a schema and ops hazard. Rejected as cache strategy.

### 4. Cache abstraction now, product later

Right *shape* if we already knew we would cache. We do not. Introducing the port now is premature infrastructure of another kind.

### 5. Distributed cache from start

No multi-node Control Plane. Remote Workers (future) still must not read budget/authz from Redis. Rejected.

---

## Comparison matrix (project fit)

**NO** = no dedicated cache. **MEM** = in-process as the *strategy*. **PG** = PostgreSQL ephemeral. **ABS** = cache port now. **DIST** = distributed cache now.

| # | Criterion | NO | MEM | PG | ABS | DIST |
|---|---|---:|---:|---:|---:|---:|
| 1 | correctness | 5 | 4 | 2 | 4 | 2 |
| 2 | truth-boundary clarity | 5 | 4 | 2 | 4 | 2 |
| 3 | local simplicity | 5 | 5 | 3 | 3 | 1 |
| 4 | single-developer ops | 5 | 5 | 3 | 3 | 1 |
| 5 | portability | 5 | 5 | 4 | 4 | 3 |
| 6 | Windows/Linux compatibility | 5 | 5 | 5 | 5 | 3 |
| 7 | Kali/WSL integration | 5 | 5 | 4 | 4 | 2 |
| 8 | remote Worker future | 4 | 3 | 3 | 4 | 3 |
| 9 | failure recovery | 5 | 4 | 3 | 4 | 2 |
| 10 | backup/restore implications | 5 | 5 | 3 | 4 | 2 |
| 11 | retention support | 5 | 5 | 2 | 4 | 2 |
| 12 | integrity verification | 5 | 4 | 3 | 4 | 2 |
| 13 | operational burden | 5 | 5 | 3 | 3 | 1 |
| 14 | testability | 5 | 4 | 3 | 4 | 2 |
| 15 | migration path | 4 | 3 | 2 | 5 | 3 |
| 16 | scalability | 3 | 2 | 3 | 4 | 5 |
| 17 | vendor lock-in | 5 | 5 | 4 | 4 | 2 |
| 18 | security boundary | 5 | 4 | 2 | 4 | 2 |
| 19 | rebuildability | 5 | 4 | 2 | 4 | 3 |
| 20 | avoiding premature infrastructure | 5 | 4 | 3 | 3 | 1 |

**NO** wins Stage 2 because there is no first-implementation need. **MEM** is allowed as a *tactic* under NO, not as a competing product strategy.

---

## What cache must never hold (as authority)

- authorization / scope allow-set
- budget remaining / issued limits
- Evidence, Finding, Approval
- Candidate lifecycle
- Research Memory as truth
- WorkerResult authoritative history
- Artifact identity/provenance (that is SoR; bytes are Decision 006)

Stale cache must **not** create a conflict that “wins” against PostgreSQL. If a cache exists later and disagrees, **PostgreSQL wins**; the cache is dropped or rebuilt.

---

## When in-process ephemeral is acceptable

- Process-local
- Recomputable from SoR or obviously disposable
- Restart/loss does not change Core decisions or recorded history
- Never used as the allow/deny or budget remaining
- Not shared with Workers as an authorization channel (Workers get issued, immutable Core decisions)

---

## First implementation / future evolution

**First implementation:** No Redis-class product. No cache port. Optional in-process memoization under the constraints above.

**Future:** Revisit a **cache abstraction** (still not automatically a product) when triggers fire. Distributed cache only if topology is actually multi-node **and** the data is non-authoritative.

Remote Workers do **not** by themselves require a distributed cache. They require the Worker contract (Decision 005) and Core-issued authorization.

---

## Constraints

1. **No dedicated cache product in v1.**
2. **No cache Platform port until a revisit trigger.**
3. **Cache/ephemeral ≠ domain truth.** Loss ≠ correctness loss.
4. **Do not cache authorization or budget as authority.**
5. **Do not use PostgreSQL as a TTL cache.**
6. **Do not treat Decision 004 coordination tables as a general cache.**
7. **Workers must not read a cache instead of Core.**
8. **Python/in-process dicts are not an architecture contract.**

---

## Revisit triggers

- Measured Control Plane read latency against PostgreSQL that indexing/schema cannot fix
- Multiple Control Plane processes needing **non-authoritative** shared ephemeral state
- Rate-limit / memoization that is unsafe to keep process-local **and** still fail-closed
- Phase B/C topology (Decision 010) with a concrete shared-ephemeral need — still not authz truth
- Discovering that in-process memoization cached a Core decision (remove it; do not “fix” by adding Redis)

---

## Open questions

- Whether a cache **port** is added at first trigger (product still optional)
- Which product if any (not chosen)
- Rate-limit implementation (must fail closed; not chosen)

---

## Confidence

**MEDIUM**

No dedicated cache is the only v1 choice that avoids a second SoR and extra ops without a demonstrated need. Confidence is not HIGH because later multi-process or latency triggers are plausible, and sloppy in-process memoization could still cache budget/authz if undisciplined.

---

## Self-audit (Decisions 006 and 007)

| Forbidden reading | Status |
|---|---|
| PostgreSQL became an artifact byte dump | **No.** Bytes go to a replaceable adapter; PG holds metadata/hash |
| Filesystem became domain truth | **No.** First adapter only; identity ≠ location |
| Object storage selected prematurely | **No.** Product deferred |
| Byte loss deletes Evidence/Finding truth | **No.** SoR remains; bytes are availability |
| Artifact automatically became Evidence | **No.** Transition B still required |
| Cache became authorization truth | **No.** Dedicated cache not selected; authz cache forbidden |
| Cache became budget authority | **Forbidden.** |
| Cache loss equals correctness loss | **No.** Loss must be disposable |
| Distributed cache selected unnecessarily | **No.** |
| Local filesystem became permanent production constraint | **No.** Adapter, not architecture |
| Windows path semantics leaked into architecture | **Forbidden** in Domain/Core contracts |
| Remote Worker made mandatory | **No.** |
| Product became architecture contract | **No.** Ports exist; S3/Redis not chosen |

**FINAL STATUS: PASS**

---

# Decision 008 — Model Abstraction / Provider Strategy

**Status:** ACCEPT WITH CONSTRAINTS (abstraction) / DEFER (provider product)  
**Date:** 2026-08-16  
**Depends on:** Decision 001 (Python primary; Core/Research no provider SDKs); Decision 002 (Research Memory is not SoR)

This decision selects how **model calls** enter Research OS: the port, replaceability, and whether v1 routes across many models.

It does **not** select:

- OpenAI, Anthropic, Google, Azure, Ollama, or any other provider product
- a model id or model family as architecture
- LangChain, LlamaIndex, or any model framework
- an embedding provider (Decision 009)
- Strix as the model layer

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**Single primary provider (unchosen) + replaceable ModelPort / ModelAdapter + routing-ready contract. True multi-provider and live multi-model routing only when needed.**

| Piece | v1 |
|---|---|
| **Abstraction** | Language-neutral **ModelPort**. Concrete **ModelAdapter** in Integrations. Core and Research **do not** import provider SDKs |
| **First implementation** | One primary provider adapter, one default model (both **unchosen** as products). Structured proposal in, structured proposal out |
| **Provider product** | **DEFER** |
| **Routing** | **Contract ready, not live.** v1 does **not** run a real cheap/medium/strong/verifier mesh. Roles exist as **capability metadata** so routing can be added later |

Model output is always **UNTRUSTED STRUCTURED PROPOSAL**. It cannot grant scope, authorization, or budget; cannot create Evidence; cannot accept a Finding; cannot execute tools.

Strix reasoning output, if Strix is used at all, follows the **same** rule. Strix is an optional Integration, not the ModelPort owner and not Research OS.

---

## Why this decision exists

`TECHNICAL_REQUIREMENTS.md`: providers stay replaceable; model output is untrusted; cost/budget observable; secrets out of model context where possible; prompt/context provenance possible; preferred ability to **route** cheaper vs stronger models later. None of that chooses a vendor.

PROJECT_STRUCTURE.md: Core must not host model-specific logic; Core and Research must not import concrete Integrations; changing a model/provider must not break the domain.

Putting a provider SDK in Research would lock the control plane to one vendor and treat SDK types as domain types. Building a full router on day one would be premature complexity. Deferring the **port** would make the first adapter a permanent architecture.

---

## Model roles (capability metadata, not v1 product matrix)

These are **jobs** a later router may assign. v1 does not require a distinct model for each:

- cheap classification
- medium reasoning
- strong reasoning
- verification
- summarization
- structured proposal generation

**Deterministic / non-LLM work first:** lookups, lifecycle, authorization, and SoR reads are not model tasks. A “router” that sends Program/Asset queries to an LLM is a design failure, not routing.

---

## Routing answer

**v1 must not perform real multi-model routing.** The ModelPort is **routing-ready** (model id, role hint, timeout, retry, cancel, cost/token accounting, correlation, capability metadata). The first implementation calls **one** configured adapter/model.

Live routing (cheap vs strong vs verifier) is a later decision when cost, quality, or verification needs are measured.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Untrusted output | Model text is never authorization, Evidence, Finding, or fact |
| No SDK in Core/Research | Adapters live in Integrations |
| Replaceability | Swapping provider must not change Domain/Core |
| Secrets isolation | Provider keys must not be required in LLM context or Domain records |
| Auditability | Model calls correlatable: run, model id/version, tokens/cost, prompt/context provenance as records/references — not conversation-history-as-SoR |
| Strix ≠ architecture | Optional adapter; same untrusted-proposal path |
| Language-neutral contract | Python does not force a Python-only LLM framework |

### Strategy results

Multiple strategies can call a model. Direct-in-Research cannot pass.

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. Single provider directly in Research** | **Fail** | SDK and vendor types in Research. Forbidden |
| **2. Thin provider abstraction** | **Pass** | Replaceable. Weaker on designed-in routing/cost/role metadata |
| **3. Full model-router abstraction in v1** | **Pass as a later shape** | Live multi-model routing now is Stage 2 premature complexity |
| **4. Multi-provider from day one** | **Pass as capability, fail v1 fit** | No demonstrated need; ops and test matrix explode |
| **5. One primary + replaceable adapter + routing-ready** | **Pass** | Selected. Port now; product deferred; routing later |

---

## Candidate evaluations

**1. Direct in Research** — fastest demo, architecture break. Rejected.

**2. Thin abstraction** — minimum replaceability. Risk: a single `complete(prompt)` with no model id, cost, or provenance, so routing never fits. Not selected as the whole strategy; the selected port is thin **plus** those fields.

**3. Router in v1** — matches preferred “cheaper vs stronger” too early. Extra failure modes, eval cost, and fake sophistication. Not selected for first implementation.

**4. Multi-provider day one** — replaceability theater. Two SDKs without a need. Rejected for v1.

**5. Primary + adapter + routing-ready** — selected. One adapter to ship the first loop; contract already has correlation, timeout, retry, cancellation where possible, structured outputs, cost/token accounting, model id/version, capability metadata, prompt/context provenance, secret isolation.

---

## Comparison matrix (project fit)

**DR** = direct in Research. **TH** = thin only. **RT** = live router v1. **MP** = multi-provider v1. **PR** = primary + port + routing-ready (selected).

| # | Criterion | DR | TH | RT | MP | PR |
|---|---|---:|---:|---:|---:|---:|
| 1 | correctness | 1 | 4 | 4 | 4 | 5 |
| 2 | provider lock-in risk | 1 | 4 | 4 | 3 | 5 |
| 3 | Core/Research boundary cleanliness | 1 | 4 | 4 | 4 | 5 |
| 4 | structured-output support | 3 | 4 | 4 | 4 | 5 |
| 5 | observability | 2 | 3 | 4 | 4 | 5 |
| 6 | reproducibility | 2 | 3 | 3 | 3 | 4 |
| 7 | cost control | 2 | 3 | 4 | 3 | 4 |
| 8 | model version traceability | 2 | 3 | 4 | 4 | 5 |
| 9 | secret isolation | 2 | 4 | 4 | 3 | 5 |
| 10 | testability | 2 | 4 | 3 | 2 | 5 |
| 11 | single-developer simplicity | 4 | 4 | 2 | 1 | 4 |
| 12 | local development | 3 | 4 | 2 | 2 | 4 |
| 13 | future routing | 1 | 2 | 5 | 4 | 5 |
| 14 | multi-provider evolution | 1 | 3 | 4 | 5 | 5 |
| 15–19 | retrieval / vector criteria | — | — | — | — | — |
| 20 | operational complexity | 4 | 4 | 2 | 1 | 4 |
| 21 | premature infrastructure risk | 3 | 4 | 2 | 1 | 5 |

Rows 15–19 belong to Decision 009; model strategy must not pretend to be Research Memory.

---

## Constraints

1. **ModelPort is the only way Research obtains model completions.** Core does not call providers and does not host model-specific logic.
2. **Adapters in Integrations.** Core/Research do not import SDKs or Strix.
3. **Output = UNTRUSTED STRUCTURED PROPOSAL.** Not fact, Evidence, authorization, scope, budget change, Finding acceptance, or tool authority.
4. **Provider product deferred.** Configuring one adapter later does not make that vendor the architecture.
5. **v1: one adapter, one default model.** No live multi-model mesh.
6. **Routing-ready fields required on the contract:** model id/version, optional role hint, correlation id, timeout, retry policy, cancellation where possible, token/cost accounting, structured output, capability metadata, prompt/context provenance references.
7. **Secrets stay out of model context** where there is an alternative; never in Domain records as prompt stuffing of keys.
8. **Model/tool budget observability** is not the same as ResearchRun Budget authority. The model cannot raise Core-issued execution budget.
9. **Strix is not the ModelPort.** If used as reasoning runtime: untrusted proposal → Research validation → Core-controlled execution. If used as tool runtime: Worker + WorkerResult after Core authorization.
10. **No LLM framework as architecture.**
11. **Conversation history is not Research Memory and not SoR.**

---

## Revisit triggers

- Measured cost/quality split that justifies cheap vs strong routing
- Need for an independent verifier model
- Primary provider unavailability, policy, or lock-in pain
- Structured-output or timeout/retry failures that a second adapter would actually fix
- Strix (or any runtime) starting to be imported by Research (remove the import; do not “standardize” it)

---

## Open questions

- Which provider/model is configured first
- Schema of structured proposal types (domain-neutral vs Research DTOs — not a provider SDK)
- How prompt/context blobs are stored (SoR references vs artifact bytes — Decision 006 if large)
- Exact retry/cancel implementation

---

## Confidence

**MEDIUM**

The port is required by Core/Research boundaries. Deferring the vendor avoids a false lock-in. Skipping live routing avoids fashion. Confidence is not HIGH because the first adapter is still unchosen and a leaky port could still look like an OpenAI client.

---

# Decision 009 — Semantic Retrieval / Vector Strategy

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 002 (Research Memory is a rebuildable read model, not SoR); Decision 003 (PostgreSQL SoR); Decision 007 (no cache as truth); Decision 008 (model output untrusted)

This decision selects **how Research Memory retrieves** in v1, and whether a **vector index** exists.

It does **not** select a vector database, pgvector, embedding provider, or RAG framework.

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS — structured-first Research Memory; optional semantic/vector companion later**

| Question | Answer |
|---|---|
| **v1 semantic/vector needed?** | **No** |
| **Exact/structured lookup sufficient for v1?** | **Yes** — Factual and Episodic Memory are SoR records keyed by Program, run, asset, and identity |
| **Retrieval abstraction now?** | **Research Memory already is that abstraction.** No separate VectorPort in v1 |
| **Vector implementation** | **Later**, as a **rebuildable, non-authoritative companion** behind Research Memory — not a second SoR |
| **Vector DB / embedding product** | **Not selected** |

**v1 retrieval:** PostgreSQL **structured and text** lookup, **Program-scoped** (and scope/authorization-aware). No embedding pipeline. No vector index.

Semantic similarity is **not** Evidence, not fact, not authorization, and not Research Memory truth.

---

## Why this decision exists

Research Memory has Factual / Episodic / Procedural categories. It is a **read/retrieval/organization** layer over authoritative records and curated procedural knowledge. It is **not** a truth source (DOMAIN_MODEL.md).

`TECHNICAL_REQUIREMENTS.md`: semantic retrieval is optional later; a vector database is **not** required; search/vector/graph may exist as companions; Research Memory does not require them.

v1 does not have a large procedural corpus or a measured recall failure of SQL/text search. Adding a vector DB “because the system uses AI” would create shadow truth, embedding drift, and cross-program leak surface for no Stage 1 gain.

---

## When semantic retrieval becomes valuable

**Factual / Episodic (v1):** exact and structured lookup is the correct tool (ids, Program, ResearchRun, Asset, timestamps, statuses). Semantic search over Observations is optional later and still not Evidence.

**Procedural:** semantic retrieval becomes valuable when curated methodologies, outcome-linked heuristics, and analyst notes are **large enough** that keyword/SQL recall fails **as observed**. Even then: procedural hits are **hints**, cannot override Core, cannot invent Evidence, cannot create Findings.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Vector ≠ SoR | Index cannot win against PostgreSQL |
| Embedding ≠ truth | Similarity is not Observation, Evidence, or Finding |
| Rebuildable | Any later index rebuilds from SoR (+ curated procedural records with provenance) |
| Program isolation | Default **no** cross-program retrieval |
| Scope filter | Deleted, revoked, out-of-scope records must be excludable using **SoR state**, not the index as authority |
| Provenance | Hits cite source record ids; no anonymous chunks as facts |
| No v1 vector product | Not required to run Research Memory |

### Strategy results

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. No semantic retrieval in v1** | **Pass as the vector slice** | Correct for embeddings. Must not mean “no Research Memory” |
| **2. PostgreSQL text/structured retrieval only** | **Pass — this is v1** | Sufficient for Factual/Episodic |
| **3. Vector in primary DB later** | **Pass as a possible later adapter** | Must not make an extension a domain dependency (Decision 003). Not v1 |
| **4. Dedicated vector companion from start** | **Fail v1 fit** | Premature infrastructure; shadow-truth temptation |
| **5. New VectorPort now, implement later** | **Redundant** | Research Memory is already the retrieval port. A second port invites a vector product |
| **6. Structured-first + optional semantic later** | **Pass** | Selected strategy. v1 = (2). Later semantic = companion behind Research Memory |

---

## Embedding drift, versions, stale data

If a vector companion is added later:

- Store **embedding model id/version** as index provenance, not as domain truth
- **Drift:** change of embedding model ⇒ **rebuild** the companion; do not mix incompatible vectors silently
- **Stale embeddings** cannot override SoR. On conflict, **PostgreSQL wins**; the index is rebuilt or dropped (Decision 002 companion rule)
- Deleted/revoked/out-of-scope: filter at retrieval time from SoR (or drop from index as a derived view). The vector hit is never a grant of scope

Cross-program leakage: retrieval APIs take Program (and must not return another Program’s episodic/factual material by similarity). Default deny.

---

## Comparison matrix (project fit)

**NV** = no retrieval at all. **PG** = PG structured/text only (v1). **VXPG** = vectors in PG from start. **DED** = dedicated vector DB v1. **PORT** = extra VectorPort now. **HY** = structured-first + optional semantic later (selected).

| # | Criterion | NV | PG | VXPG | DED | PORT | HY |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | correctness | 2 | 5 | 3 | 2 | 4 | 5 |
| 2 | provider lock-in risk | 5 | 5 | 3 | 2 | 4 | 5 |
| 3 | Core/Research boundary cleanliness | 3 | 5 | 4 | 3 | 3 | 5 |
| 15 | retrieval correctness | 1 | 5 | 3 | 2 | 4 | 5 |
| 16 | provenance preservation | 2 | 5 | 3 | 2 | 4 | 5 |
| 17 | cross-program isolation | 3 | 5 | 3 | 2 | 4 | 5 |
| 18 | rebuildability | 3 | 5 | 3 | 2 | 4 | 5 |
| 19 | stale-data risk | 5 | 5 | 2 | 2 | 3 | 5 |
| 20 | operational complexity | 5 | 5 | 3 | 1 | 3 | 5 |
| 21 | premature infrastructure risk | 4 | 5 | 2 | 1 | 3 | 5 |
| 10 | testability | 3 | 5 | 3 | 2 | 4 | 5 |
| 11 | single-developer simplicity | 4 | 5 | 3 | 1 | 3 | 5 |
| 12 | local development | 4 | 5 | 3 | 1 | 3 | 5 |

**NV** fails because Research Memory still must retrieve Factual/Episodic from SoR. **HY** is **PG in v1** plus a gated companion path, not a vector install.

---

## Constraints

1. **v1: no vector index, no embedding pipeline, no vector product.**
2. **Research Memory retrieves from PostgreSQL** (structured + text), Program-scoped.
3. **Semantic similarity ≠ Evidence, fact, authorization, or Finding.**
4. **Any later vector index is a rebuildable companion.** PostgreSQL wins conflicts.
5. **Embedding model version is index provenance**, required if/when embeddings exist; embeddings are not SoR.
6. **Cross-program isolation by default.** Similarity must not leak Programs.
7. **Out-of-scope / deleted / revoked records** must be filterable from retrieval using SoR.
8. **No VectorPort parallel to Research Memory** in v1.
9. **pgvector / extension is not selected** and must not become a Domain type.
10. **Model suggestions (Decision 008) are not retrieval truth.**
11. **Cache (Decision 007) is not a semantic index.**

---

## First implementation / future evolution

**v1:** Research Memory = organized reads over SoR (+ curated procedural rows with provenance). Keyword/text search in PostgreSQL is allowed; it is not a vector DB.

**Later:** If procedural/factual recall fails as measured, add semantic retrieval **behind Research Memory**, rebuildable from SoR, with embedding-version provenance and Program/scope filters. Dedicated vector product or in-DB vectors would be a **new** decision.

---

## Revisit triggers

- Measured failure of structured/text recall on a real procedural or episodic corpus
- Analyst workflow that needs similarity **hints** without treating them as Evidence
- Embedding/rebuild cost becoming an actual ops problem (then companion topology, still not truth)
- Cross-program leak in any retrieval path (fix isolation; do not “tune” the index as authority)
- Pressure to put vectors in PostgreSQL as Domain (refuse; adapter only, later decision)

---

## Open questions

- Text-search implementation inside PostgreSQL (not a product decision here)
- Future vector product / embedding model
- Chunking strategy if semantic retrieval is added
- How procedural notes are curated (still not vector)

---

## Confidence

**MEDIUM**

v1 does not need vectors; Research Memory already forbids shadow truth; structured lookup matches Factual/Episodic. Confidence is not HIGH because procedural corpus size is unknown and a later companion will need strict Program filters to avoid leaks.

---

## Self-audit (Decisions 008 and 009)

| Forbidden reading | Status |
|---|---|
| Provider SDK in Core/Research | **Forbidden.** Adapters in Integrations |
| Model output became truth | **No.** Untrusted structured proposal |
| Router unnecessarily complex in v1 | **No.** Routing-ready contract; no live mesh |
| Multi-provider mandatory in v1 | **No.** One adapter; product deferred |
| Vector DB chosen because “AI” | **No.** No vector in v1 |
| Semantic result used as fact/Evidence | **Forbidden.** |
| Vector index became shadow truth | **No index in v1;** later companion cannot win vs SoR |
| Cross-program memory leak designed in | **Default isolation required** |
| Embedding version/provenance forgotten | **Required if/when embeddings exist** |
| Stale vectors override SoR | **Forbidden.** PostgreSQL wins |
| Strix became architecture owner / provider | **No.** Optional Integration; same untrusted path |

**FINAL STATUS: PASS**

---

# Decision 010 — Deployment Model

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 003 (PostgreSQL SoR); Decision 004 (hybrid orchestration, product deferred); Decision 005 (mixed Worker topology, local-first, no mandatory broker)

This decision selects the **first-implementation deployment model** and the **allowed evolution path**.

It does **not** select:

- Docker / Podman / any container runtime
- Kubernetes or any cluster orchestrator
- a cloud provider
- a secrets product
- HA/replication topology
- production hosting

---

## Decision

**FIRST DEPLOYMENT MODEL: ACCEPT WITH CONSTRAINTS — staged**

**Phase A (first working implementation):**

- Windows + Cursor **developer host** (current context, not architecture)
- local PostgreSQL (Decision 003)
- local Control Plane on that host
- Kali/WSL **Worker integration** for tool execution (Decision 005)
- no mandatory containers, Kubernetes, remote services, or distributed broker

**Phase B:**

- same Worker contract
- replaceable local and/or **remote authenticated** Workers
- Control Plane and PostgreSQL location may move only if a later decision says so; Domain/Core contracts do not change

**Phase C:**

- distributed production topology **only if** measured requirements justify it
- still not a Kubernetes decision, still not a container mandate

Windows/Kali/WSL describe **Phase A context**. They are not a permanent architecture constraint.

---

## Why this decision exists

`TECHNICAL_REQUIREMENTS.md` leaves production topology unchosen, prefers local/mock before distributed deployment, and requires easy testing against Kali/WSL **without** making that environment the architecture.

Decision 005 already places Control Plane local and the first tool Worker in Kali/WSL. Deployment must not invent a second topology, must not put Kubernetes under the first loop, and must not encode “runs on WSL” into domain records.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Deployment ≠ domain logic | Program/ResearchRun/WorkerResult do not carry Docker/K8s/WSL as truth |
| Current env ≠ production architecture | Windows/Kali/WSL are Phase A |
| SoR remains PostgreSQL | Deployment does not replace Decision 003 |
| Worker isolation preserved | Phase A still uses out-of-process Workers (Decision 005) |
| No premature cluster | Kubernetes/remote mesh not required to run Phase A |
| Evolution without Domain change | Phase B/C must not rewrite Core/Research contracts |

### Deployment candidate results

| Model | Stage 1 | Note |
|---|---|---|
| **Single local application process** | **Fail as the Worker isolation story** | Can host Control Plane+fakes. Real side-effect Workers in the same process fail Decision 005 isolation |
| **Local multi-process application** | **Pass, incomplete** | Good Control Plane + child Workers. Misses Kali/WSL as the stated first tool env unless mixed |
| **Host + Kali/WSL split as the standing model** | **Pass as Phase A snapshot only** | Accurate today. Fails if it is the *permanent* architecture |
| **Containerized local stack** | **Pass as an optional later packaging** | Not required. Container runtime **not** chosen. Must not become mandatory |
| **Remote distributed services** | **Pass as Phase C capability** | Premature as first model |
| **Kubernetes-style orchestration** | **Not selected; premature** | Capable production class. Not a correctness gate. Not v1 |
| **Staged deployment model** | **Pass** | Phase A = host + local PostgreSQL + local Control Plane + Kali/WSL Worker. B/C are gated evolutions |

---

## Candidate evaluations

**Single local process** — simplest debug for Control Plane; cannot be the Worker execution model.

**Local multi-process** — correct isolation on one OS; insufficient as the *whole* first implementation because security tools are expected on Kali/WSL.

**Host + Kali/WSL split** — correct **Phase A** picture. Wrong as the name of the architecture.

**Containerized local stack** — can wait. Adds operational surface a single developer does not need for the first Evidence/FindingProposal loop. Not forbidden later; not accepted now.

**Remote distributed services** — future Control Plane/Worker/PostgreSQL split. Requires authentication, network untrust, and a later decision. Not first implementation.

**Kubernetes-style** — production scheduler class. Fashionable and premature. Failure isolation and scale are not current requirements.

**Staged** — selected. Records Phase A honestly, forbids treating it as destiny, and ties Phase B to Decision 005’s Worker contract.

---

## Comparison matrix (project fit)

**SP** = single process. **MP** = local multi-process. **HK** = host+Kali as standing model. **CT** = containerized local. **RD** = remote distributed now. **K8** = Kubernetes now. **ST** = staged (selected).

| # | Criterion | SP | MP | HK | CT | RD | K8 | ST |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | Core authority preservation | 3 | 4 | 4 | 4 | 4 | 4 | 5 |
| 2 | Worker isolation boundary | 1 | 5 | 4 | 4 | 5 | 5 | 5 |
| 3 | local development simplicity | 5 | 4 | 3 | 2 | 1 | 1 | 4 |
| 4 | Kali/WSL integration | 1 | 2 | 5 | 3 | 2 | 2 | 5 |
| 5 | remote-worker future | 1 | 3 | 2 | 3 | 5 | 4 | 5 |
| 6 | authentication capability | 2 | 3 | 3 | 3 | 5 | 4 | 4 |
| 7 | cancellation | 3 | 4 | 4 | 4 | 4 | 4 | 4 |
| 8 | retry / duplicate safety | 3 | 4 | 4 | 4 | 3 | 3 | 4 |
| 9 | correlation / auditability | 3 | 4 | 4 | 4 | 4 | 4 | 5 |
| 10 | debugging | 5 | 4 | 3 | 2 | 1 | 1 | 4 |
| 11 | failure isolation | 1 | 5 | 4 | 4 | 5 | 5 | 5 |
| 12 | artifact / result transfer | 4 | 4 | 3 | 3 | 2 | 2 | 4 |
| 13 | operational complexity | 5 | 4 | 3 | 2 | 1 | 1 | 4 |
| 14 | single-developer suitability | 5 | 4 | 4 | 2 | 1 | 1 | 4 |
| 15 | portability | 2 | 4 | 1 | 3 | 4 | 3 | 5 |
| 16 | production evolution | 1 | 3 | 2 | 3 | 4 | 4 | 5 |
| 17 | vendor lock-in | 5 | 5 | 4 | 3 | 2 | 1 | 5 |
| 18 | observability | 3 | 4 | 4 | 4 | 4 | 4 | 4 |
| 19 | security boundary clarity | 2 | 4 | 4 | 3 | 4 | 3 | 5 |
| 20 | local → remote migration | 1 | 3 | 2 | 3 | 5 | 4 | 5 |
| 21 | avoiding premature distribution | 5 | 5 | 4 | 3 | 1 | 1 | 5 |

Staged wins because it is **Host + Kali/WSL split for Phase A** plus an explicit ban on making that split the architecture, plus a gated path to remote Workers without Kubernetes-now.

---

## Constraints

1. **Phase A is local:** developer host Control Plane, local PostgreSQL, Kali/WSL Worker integration, no mandatory broker/containers/K8s.
2. **Windows + Kali/WSL are current context**, not production architecture, not Domain fields, not a language mandate (Decision 001 already).
3. **Deployment topology must not leak into domain logic.** No `environment=wsl` as authorization or Evidence.
4. **Containers are optional later packaging, not a requirement.**
5. **Kubernetes is not selected** and is not implied by “Phase C.”
6. **Secrets product is not selected.**
7. **Phase B remote Workers** use Decision 005’s contract: authenticated identity, still Core-authorized, still untrusted WorkerResult.
8. **Phase C** requires a new recorded decision when distribution is a real requirement, not a preference.
9. **Orchestration product remains deferred** (Decision 004). Deployment must not smuggle Temporal/Celery/K8s-as-orchestrator.
10. **PostgreSQL remains the SoR** wherever it is hosted later; hosting move ≠ product change.

---

## Evolution path (allowed)

```
local Control Plane + local PostgreSQL
→ local child-process Workers + Kali/WSL Worker (Phase A)
→ multiple local Workers
→ remote authenticated Worker(s) (Phase B)
→ distributed worker pool / split services (Phase C, only if justified)
```

Core/Research contracts stay the same across this path. Worker contract stays the same. Transport adapters change.

---

## Revisit triggers

- Phase A host/WSL split blocks a required tool or Control Plane run
- Need to run Control Plane or PostgreSQL off the developer laptop **as a requirement**
- Remote Worker topology is actually adopted (Decision 005 revisit + this Phase B)
- Packaging/reproducibility pain that a **later** container decision might ease (does not auto-select Docker)
- Production HA/scale that a **later** cluster decision might ease (does not auto-select Kubernetes)
- Deployment fields appearing in domain records (fix the leak; do not “standardize” it)

---

## Open questions

- Whether Phase A PostgreSQL runs native-Windows, WSL, or a later container (product remains PostgreSQL; runtime packaging deferred)
- How Control Plane is started on the developer host
- Production hosting, HA, backup implementation (Decision 003 open questions)
- Container/K8s if and when Phase C is real

---

## Confidence

**MEDIUM**

Staged deployment is the only model that tells the truth about Phase A (Windows host + local PostgreSQL + local Control Plane + Kali/WSL Worker) without freezing that picture or jumping to Kubernetes. Confidence is not HIGH because production topology is still unchosen and Phase A packaging (native vs WSL PostgreSQL, how WSL is launched) is unspecified.

---

## Self-audit (Decisions 005 and 010)

| Forbidden reading | Status |
|---|---|
| Windows/Kali became permanent architecture | **No.** Phase A context; portability required; Domain must not store it as truth |
| Remote workers selected prematurely | **No.** Future path only |
| Broker made mandatory | **No.** Explicitly non-mandatory; product not chosen |
| Local process boundary removed | **No.** Side-effect Workers are out-of-process; in-process is fakes only |
| Worker writes PostgreSQL truth | **Forbidden.** WorkerResult ingest is Control Plane/Data |
| Transport became truth source | **No.** Delivery ≠ success ≠ Evidence |
| Authentication confused with authorization | **Separated.** Worker identity/authn ≠ Core authorization |
| Deployment model leaked into domain logic | **Forbidden.** |
| Kubernetes selected prematurely | **No.** Not selected; Phase C is not K8s |
| Containers made mandatory | **No.** |
| Strix defined as a Worker | **No.** Optional Integration used *by* a Worker |
| WSL made mandatory production runtime | **No.** Initial tool-execution location only |

**FINAL STATUS: PASS**

---

# Decision 011 — Frontend / Interface Strategy

**Status:** ACCEPT WITH CONSTRAINTS (strategy) / DEFER (frontend and API framework products)  
**Date:** 2026-08-16  
**Depends on:** Decision 001 (Python primary; Interface is application logic, not Core); Decision 010 (staged deployment); Decision 015 (Human Operator identity; Approval actor)

This decision selects **how humans and external systems talk to Research OS**, and what exists in the first working implementation.

It does **not** select a web framework, CLI framework, desktop toolkit, API framework (FastAPI/Flask/etc.), or a dashboard product. n8n remains an example Integration, not Interface-as-Core.

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS — staged interface**

**PRODUCT: DEFER**

| Phase | Interface surface |
|---|---|
| **A — first working implementation** | Stable **application/API boundary** (language-neutral contracts into Research/Core). **Minimal CLI / operator tooling**. **Minimal Human Review interface** sufficient to present FindingProposal and record a decision through Core Approval. **Not** a full web dashboard |
| **B** | Web dashboard for the listed operator capabilities |
| **C** | Richer operational/research visualization |

**Answer:** A **full web dashboard is not required** for the first working implementation.

Interface ≠ business logic. Interface cannot bypass Core, cannot promote Candidate → Finding, does not own Approval semantics, does not own Research logic, and must not write PostgreSQL **authority** by going around Core/Data.

Human Approval path:

```
Interface → approval request → Core Approval semantics → persisted Approval
```

FindingProposal APPROVED remains the domain view of that Core record (DOMAIN_MODEL.md).

---

## Why this decision exists

PROJECT_STRUCTURE.md: Interface contains API, dashboard, CLI, human review, approval screens, reporting. It must not own business logic or approval semantics.

Human Review is **permanent**. CLI-only review of Evidence/Artifacts (screenshots, captures) is a poor fit as the **only** long-term surface, but a **full** dashboard on day one is frontend complexity a single developer does not need to finish the first authorized loop.

An **API/application boundary** is required immediately so CLI, a later dashboard, tests, and future automations (n8n as **Integration**, not policy owner) share one Core-gated path.

Windows + Cursor is Phase A **context** (Decision 010), not a reason to pick Electron or a JS SPA now.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Interface cannot bypass Core | No “admin SQL” as Approval or Finding |
| Interface does not own Approval | UI/CLI submits a request; Core records |
| No direct SoR authority writes | PostgreSQL writes go through Data after Core/Research rules |
| Human Review is possible in v1 | Finding cannot be created without it |
| API/application boundary exists | Surfaces are replaceable; n8n cannot become Core |
| No framework required to start | Product deferred |

### Strategy results

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. CLI-first only** | **Pass weakly** | Fast. Human Review of artifacts is painful as the standing model |
| **2. API-first only** | **Pass as a boundary, fail as the only human surface** | Automation-ready; operators still need CLI or review UI |
| **3. Web dashboard first** | **Pass later** | Best long-term Human Review ergonomics. Premature full product/framework |
| **4. API + CLI** | **Pass** | Solid Phase A if Human Review is explicitly included in the CLI/minimal surface |
| **5. API + minimal web dashboard** | **Pass** | Reasonable Phase A/B blur. Full dashboard still not mandatory in A |
| **6. API + web dashboard + CLI at once** | **Pass as Phase C shape** | Too much v1 surface area |
| **7. Desktop application** | **Fail v1 fit** | Extra stack; freezes OS/desktop as architecture |
| **8. Staged interface** | **Pass** | Selected: API boundary + minimal CLI + minimal review in A; dashboard later |

---

## Candidate evaluations

**CLI-first** — best single-developer speed and debugging. Worst standing Human Review for screenshots/HTTP captures. Acceptable as **Phase A tooling**, not as “Interface = CLI forever.”

**API-first** — correct **boundary**. Not sufficient alone for Human Review.

**Web dashboard first** — answers the capability list in one UI. Forces a frontend product/framework before the API contract is stable. Not selected for v1.

**API + CLI** — close to Phase A. Selected staged model **includes** this plus an explicit **minimal Human Review** surface (CLI prompts and/or a tiny local review page). That surface is not a dashboard product.

**API + minimal web** — allowed as a Phase A *implementation* of “minimal Human Review” without selecting React/Vue. Still not “full dashboard required.”

**API + dashboard + CLI together** — the long-term Interface contents list. Not the first implementation.

**Desktop** — unnecessary packaging; not chosen.

**Staged** — selected. Matches Decision 010’s gated evolution: contracts first, richness later.

---

## Comparison matrix (project fit)

**CLI** = CLI-only. **API** = API-only. **WEB** = dashboard-first. **AC** = API+CLI with no review UX. **AM** = API+minimal web. **ALL** = all three at once. **DESK** = desktop. **ST** = staged (selected).

| Criterion | CLI | API | WEB | AC | AM | ALL | DESK | ST |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single-developer speed | 5 | 4 | 2 | 4 | 3 | 1 | 2 | 5 |
| Human Review ergonomics | 2 | 1 | 5 | 2 | 4 | 5 | 4 | 4 |
| operational visibility | 3 | 3 | 5 | 3 | 4 | 5 | 3 | 4 |
| research traceability | 3 | 4 | 5 | 4 | 4 | 5 | 3 | 4 |
| approval UX | 2 | 1 | 5 | 2 | 4 | 5 | 4 | 4 |
| API stability | 2 | 5 | 3 | 5 | 5 | 4 | 3 | 5 |
| automation / future n8n | 2 | 5 | 3 | 5 | 5 | 5 | 2 | 5 |
| CLI usefulness | 5 | 2 | 1 | 5 | 3 | 5 | 2 | 5 |
| debugging | 5 | 4 | 2 | 5 | 3 | 2 | 2 | 5 |
| local Windows development | 5 | 4 | 3 | 4 | 3 | 2 | 2 | 4 |
| future hosted deployment | 2 | 5 | 4 | 5 | 5 | 5 | 1 | 5 |
| vendor lock-in | 5 | 5 | 3 | 5 | 4 | 3 | 2 | 5 |
| frontend complexity | 5 | 5 | 2 | 5 | 3 | 1 | 2 | 5 |
| testability | 4 | 5 | 3 | 5 | 4 | 3 | 2 | 5 |

Staged wins because Phase A is **API + CLI + minimal review** (high speed, Core-gated) without locking a dashboard framework.

---

## Phase A capability coverage (conceptual)

All listed operator capabilities must be **reachable through the application/API boundary** (so they are not trapped in a future SPA). Phase A **CLI/minimal review** must cover at least: start/stop ResearchRun (Core-authorized), Human Review / Approval request, and enough read-back of FindingProposal, Evidence, Budget, Worker status, and Audit history to decide. Rich Asset/Hypothesis/graph visualization waits for B/C.

---

## Constraints

1. **Interface is not Core, Research, or Data.** No policy, no Finding creation, no Approval semantics ownership.
2. **No PostgreSQL authority writes from UI/CLI.**
3. **Approval: Interface request → Core → persisted Approval.** Operator identity from Decision 015.
4. **Full web dashboard is not a v1 requirement.**
5. **Frontend framework and API framework products are deferred.**
6. **n8n/external automation**, if used, is an Integration/API **client**. It cannot own Core logic.
7. **Windows is not a reason to choose a desktop app.**
8. **API/application contracts stay language-neutral** where they cross process boundaries (Workers already are).
9. **AI recommendation and final judgment stay separate in the review UI.**

---

## Revisit triggers

- Human Review on CLI/minimal surface blocks real Finding decisions (then Phase B dashboard, still no implied React)
- External automation needs a stable API that is not yet documented (fix the boundary; do not put logic in n8n)
- Operators need operational visualization beyond logs (Decision 012 + Phase B)
- Pressure to write Findings from a UI shortcut (refuse)

---

## Open questions

- Whether Phase A “minimal Human Review” is CLI, a tiny local page, or both (not a framework choice)
- API transport (HTTP vs in-process for single process Control Plane — not a FastAPI decision)
- Dashboard stack when Phase B starts

---

## Confidence

**MEDIUM**

Staged Interface matches Human Review as permanent without a v1 SPA. Confidence is not HIGH because “minimal review surface” could be under-built (CLI-only artifact review) or over-built (stealth dashboard).

---

# Decision 012 — Observability Strategy

**Status:** ACCEPT WITH CONSTRAINTS (abstraction) / DEFER (logging/metrics/tracing products)  
**Date:** 2026-08-16  
**Depends on:** Decision 003 (AuditEvent in PostgreSQL SoR); Decision 004 (orchestration ≠ truth); Decision 005 (correlation id on Worker contract); Decision 008 (model id/cost/provenance on ModelPort); Decision 013 (secret values never in logs)

This decision selects how **operational visibility** is produced, and how it stays distinct from **AuditEvent** and domain truth.

It does **not** select a logging vendor, metrics backend, tracing backend, APM, or “observability platform.”

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**ObservabilityPort / instrumentation conventions:** structured **logs first**; **metrics and tracing capability designed in**; **concrete observability platform later**.

**PRODUCT: DEFER**

| Signal | What it is | What it is not |
|---|---|---|
| **AuditEvent** | Authoritative reconstructive **security/decision** history in PostgreSQL | Not logs. Not Evidence. Not AuthorizationSource |
| **Logs** | Structured **diagnostics** | Not Audit truth. Not WorkerResult truth |
| **Metrics** | Aggregate **operational / research / security** insight | Not domain state, Finding, or Evidence |
| **Traces** | Causal **execution path** visibility | Not AuditEvent, Evidence, or SoR |

If logs or a tracing backend are deleted: **AuditEvent, Evidence, Finding, Approval remain.** Metric drift must not change domain correctness.

**v1 does not install a full observability platform.**

---

## Why this decision exists

Auditability is a **hard** requirement. Observability is **preferred visibility** of operation (`TECHNICAL_REQUIREMENTS.md` lists events; no product chosen). Collapsing them would make ELK/Datadog the SoR, or would skip AuditEvent because “we have logs.”

Workers may be non-Python (Decision 001/005). Correlation must be **language-neutral**. Remote Workers later must still join the same run/experiment/worker ids.

Model cost/provenance must be observable (Decision 008) without dumping secrets or full prompts by default (Decision 013).

---

## Minimum visible events

These must be **observable** (log and, where they are control decisions, **also** AuditEvent in SoR). Observability does not replace the AuditEvent.

ResearchRun start/end; authorization decision; scope decision; budget issue/use/exhaustion; Experiment transition; Worker dispatch; Worker completion/failure; retry; timeout; cancellation; redirect/re-authorization; WorkerResult ingestion; Transition A; Evidence admission; Candidate transition; Verification; FindingProposal; Human Review; Approval; Finding creation; model call (id/version, adapter identity, correlation, role hint, token/cost, latency, retry, timeout, context provenance **reference**); artifact creation; snapshot/change generation; **secret reference use without secret value**; external integration failures.

---

## Logging (v1)

- Structured
- Correlation id; ResearchRun / Experiment / Worker relationship reconstructible
- **No secret values**
- Raw sensitive payloads **not** logged by default
- Model prompts/responses: **configurable redaction**; default is **provenance reference**, not full body
- Worker output logs are **not** truth (WorkerResult ingest + Transition A are)

---

## Metrics (designed in; product deferred)

**Operational:** run/worker duration, retries, failures, wait time, model latency, storage latency.

**Research:** hypotheses created/tested, hypothesis success rate, Candidate conversion, Finding conversion, false-positive rate, duplicate rate, time-to-first-valid-finding, cost per accepted Finding, accepted findings per request volume, verification rejection rate, chain conversion rate.

**Security:** denied execution, out-of-scope block, approval-required, budget-exhaustion, re-authorization counts.

v1 may emit counters/timers through ObservabilityPort **without** Prometheus/etc. Research metrics are **aggregates over SoR**, not a second Candidate ledger.

---

## Tracing (designed in; product deferred)

Intended chain:

Operator → ResearchRun → Research → Core authorization → orchestration → Worker → WorkerResult → Transition A → Evidence admission → Candidate/Verification → Approval/Finding.

Traces **do not** replace AuditEvent. No Jaeger/OTel backend is required in v1; **span/correlation fields** should exist so a backend can be attached later. Language-neutral Worker correlation is mandatory now (Decision 005).

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| AuditEvent remains SoR | Logs cannot be the reconstructive authority |
| Secrets never in logs | Decision 013 |
| Correlation present | Run/experiment/worker/model joinable |
| Observability ≠ Evidence | Success in a trace is not Finding |
| No vendor required for v1 | Platform later |
| Model cost/provenance visible | Without default full prompts |

### Strategy results

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. Logs only** | **Pass as v1 export, fail as the whole strategy** | Diagnostics only; metrics/traces would never fit |
| **2. Logs + metrics products now** | **Pass later** | Premature backends |
| **3. Logs + tracing products now** | **Pass later** | Same |
| **4. Logs + metrics + traces products now** | **Fail v1 fit** | Full platform too early |
| **5. ObservabilityPort; logs first; metrics/traces designed in** | **Pass** | Selected |
| **6. Full observability platform day one** | **Fail v1 fit** | Vendor becomes architecture |

---

## Comparison matrix (project fit)

**LG** = logs only as strategy. **LM** = logs+metrics products. **LT** = logs+tracing products. **ALL** = three products now. **PORT** = port + logs first (selected). **PLT** = full platform v1.

| Criterion | LG | LM | LT | ALL | PORT | PLT |
|---|---:|---:|---:|---:|---:|---:|
| audit vs diagnostics clarity | 3 | 3 | 3 | 2 | 5 | 2 |
| local dev simplicity | 5 | 3 | 3 | 2 | 5 | 1 |
| production evolution | 2 | 3 | 3 | 4 | 5 | 4 |
| Worker correlation | 3 | 3 | 4 | 4 | 5 | 4 |
| remote Worker future | 2 | 3 | 4 | 4 | 5 | 4 |
| operational burden | 5 | 3 | 3 | 2 | 5 | 1 |
| vendor lock-in | 5 | 3 | 3 | 2 | 5 | 1 |
| testability | 5 | 3 | 3 | 2 | 5 | 2 |
| model cost/provenance | 3 | 4 | 3 | 4 | 5 | 4 |
| premature infrastructure | 4 | 3 | 3 | 2 | 5 | 1 |

---

## Constraints

1. **AuditEvent in PostgreSQL is authoritative audit.** Logs/metrics/traces are not.
2. **Log loss must not erase Approval/Evidence/Finding/authorization history.**
3. **No secret values, no default full prompts/responses, no default raw sensitive payloads.**
4. **Worker logs ≠ WorkerResult ≠ Observation ≠ Evidence.**
5. **Metrics are not Candidate/Finding truth.**
6. **Traces are not AuditEvent.**
7. **ObservabilityPort exists; logging/metrics/tracing vendors deferred.**
8. **Correlation ids are contract-level** (Control Plane, Worker, model call), not vendor-trace-id as Domain.
9. **Secret reference use may be logged; values must not.**
10. **Python logging libraries are not the architecture**; Workers in other languages must still correlate.

---

## First implementation / future

**v1:** Structured logs to local stdout/file with required fields; AuditEvent written for control decisions; ObservabilityPort stubs for metrics/traces (or in-process counters) without a platform.

**Later:** Attach a self-hostable or hosted backend **behind the port** when production evolution (Decision 010 Phase C or operational pain) justifies it. Not a Domain change.

---

## Revisit triggers

- Cannot reconstruct a run from AuditEvent + logs (fix instrumentation; do not make logs SoR)
- Need dashboards of operational/research/security aggregates (metrics backend **behind the port**)
- Cross-process traces required for remote Workers
- Secrets or full prompts appearing in logs (incident; tighten redaction)
- Vendor SDK in Core/Research (remove it)

---

## Open questions

- Log destination (stderr vs file) as adapter
- Metrics/tracing products when triggered
- Prompt retention policy for debugging (default off)

---

## Confidence

**MEDIUM**

Separating AuditEvent from logs is required. Structured logs first matches single-developer Phase A. Confidence is not HIGH because “designed-in tracing” can be forgotten until remote Workers, and research metrics can be mistaken for SoR if undisciplined.

---

## Self-audit (Decisions 011 and 012)

| Forbidden reading | Status |
|---|---|
| UI owns business logic | **Forbidden** |
| UI bypasses Core | **Forbidden** |
| UI writes PostgreSQL authority directly | **Forbidden** |
| Full dashboard mandatory in v1 | **No** |
| CLI-only forever (Human Review ignored) | **No**; Phase A includes minimal review surface |
| Frontend framework chosen | **Deferred** |
| n8n/Interface owns Core | **No**; client of API only |
| Logs replace AuditEvent | **No** |
| Traces are truth | **No** |
| Metrics are domain state | **No** |
| Secrets logged | **Forbidden** |
| Full prompts stored by default | **No** |
| Observability vendor is architecture | **Product deferred** |
| Worker correlation missing | **Required on contract** |
| Model cost/provenance invisible | **Required on ModelPort + logs** |
| Full observability platform in v1 | **No** |

**FINAL STATUS: PASS**

---

# Decision 013 — Secrets Management Strategy

**Status:** ACCEPT WITH CONSTRAINTS (abstraction) / DEFER (product)  
**Date:** 2026-08-16  
**Depends on:** Decision 005 (Workers less trusted than Control Plane); Decision 008 (secrets out of model context); Decision 010 (staged local-first)

This decision selects how **credentials and other secrets** are referenced, resolved, and kept out of Domain, prompts, and AuditEvent **values**.

It does **not** select Vault, cloud secret managers, password managers, OS credential-store products, or a KMS.

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**SecretPort / SecretReference**, with a **local-dev adapter first**. An external secrets manager is allowed **later** when deployment actually requires it.

| Piece | Rule |
|---|---|
| Domain / SoR | May store **SecretReference** (name/id, purpose, not the value). Must **not** store secret **values** |
| Research / LLM / ModelPort | Receive capabilities and references, **not** raw credentials, where there is an alternative |
| Worker | After Core authorization, resolves **only the minimum** secrets for that issued job at the **execution boundary** |
| AuditEvent | May record that a named secret was **used/rotated/referenced**. Must **not** contain secret **values** |
| Logs | Secret values forbidden |

**PRODUCT: DEFER**

---

## Why this decision exists

Platform already lists **secrets access** as a capability, not a vendor (`PROJECT_STRUCTURE.md`). Requirements demand secrets/model-context separation, least privilege, and no provider owning domain logic.

Environment variables as **the architecture** leak into process lists, child environments, and logs, and they do not scale to remote Workers without copying the Control Plane’s entire secret set. An external manager on day one is extra infrastructure a single local developer does not need (Decision 010 Phase A).

The port lets local env-file / env-var / file adapters exist **without** becoming Domain types or a Vault lock-in.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Values ∉ Domain | PostgreSQL must not be a password dump |
| Values ∉ prompts | ModelPort/Strix reasoning must not require raw API keys in context where avoidable |
| Values ∉ AuditEvent payloads | References/ids only |
| Least privilege to Workers | No global/master credential bundle for every job |
| Replaceability | Provider/tool credentials swap without Core/Research SDK lock-in |
| Rotation possible later | Reference stays; value changes in the adapter |
| Local simplicity | Phase A must not require a cloud secret manager |
| Remote-ready | Future Workers must not need a copy of all Control Plane secrets |

### Candidate results

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. Environment variables only** | **Pass as a local adapter, fail as the strategy** | Simple. Weak isolation, easy to pass into Worker env wholesale, poor remote story |
| **2. Local encrypted config/secret file** | **Pass as a local adapter** | Still a file on the developer host. Not the contract |
| **3. SecretPort + local-dev adapter first** | **Pass** | Selected |
| **4. OS-native credential store as architecture** | **Pass as an optional adapter** | Windows vs Linux stores would freeze current OS context as architecture |
| **5. External secrets manager from day one** | **Pass later, fail v1 fit** | Premature product and ops |

---

## Candidate evaluations

**Env-only** — acceptable **implementation** of SecretPort on a laptop if values never enter Domain, prompts, or audit payloads, and Workers do not inherit the full Control Plane environment. Not the strategy: remote Workers and rotation become “copy `.env`,” which this decision forbids as the design.

**Encrypted local file** — similar: adapter, not architecture.

**SecretPort** — selected. Research asks for a **capability**; Core authorizes the job; Worker/Platform resolves `SecretReference` at execution. LLM does not receive the credential.

**OS-native store** — optional later adapter; not chosen as the model (would make Windows Credential Manager or libsecret an architecture constraint).

**External manager now** — justified when Phase B/C or multi-operator hosting makes local files unsafe. Product still a later decision.

---

## Comparison matrix (project fit)

**ENV** = env-only as strategy. **FILE** = encrypted file as strategy. **PORT** = SecretPort + local first (selected). **OS** = OS store as architecture. **EXT** = external manager v1.

| Criterion | ENV | FILE | PORT | OS | EXT |
|---|---:|---:|---:|---:|---:|
| correctness / least privilege | 2 | 3 | 5 | 4 | 4 |
| values out of Domain/prompts/audit | 3 | 3 | 5 | 4 | 4 |
| local simplicity | 5 | 4 | 4 | 3 | 1 |
| remote Worker secret isolation | 1 | 1 | 5 | 3 | 4 |
| rotation later | 2 | 3 | 5 | 4 | 5 |
| vendor lock-in | 5 | 5 | 5 | 3 | 2 |
| premature infrastructure | 4 | 4 | 5 | 3 | 1 |
| testability | 4 | 3 | 5 | 2 | 2 |

---

## Secrets + identity relationship (conceptual)

```
Research → capability request
→ Core authorization (scope, budget, approval if required)
→ Worker (identity + issued job)
→ SecretPort resolves SecretReference at execution boundary
```

Not: `LLM → raw credential`.

Do not over-specify injection (env vs fd vs file in the Worker). The invariant is **minimum required**, **after** authorization, **not** in ModelPort context.

---

## Constraints

1. **Secret values never in Domain records, WorkerResult, Evidence, prompts, or AuditEvent payloads.**
2. **SecretReference may be stored and audited.**
3. **Workers never receive the Control Plane master/global secret set.**
4. **Local-dev adapters (env, file) are allowed; they are not the architecture.**
5. **No secrets product selected.**
6. **Rotation must remain possible** by changing the value behind a stable reference.
7. **Future remote Workers get per-job or per-worker scoped material**, not a cloned Control Plane secret bag.
8. **Python/OS/Kali must not define the SecretPort.**

---

## Revisit triggers

- More than one operator / hosted Control Plane
- Remote Workers that must not see Control Plane secrets (Phase B)
- Rotation or leak incident
- Local file/env adapter appearing in Domain or logs
- A specific manager is required by a **later** deployment decision (still a new decision, not a silent Vault import)

---

## Open questions

- Local adapter (env vs file vs OS store)
- External product when triggered
- How Worker-scoped short-lived material is minted (not chosen)

---

## Confidence

**MEDIUM**

The port is required to keep secrets out of SoR, prompts, and audit **values**. Deferring the product matches Phase A. Confidence is not HIGH because the first adapter is unchosen and a sloppy env pass-through could still dump master credentials into Kali/WSL.

---

# Decision 014 — Worker Isolation Strategy

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 005 (out-of-process side-effect Workers; Kali/WSL first tool Worker; in-process = fakes only); Decision 010 (staged deployment; containers not mandatory); Decision 013 (minimum secrets at execution boundary)

This decision selects **isolation as a property** of Worker execution. It does **not** select Docker, a VM product, Kubernetes, or a sandbox vendor.

`TECHNICAL_REQUIREMENTS.md`: Worker isolation is a **property**, not a chosen container/VM product.

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS — mixed isolation policy by Worker capability; process/OS-environment boundary first**

**First implementation:**

```
Control Plane
→ explicit Worker process boundary
→ Kali/WSL (or local child-process) execution environment
```

Stronger **container/VM** isolation is **deferred**. Docker/Kubernetes are **not** selected and **not** required.

In-process execution remains **test doubles only** (Decision 005). Real side-effect Workers are out-of-process.

Isolation policy may **strengthen** with conceptual side-effect **level**. Isolation technology is **not** domain truth and is **not** an offensive-automation design.

---

## Conceptual side-effect levels

These are **control/runtime** categories for how harshly to isolate and whether Core Approval is required. They are **not** Finding severity and **not** stored as “the database says Docker.”

| Level | Meaning | Default isolation posture (v1) |
|---|---|---|
| **0** | Read-only / low side-effect | Out-of-process still; no extra product |
| **1** | Minor / reversible | Same process boundary; least-privilege secrets |
| **2** | External state change / approval-sensitive | Same boundary; **Core Approval** may be required (already domain). No new sandbox product required in v1 |
| **3** | Destructive / high-impact | **Denied by default.** If ever allowed, stronger isolation + Core Approval. Not designed here as an exploit pipeline |

This is not a catalog of attacks and not a mandate to automate destructive actions.

---

## Why this decision exists

Workers run tools against **untrusted** targets and **untrusted** model/tool text (prompt-injection-derived requests). Crash, filesystem, network, and credential blast radius must not include Core/PostgreSQL.

Decision 005 already forbids in-process side-effect Workers and places first tool execution in Kali/WSL. Decision 010 forbids mandatory containers. Isolation must **use** that process/OS boundary without freezing WSL or Docker as architecture.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Side-effect Workers out-of-process | Shared fate with Control Plane is forbidden |
| Worker cannot widen scope | Isolation does not grant authorization |
| Untrusted content contained | Target bytes, HTML, and tool output do not run inside Core |
| No container product required | Isolation property ≠ Docker |
| WSL ≠ architecture | First env, not production isolation technology |
| Isolation ≠ domain SoR | No `runtime=wsl` as authorization |

### Candidate results

| Strategy | Stage 1 | Note |
|---|---|---|
| **1. In-process execution** | **Fail for real Workers** | Allowed as fakes only |
| **2. Child-process isolation** | **Pass** | Default local isolation story |
| **3. WSL/Kali process boundary** | **Pass as first tool env** | OS-environment isolation + tools. Not permanent architecture |
| **4. Container isolation** | **Pass later** | Stronger FS/network limits. Product not chosen. Not v1 mandate |
| **5. VM isolation** | **Pass later** | Highest ops cost. Premature |
| **6. Mixed policy by capability** | **Pass** | Selected: process/WSL now; container/VM if risk/topology justify |

---

## Isolation concerns (v1 vs later)

| Concern | v1 | Later |
|---|---|---|
| Filesystem | Worker process/WSL not the Control Plane disk as a shared writable tree | Container/VM mounts if needed |
| Network | Worker may have network for authorized tools; Core does not proxy arbitrary LLM→network | Same contract; tighter netns later |
| Credentials | Decision 013 minimum at boundary; do not inherit Control Plane env | Per-job material |
| Process lifetime / crash / cancel | Kill the Worker process; Control Plane survives | Same |
| Cleanup | Worker workspace discarded; artifacts via Decision 006 ingest | Same |
| CPU/memory | Best-effort OS limits; no orchestrator product | cgroups/VM if justified |
| Tool dependencies | Kali/WSL or child-process images **as adapters** | Replaceable |
| Malicious target / prompt-injected tool requests | Stop, WorkerResult, Core re-eval; do not execute unauthorized tools | Stronger sandbox if measured |

---

## Comparison matrix (project fit)

**IP** = in-process. **CH** = child-process. **WSL** = Kali/WSL as standing isolation tech. **CT** = containers v1. **VM** = VMs v1. **MX** = mixed, process/WSL first (selected).

| Criterion | IP | CH | WSL | CT | VM | MX |
|---|---:|---:|---:|---:|---:|---:|
| crash containment | 1 | 5 | 4 | 5 | 5 | 5 |
| local simplicity | 5 | 4 | 3 | 2 | 1 | 4 |
| Kali/WSL tool fit | 1 | 2 | 5 | 3 | 2 | 5 |
| credential blast radius | 1 | 4 | 4 | 4 | 5 | 5 |
| future remote Workers | 1 | 3 | 2 | 4 | 4 | 5 |
| premature infrastructure | 4 | 5 | 4 | 2 | 1 | 5 |
| not freezing WSL/Docker | 3 | 5 | 2 | 2 | 3 | 5 |
| Level 3 default deny | 2 | 4 | 4 | 4 | 4 | 5 |

---

## Constraints

1. **Real Workers: process boundary.** In-process = fakes only.
2. **First tool Worker: Kali/WSL or local child-process** behind the same contract (Decision 005).
3. **Docker/container runtime not selected and not required.**
4. **VMs/Kubernetes not selected.**
5. **WSL is not the permanent isolation technology.**
6. **Isolation policy is not domain truth** (not Evidence, not authorization).
7. **Level 3 denied by default.** No offensive-automation playbook in this decision.
8. **Prompt-injected tool requests** do not execute without Core authorization; isolation is not a substitute for DEFAULT DENY.
9. **Workers cannot write SoR** (unchanged).
10. **Remote Workers not forced.** When they exist, they remain less trusted and authenticated ≠ authorized (Decision 015).

---

## Revisit triggers

- Need for stronger FS/network/credential isolation than a process/WSL boundary **as observed**
- Level 2/3 work that Core Approval alone cannot contain
- Host compromise risk from untrusted target content
- Phase B remote Workers (isolation becomes peer sandbox + authn, still not Core)
- Any proposal that “Docker is the Worker” (adapter only, new decision)

---

## Open questions

- OS resource-limit mechanism
- Worker workspace layout (not Domain)
- Container/VM product if triggered

---

## Confidence

**MEDIUM**

Process + Kali/WSL matches locked topology without selecting Docker. Confidence is not HIGH because WSL is a coarse boundary (not a capability sandbox) and Level 2 work may later need more than process isolation.

---

# Decision 015 — Identity / Authentication / Inter-Component Trust Model

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 005 (Worker identity vs Core authorization); Decision 008 (models are not principals); Decision 013 (SecretReference); Decision 014 (Workers less trusted)

This decision defines **who exists as an identity**, **what trust means**, and **what first implementation must record**. It does **not** select OAuth, OIDC, mTLS, IAM, an API gateway, or a service mesh.

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS — explicit identity classes; local single-operator first; authentication ≠ authorization**

There is **no** identity named “AI” or “the model” as an authorization principal. Models never authorize.

**First implementation:** one **Human Operator** identity is enough to run locally, but that identity **must exist** as a stable id for AuditEvent, Approval `decision actor`, and ResearchRun `initiator`. Control Plane and Worker identities are **distinct**. Worker authentication for remote peers is **required when Workers are services**; local child-process/WSL still has an **auditable worker id**. No IAM product.

---

## Identity classes

| Class | Role | Trust |
|---|---|---|
| **Human Operator** | Initiates runs; performs Human Review | Highest *human* authority through Interface; decisions become **Core Approval**, not “the UI said so” |
| **Control Plane** | Hosts Core, Research, Data access, Interface, Platform contracts | Highest *system* trust for **policy decisions**. Not a Worker |
| **Worker** | Side-effect runtime | Lower trust. Authenticated ≠ authorized |
| **Integration / Adapter** | Strix, Burp, ModelAdapter, SecretPort adapter, tools | **Does not inherit Core trust.** Output untrusted |
| **External Model Provider** | Completions via ModelPort | Untrusted output; not a principal |
| **External Tool Runtime** | Scanner/browser/agent processes | Untrusted output; not a principal |

No other principal is invented for “the LLM allowed it.”

---

## Trust hierarchy (conceptual)

Highest trust: **Core authority decisions** (authorization, scope, policy, budget, Approval).

Lower: **Research proposals** (untrusted as authority).

Lower: **Worker execution runtime** (untrusted as truth; may be authenticated).

**Untrusted input:** model outputs; tool outputs; web/API/email/document content; WorkerResult before Transition A; Integration content.

```
Authentication ≠ authorization
Authorization ≠ Evidence
Execution success ≠ trust
Same machine / same network / WSL ≠ trust
```

Logical trust (`PROJECT_STRUCTURE.md`) remains:

Core > Research > Interface/orchestration callers.

Workers and Integrations sit **below** that chain as execution/adapters. They do not enter the Core trust set by sharing a laptop with the Control Plane.

---

## Operator identity

v1 may be **single-user/local** (no OAuth). The operator still needs a **stable identifier** so that:

- ResearchRun has an initiator
- Approval has a decision actor
- AuditEvent can answer *who*

A missing operator id would make Approval and audit untraceable. Local “dev operator” is an identity, not an anonymous god mode that bypasses Core.

---

## Control Plane vs Worker

Control Plane identity ≠ Worker identity.

A Worker presenting “I’m on WSL on the same host” is **not** Core. Future remote communication must support **authenticated peers** (mechanism deferred). Local IPC still names the Worker runtime for audit.

---

## Worker identity

Local and future remote Workers need a **stable worker identity** (which runtime executed this job).

**Authenticated Worker ≠ authorized action.** Core issues per-request authorization and immutable budget. Worker cannot self-authorize or widen scope.

---

## Integration identity

Strix/Burp/ModelAdapter/tool adapters are **Integrations**. They do not inherit Core trust. Strix is not a Control Plane component.

---

## Transport trust

Decision 005: transport is not truth. This decision: **same-machine is not a trust grant.** Phase B remote Workers: authenticated transport required; product/protocol still unchosen.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| No model principal | LLM cannot be an Approval actor or AuthorizationSource |
| Operator id for audit/approval/run | Even single-user |
| Worker id ≠ Core | Distinct identities |
| Authn ≠ authz | Core still DEFAULT DENY per request |
| No IAM product required for v1 | Local operator id is enough to start |
| Integrations untrusted | Strix ≠ Core |

All candidates that keep these gates can pass. Selecting OIDC now is not a gate; it is premature product.

---

## Comparison (why not a product now)

| Approach | v1 fit |
|---|---|
| Anonymous local, no operator id | **Fail** audit/Approval/initiator |
| Conceptual identities + local operator id (selected) | **Pass** |
| OAuth/OIDC/IAM from day one | Premature; single-developer Phase A |
| mTLS/service mesh from day one | Premature; no remote mesh |
| “Same WSL = trusted Worker” | **Fail** Stage 1 |

---

## Constraints

1. **No AI/model authorization principal.**
2. **Human Operator identity exists in v1** for initiator, Approval actor, audit.
3. **Control Plane and Worker identities are distinct.**
4. **Authentication never replaces Core authorization.**
5. **Integrations do not inherit Core trust.**
6. **Same host/WSL/network is not a trust domain.**
7. **No OAuth, OIDC, mTLS, IAM, gateway, or mesh product selected.**
8. **Identity records are not Evidence** and not Research Memory truth.
9. **Secret resolution (013) is keyed by authorized job + Worker identity**, not by model identity.
10. **Remote Worker authn mechanism deferred** until Phase B, but the **requirement** is already stated.

---

## First implementation / evolution

**v1:** Configured local operator id; Control Plane instance id; Worker runtime id on each job; no SSO. Approvals record that operator.

**Later:** Real operator authentication when multi-user; Worker peer authentication when remote; still Core authorization; still no model principal.

---

## Revisit triggers

- Second human operator
- Remote Workers (authenticated peers)
- Need to prove Control Plane authenticity to Workers
- Operator id missing on Approval/AuditEvent (bug, not “add Okta”)
- Any path treating model id as decision actor

---

## Open questions

- Operator id format/storage (not a vendor)
- Worker authentication protocol (Decision 005 open)
- Multi-user role model beyond “operator vs system”

---

## Confidence

**MEDIUM**

Identity classes and authn≠authz are required by Core, Approval, and Decision 005. Deferring IAM matches Phase A. Confidence is not HIGH because local single-user can be implemented as a fake “always-admin” if undisciplined, and Worker authn for WSL is still a stub until specified.

---

## Self-audit (Decisions 013, 014, 015)

| Forbidden reading | Status |
|---|---|
| Raw secrets in prompts | **Forbidden**; SecretReference + ModelPort constraint |
| Secrets in AuditEvent **values** | **Forbidden**; references only |
| Worker receives global/master credentials | **Forbidden** |
| Model becomes authorization principal | **Forbidden** |
| Same-machine = trusted | **Rejected** |
| Authenticated Worker = authorized action | **Rejected** |
| Strix becomes trusted Core component | **No** |
| WSL becomes permanent isolation technology | **No**; first env only |
| Docker/Kubernetes selected prematurely | **No** |
| Process boundary bypass for real Workers | **No**; in-process = fakes |
| Worker can widen scope | **No** |
| Remote Worker selected before needed | **No** |
| Isolation policy becomes domain truth | **Forbidden** |
| Secret product becomes architecture | **Product deferred** |

**FINAL STATUS: PASS**

---

# Decision 016 — Contract Representation / Versioning Strategy

**Status:** ACCEPT WITH CONSTRAINTS  
**Date:** 2026-08-16  
**Depends on:** Decision 001 (language-neutral contracts; Python classes are not architectural truth); Decision 005 (Worker contract; transport replaceable); Decision 013 (SecretReference); Decision 014 (side-effect levels)

This decision selects the **canonical representation** of cross-boundary contracts and the **versioning layout**.

It does **not** select:

- HTTP, gRPC, or any transport
- a queue/broker
- a JSON Schema **validator library**
- a Protobuf runtime, compiler, or codegen toolchain
- OpenAPI as Worker-contract truth
- ORM / database types (including UUID)

**Canonical contract representation ≠ transport protocol.**

---

## Decision

**STRATEGY: ACCEPT WITH CONSTRAINTS**

**Canonical representation: JSON Schema Draft 2020-12** (`https://json-schema.org/draft/2020-12/schema`).

**Versioning:** major contract generations live under `contracts/v1/`, `contracts/v2/`, … Messages carry an explicit `contract_version`. Breaking semantic/schema change ⇒ new major directory. Backward-compatible additive fields may stay in the same major. Field removal or meaning change is breaking.

Python classes, PostgreSQL types, OpenAPI documents, and Protobuf encodings are **not** the architectural contract truth. They may later **project** or **carry** these schemas.

**PRODUCT / RUNTIME: DEFER** — no validator or codegen dependency in this decision.

---

## Why this decision exists

Decision 001: contracts are language-neutral; Python types are not architectural contracts. Decision 005: local IPC now, remote transport later, same Worker contract. A1 must exist as files Workers in Python/Go/Rust can validate without importing `research_os`.

Python classes as canonical truth would lock Workers to the control-plane package. OpenAPI as canonical truth would lock the Worker boundary to HTTP (Interface may use OpenAPI later; that is a different surface). Protobuf as **canonical** truth is a capable IDL but couples identity, codegen, and a binary encoding before any remote Worker exists. Avro pulls schema-registry/broker gravity. Hybrid dual-canonical (Schema + proto both “truth”) splits the SoR of the contract itself.

JSON Schema is validation-focused, inspectable, codegen-optional, and transport-independent: the same schema can describe a JSON object over a pipe today and over a later request/response without becoming that transport.

---

## Stage 1 — Mandatory gates

| Gate | Meaning |
|---|---|
| Language-neutral | Go/Rust Workers are not blocked |
| Independent of Core/Research classes | No `research_os` import required to know the shape |
| Machine-validatable | Schema files parse; later a validator may be chosen |
| Transport-neutral | Not HTTP, not a broker, not Postgres |
| Versionable | Explicit major + in-message version |
| Secret-safe | Values cannot appear as required secret fields |

### Candidate results

| Candidate | Stage 1 | Note |
|---|---|---|
| **1. Python classes as canonical** | **Fail** | Violates Decision 001. Not language-neutral |
| **2. JSON Schema** | **Pass** | Selected. Semantics without transport or codegen |
| **3. Protocol Buffers as canonical** | **Pass as a later encoding** | Strong IDL. Canonical use forces protoc/runtime coupling now; user forbade installing that runtime this round. Not rejected as incapable |
| **4. OpenAPI as canonical Worker truth** | **Fail as Worker canonical** | HTTP-specific Interface description. May later describe Decision 011 API as a **projection** |
| **5. Avro-like** | **Pass weakly** | Extra ecosystem; broker/registry gravity. Not needed |
| **6. Dual canonical hybrid** | **Fail clarity** | Two truths. Allowed later: JSON Schema canonical + other encodings as projections |

---

## Candidate evaluations

**Python classes** — convenient for the control plane; forbidden as architecture. Implementation DTOs may exist later **derived from** schemas, not the reverse.

**JSON Schema Draft 2020-12** — selected. `$id` is the contract id. `$schema` pins the dialect. Top-level `additionalProperties: false` keeps unknown authority-bearing fields from being silently accepted. Extensibility is confined to named bags (`arguments`, `raw_result`, `diagnostics`, `discovery_context`, `control_signal`). Those bags **must not** carry policy, authorization, Evidence, Finding, Approval, or budget truth.

Trade-offs accepted: no native types; no binary framing; evolution still needs discipline. None of those choose a transport.

**Protobuf** — best-in-class for multi-language **encoding** and evolution if remote Workers appear. Not canonical now: installing runtime/codegen would make protobuf the architecture. A later decision may add `.proto` **projections** of v1 JSON Schema without replacing canonical files.

**OpenAPI** — Worker execution is not an HTTP resource. Interface Phase A may publish OpenAPI later; it must `$ref` or duplicate these Worker schemas, not become their parent.

**Avro** — similar to protobuf with more Kafka-shaped ops. Rejected for v1.

---

## Versioning rules

```
contracts/
  v1/          # current major
  v2/          # next breaking generation, if needed
```

- `contract_version` on Worker-facing messages is `"v1"` for this generation.
- Additive optional fields: same major, documented.
- Remove/rename/change meaning: new major (`v2/`).
- **Transport version ≠ domain lifecycle version ≠ this contract major.** Experiment status and HTTP API versions are different axes.
- Producer/consumer compatibility is **testable** (contract tests later). No SemVer tooling product is selected.

---

## Constraints

1. **JSON Schema Draft 2020-12 is canonical.** Other formats are projections or transports.
2. **Python class ≠ contract truth.**
3. **Transport ≠ contract semantics.** IPC/HTTP/gRPC/queue unchosen.
4. **No UUID or PostgreSQL type in contracts.** Identifiers are opaque strings.
5. **No Protobuf/OpenAPI/Avro runtime or codegen in this decision.**
6. **No JSON Schema Python library required** to store or lint files with the stdlib.
7. **Secret values forbidden** in schemas (Decision 013).
8. **WorkerResult ≠ Observation/Artifact/Evidence/Candidate/Finding.**
9. **ReauthorizationRequest is not an authorization decision.**
10. **Side-effect level is not policy.** Level 3 is representable and **denied by default** in Core (Decision 014).
11. **Workers cannot mint authorization or raise budget** via payload.
12. **`additionalProperties: false`** on authority-bearing objects. Extensibility only on listed bags.

---

## Revisit triggers

- Remote Workers need a binary encoding (consider Protobuf **projection**, not a silent canonical swap)
- Interface needs HTTP description (OpenAPI **projection** of these schemas)
- Schema dialect or `$id` policy becomes operationally painful
- Compatibility tests fail because silent additional properties were allowed on authority objects

---

## Open questions

- JSON Schema validator library (later)
- Whether `.proto` projections are generated
- Exact additive-field process inside `v1`

---

## Confidence

**MEDIUM**

JSON Schema is the only candidate that is language-neutral, transport-neutral, and codegen-free for A1 without contradicting Decision 001. Confidence is not HIGH because Protobuf remains a strong **encoding** alternative if Workers go remote, and Draft 2020-12 still needs human evolution discipline.

---

## Self-audit (Decision 016)

| Forbidden reading | Status |
|---|---|
| Python class is canonical truth | **No** |
| Contract is PostgreSQL-specific | **No** |
| UUID forced as DB type | **No**; opaque strings |
| HTTP selected | **No** |
| Queue/broker selected | **No** |
| JSON Schema library/product lock-in | **Dialect chosen; runtime deferred** |
| Protobuf canonical lock-in | **Not selected as canonical** |
| WorkerResult is Observation/Evidence | **Forbidden in A1 docs/schemas** |
| Raw payload is authority | **Forbidden**; extensible bags only |
| Secret values in contract | **Forbidden** |
| Worker produces authorization | **No** |
| Worker changes budget | **Budget is Core-issued; result has no budget authority** |
| Reauthorization = authorization | **No** |
| Side-effect level replaces policy | **No**; Core still DEFAULT DENY; level 3 denied by default |
| Go/Rust Workers blocked | **No** |

**FINAL STATUS: PASS**

