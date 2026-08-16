# Research

Research produces **proposals**. A7 v1 adds a bounded reasoning cycle. It is not an autonomous bug-bounty agent.

Types:

- `ResearchContext` — typed epistemic input. Not a prompt blob.
- `HypothesisProposal` / `HypothesisChallenge` — untrusted structured model output.
- `HypothesisDraft` — human-seeded statement + origin. Not fact.
- `ExperimentPlan` — proposed capability/action/target plus expected and disconfirming observations. Not authorization.
- `ExperimentFeedback` — execution/observation references. Not a vulnerability verdict.

Admission (`admit_hypothesis`) is Research-domain logic. Generator output is not a Hypothesis until admitted.

Research must not:

- call a Worker or subprocess
- persist via PostgreSQL
- import a provider SDK
- authorize itself
- treat model output as Observation, Evidence, or Finding

Application coordinates `ProposeResearchHypothesis` with Data ports and an injected ModelPort.
