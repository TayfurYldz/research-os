# Application

Use-case coordination for the Control Plane.

Application **sequences** Core decisions, Research plans, Platform ports, Data Unit of Work, Transition A, and durable ExecutionAttempt dispatch.

It does **not** own:

- authorization / scope / budget policy (Core)
- hypothesis semantics (Research)
- PostgreSQL or subprocess implementations
- Evidence / Candidate / Finding *authority*

Use cases:

- `IngestCompletedWorkerInvocation` (Transition A)
- `ExecutePlannedExperiment` (A7-lite control-loop skeleton; not a Research Brain)
- `ProposeResearchHypothesis` (bounded Generator/Falsifier/admission)
- `PreparePlannedExperiment` (Experiment lifecycle + immutable ExperimentPlan spec)
- `EvaluateExperimentFeedback` (reconstruct feedback, deterministic assessment, persist history)
- `AdmitDiagnosticEvidence` (Transition B coordination; Research admits; Data persists)
- `ProposeCandidateFromEvidence` (GATE 05; Research admits OPEN Candidate)
- `StartCandidateVerification` / `CompleteCandidateVerification` (Research transition rules; verifier cannot write Candidate)
- `SubmitFindingProposal` / `StartHumanReview` / `RecordHumanReview` / `FinalizeFinding` (GATE 06; Application coordinates; cannot self-approve)
- `ProjectDiagnosticTargetModel` / `AdmitTargetInference` / `CompareDiagnosticDifferential` (GATE 07; Application coordinates; cannot turn difference into Evidence)
- `AdmitDiagnosticInvariant` / `RecordInvariantCounterexample` / `ComposeDiagnosticChain` (GATE 08; Application coordinates; cannot turn an invariant or chain into Evidence, Candidate, Finding, or a Worker dispatch)
- `SelectResearchOpportunities` / `CaptureDiagnosticSnapshot` / `CompareDiagnosticSnapshots` (GATE 09; Application coordinates; selection is not Core ALLOW; a ChangeEvent is not Evidence)
- `AuthorizeStrixExecution` (GATE 10; Core ALLOW first; denied requests never reach Strix; Strix output is untrusted and is not Observation/Evidence)

`request_id` is generated here. Worker and model do not choose it. Worker invocation happens only after durable AUTHORIZED/DISPATCHING intent is committed, and never inside an open database transaction.

Assessment does not invoke a model, does not create Evidence, and does not start another experiment.
Evidence admission does not create Candidate or Finding and is not Verification.
Candidate VALIDATED is not a Finding.
FindingProposal is not a Finding. Application does not fabricate Approval.
Target Model is not SoR truth. Differential results are not Evidence.
An invariant hypothesis is not a fact or ScopeRule. A chain hypothesis is not an exploit and does not dispatch a Worker.
A selected ResearchOpportunity is not Hypothesis truth and not authorization. A Snapshot is not a second SoR. A ChangeEvent is not a vulnerability.
Strix is an Integration runtime. Application cannot import `integrations.strix`. A provider/runtime content-policy block is `CONTENT_POLICY_BLOCKED`, not Hypothesis rejection.

Dependency direction:

```
Interface
  → Application
    → Core / Research
    → Data ports
    → Platform ports
```

Core and Research must not import Application. Concrete adapters are injected.
