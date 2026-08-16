# Application

Use-case coordination for the Control Plane.

Application **sequences** Core decisions, Research plans, Platform ports, Data Unit of Work, Transition A, and durable ExecutionAttempt dispatch.

It does **not** own:

- authorization / scope / budget policy (Core)
- hypothesis semantics (Research)
- PostgreSQL or subprocess implementations
- Evidence / Candidate / Finding

Use cases:

- `IngestCompletedWorkerInvocation` (Transition A)
- `ExecutePlannedExperiment` (A7-lite control-loop skeleton; not a Research Brain)
- `ProposeResearchHypothesis` (bounded Generator/Falsifier/admission)
- `PreparePlannedExperiment` (Experiment lifecycle + immutable ExperimentPlan spec)
- `EvaluateExperimentFeedback` (reconstruct feedback, deterministic assessment, persist history)

`request_id` is generated here. Worker and model do not choose it. Worker invocation happens only after durable AUTHORIZED/DISPATCHING intent is committed, and never inside an open database transaction.

Assessment does not invoke a model, does not create Evidence, and does not start another experiment.

`request_id` is generated here. Worker and model do not choose it. Worker invocation happens only after durable AUTHORIZED/DISPATCHING intent is committed, and never inside an open database transaction.

Dependency direction:

```
Interface
  → Application
    → Core / Research
    → Data ports
    → Platform ports
```

Core and Research must not import Application. Concrete adapters are injected.
