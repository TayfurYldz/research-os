# Security ground-truth benchmark (evaluation data)

This directory is **evaluation authority** for GATE 15. It is not:

- the research/model benchmark (`benchmarks/research/`)
- Domain SoR
- Research Memory
- a Worker contract
- Evidence, Candidate, or Finding truth

Each scenario splits:

| Field | Who may see it |
|---|---|
| `harness` | E2E lab fixture starter only |
| `hidden_evaluation` | scorecard / tests only |

Hidden evaluation **must never** enter WorkerRequest, Observation, Evidence evaluator input, Candidate, or Verification.

`scenario_id` + `version` is identity. Do not silently rewrite expected semantics after results exist.

GATE 15 is a **false-positive / ground-truth** benchmark for the existing `http.authorization.differential` pipeline. It is not a model benchmark and not GATE 04B.
