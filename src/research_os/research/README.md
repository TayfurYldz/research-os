# Research

Research produces **proposals**. A7 v1 adds a bounded reasoning cycle. It is not an autonomous bug-bounty agent.

Types:

- `ResearchContext` — typed epistemic input. Not a prompt blob.
- `HypothesisProposal` / `HypothesisChallenge` — untrusted structured model output.
- `HypothesisDraft` — human-seeded statement + origin. Not fact.
- `ExperimentPlan` — proposed capability/action/target plus expected and disconfirming observations. Not authorization.
- `ExperimentFeedback` — reconstructs what happened. Not a vulnerability verdict.
- `HypothesisAssessment` — context-bound learning under one experiment. Not Hypothesis truth and not Evidence.

Admission (`admit_hypothesis`) is Research-domain logic. Generator output is not a Hypothesis until admitted.

Research must not:

- call a Worker or subprocess
- persist via PostgreSQL
- import a provider SDK
- authorize itself
- treat model output as Observation, Evidence, or Finding
- treat a matching Observation as a verified security issue

Application coordinates `ProposeResearchHypothesis` and `EvaluateExperimentFeedback` with Data ports. Deterministic assessment for GATE 03 is `diagnostic.echo.v1` only.

Provider-neutral research-behavior evaluation lives in `research_os.benchmark` and `benchmarks/research/` (Decisions 029–030). Research must not import the benchmark package. Benchmark reports are not Evidence, Finding, or SoR truth.
