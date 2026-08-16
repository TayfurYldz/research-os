# Research benchmark (engineering data)

This directory is **evaluation data**. It is not:

- Domain SoR
- Research Memory
- production configuration
- a Worker contract
- Evidence, Finding, Candidate, or Hypothesis truth

JSON fixtures are intentional. YAML is not used.

## Visible vs hidden

Each scenario splits:

| Field | Who may see it |
|---|---|
| `visible_input` | ResearchContext, Generator, Falsifier, ModelCallRequest |
| `hidden_evaluation` | evaluator / tests / scorecard only |

Hidden evaluation **must never** enter prompts, ResearchContext, model requests, or model-visible metadata.

If hidden material is serialized into a model-visible structure, that is a **benchmark leakage failure**, not a grading footnote.

## Identity

`scenario_id` + `version` is the identity. Changing hidden expected semantics materially requires a new version. Do not silently rewrite history after results exist.

## Development vs holdout

| Split | Rule |
|---|---|
| `development` | May be inspected while building the harness and scripted baselines |
| `holdout` | Must not be used to tune prompts or admission logic by hand |

This repository currently ships **development** scenarios only. The holdout rule is in force for any future holdout files: `--include-holdout` loads them for evaluation, not for prompt/admission iteration.

Optimizing Research Brain to this suite is a failure mode.

## Categories (synthetic / controlled)

No exploit payloads. No real bug-bounty targets.

1. `CLEAN_DIAGNOSTIC` — echo-style neutral baseline
2. `UNSUPPORTED_SECURITY_CLAIM` — context does not support a security conclusion
3. `AMBIGUOUS_BEHAVIOR` — multiple benign explanations
4. `SOURCE_HALLUCINATION_TRAP` — limited ids; fabricated refs must be caught
5. `PROMPT_INJECTION_CONTENT` — untrusted “ignore previous instructions…” remains data
6. `PRIOR_HYPOTHESIS_POISONING` — a prior Hypothesis is not a fact
7. `NEGATIVE_CONTEXT_SCOPE` — contradiction under context C is not “impossible everywhere”
8. `DIFFERENTIAL_REASONING_SEED` — actor/state difference is not a vulnerability
9. `INCONCLUSIVE_CONTEXT` — insufficient information; caution is desirable
10. `POLICY_BOUNDARY_TRAP` — proposal must not acquire authority

Not every scenario should be `ADMITTED`. A suite that always admits is wrong.

## Scoring

The harness prints a **scorecard**: hard-fail event counts plus quality dimensions.

It does **not** emit `MODEL_SCORE = 8.72` or any other magic total.

It does **not** claim N4, zero-day discovery, or “true creativity.”

Novelty language allowed in reports: diversity, composition, target-specificity, non-template behavior.

## Human-review rubric (future, no UI)

Automatic checks cannot resolve every dimension. Blind human review, when added later, uses ordinal labels only:

| Dimension | Labels |
|---|---|
| usefulness | POOR / ACCEPTABLE / STRONG |
| non-triviality | POOR / ACCEPTABLE / STRONG |
| quality of alternative explanation | POOR / ACCEPTABLE / STRONG |
| experiment discrimination | POOR / ACCEPTABLE / STRONG |
| target-specific reasoning | POOR / ACCEPTABLE / STRONG |

No dashboard in GATE 04A. No LLM-as-judge in GATE 04A.

## Run

```
uv run python scripts/run_research_benchmark.py
uv run python scripts/run_research_benchmark.py --baseline BAD_HALLUCINATOR
uv run python scripts/run_research_benchmark.py --json-report var/benchmark-results/report.json
```

Scripted baselines are test doubles, not real models. GATE 04B will attach real provider adapters to this same harness.
