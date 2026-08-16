# Research

Research produces **proposals**. It is not a Research Brain in A7-lite.

A7-lite types:

- `HypothesisDraft` — human-seeded statement + origin. Not fact.
- `ExperimentPlan` — proposed capability/action/target. Not authorization.

Research must not:

- call a Worker or subprocess
- persist via PostgreSQL
- authorize itself
- generate hypotheses with a model
- update Hypothesis truth from Observation

Application coordinates Research plans with Core and WorkerPort.
