# Slice 7 Completion Record — Exploratory execution plumbing + human-gated family promotion

Status: CLOSED / **SLICE_QUALIFIED (PASS)** for the **narrow** lock Slice 7 criteria below.
Implementation status: **IMPLEMENTATION_COMPLETE** for that same narrow path.

These two are not the same claim. Implementation complete means the smallest required path exists. Qualified means the PASS/hard-fail tests below were executed against that path.

## Qualification boundary (do not inflate)

Slice 7 is qualified as:

1. run-scoped exploratory **execution plumbing** (`diagnostic.echo` through the existing compiler → Core → Worker chain), and
2. **human-gated permanent HunterFamily write**.

It does **not**:

- close **canonical MR-5 PromotionPipeline** (`RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md` §10 / reconnection MR-5: Assessment → Evidence → Candidate → Independent Verification → FindingProposal, restart-safe, human gate retained). Slice 5 only added the Assessment→Evidence hop. The rest of that pipeline remains separately invoked. Slice 7 did not extend it.
- close **mutation or protocol execution**. Slice 4B matrix cells stay `BLOCKED_MISSING_SEMANTICS`. Slice 4C protocol execution stays FAIL/DEFERRED. Exploratory compile does not become a payload or wire-semantics back door.
- constitute **full exploratory attack capability**. Master-plan Phase 8 / reconnection MR-6 still require family-shaped discriminating experiments, evidence/verification/finding chain for exploratory work, and anomaly-class hunting. This slice only proves a registry-external hypothesis can enter the normal diagnostic control loop without writing the registry.

Numbering collision, recorded so later readers do not merge gates:

| Document | “MR-5” means |
|---|---|
| `RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md` | **PromotionPipeline** (canonical) |
| `RESEARCH_OS_MASTER_PLAN.md` / `IMPLEMENTATION_SEQUENCE_LOCK.md` Slice 7 | **Exploratory execution** |
| This campaign’s Slice 5 | lock “MR-4” = Evidence-admission trigger only, not canonical MR-5 |

Lock Slice 7 reused the master-plan “MR-5 Exploratory” label. That label is not a PASS on canonical PromotionPipeline.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 7 — Exploratory execution + permanent-family promotion (MR-5)". Eighth slice this campaign. Depends on Slice 4 compiler registry. Last locked reconnection slice in this campaign — not a close of reconnection MR-5 PromotionPipeline.

## Repo evidence before change

SD-G16 (`draft_exploratory_hypothesis.py` + `research/exploratory.py`) persisted a normal `HypothesisRecord` plus `EXPLORATORY_HYPOTHESIS_DRAFTED` audit. Flags (`registry_external`, `requires_human_family_approval`, `may_write_hunter_registry=False`) were metadata only — no consumer compiled or executed the draft, and no use case called `hunter_families.insert` except the `a29` seed.

Human review / Core `Approval` are FindingProposal-bound (`approval.proposal_id` FK → `finding_proposal`). They do **not** currently gate "test this hypothesis". Testing and permanent-family admission were not accidentally the same gate; testing simply had no path.

Existing `Hypothesis` + `ExperimentCompilerRegistry` generic planner can carry exploratory work via `plan_admitted_hypothesis` → `diagnostic.echo`. A new `TemporaryFamilyInstance` type was not required: run-scoped binding is hypothesis + originating audit, keyed by `research_run_id`.

## What changed

Research:

- `exploratory_draft_from_audit` / `assert_ephemeral_registry_binding` — tampered `may_write_hunter_registry=true` fails closed.
- `research/exploratory_compile.py` — ephemeral adapter. Always `family_name=None` so known-family compilers cannot capture a registry-external idea. Compiles only through the generic planner onto `diagnostic.echo`. Rejects a compiled non-diagnostic capability.

Application:

- `ExecuteExploratoryHypothesis` — compatibility/delegation layer over ARC `start` + `run_managed_cycle`. Uses ARC's single `PreparePlannedExperiment` / `ExecutePlannedExperiment` / `EvaluateExperimentFeedback`. Does not write `hunter_family`. Does not construct a second scheduler.
- `PromoteExploratoryFamily` — genuinely new human-gated registry write. Does **not** reuse Finding `Approval`/`HumanReview` (those FKs would conflate family admission with Finding acceptance). `HUMAN_OPERATOR` + `APPROVE` required on the command; CONTROL_PLANE cannot promote. Trail is append-only audit + `hunter_family` insert.

No new Worker capability. Side-effect stays diagnostic SE 0. No generic payload execution. No Candidate/Verification/FindingProposal automation. Epistemic chain unchanged. `PromotionPipeline` (Slice 5) was not modified.

## Files changed

- `src/research_os/research/exploratory.py`
- `src/research_os/research/exploratory_compile.py` (new)
- `src/research_os/application/exploratory_binding.py` (new)
- `src/research_os/application/execute_exploratory_hypothesis.py` (new)
- `src/research_os/application/promote_exploratory_family.py` (new)
- `tests/unit/research/test_exploratory_compile.py` (new)
- `tests/unit/application/test_execute_exploratory_hypothesis.py` (new)
- `tests/integration/test_slice7_exploratory_family.py` (new)

## Schema impact

None. Alembic head remains `a37_001_impact_edge_proof`.

A `family_promotion_review` table was considered. Postgres proved `approval` cannot be reused without a dummy `finding_proposal`. Inventing a FindingProposal to hold family consent would be the exact gate conflation the operator forbade. Command-level HUMAN_OPERATOR + append-only audit is the smallest durable trail that stays off the Finding path.

## Qualification

| Criterion | Status |
|---|---|
| Registry-external lab hypothesis enters experiment path | **PASS** |
| Path is compiler → Core → Worker (ARC-owned dispatch) | **PASS** |
| Permanent registry unchanged by execute | **PASS** |
| Permanent promotion only after HUMAN_OPERATOR APPROVE | **PASS** |
| CONTROL_PLANE cannot promote | **PASS** |
| Negative/deceptive echo mismatch does not create Finding or registry row | **PASS** |
| Core deny does not invoke Worker | **PASS** |
| Exploratory compile cannot raise side-effect (diagnostic SE 0; known-family name cannot capture) | **PASS** |
| Restart/reload does not make exploratory state permanent | **PASS** |
| Tampered `may_write_hunter_registry=true` hard-fails | **PASS** |
| Non-exploratory hypothesis rejected by this path | **PASS** |
| ARC remains sole `research_orchestration` writer on this path | **PASS** |
| No new Worker capability / no arbitrary payload | **PASS** |

Lock hard-fail avoided: no path sets `may_write_hunter_registry` true from model output or by default. Draft constructor still forbids it; execute/promote re-check the raw audit payload.

Not claimed: canonical PromotionPipeline PASS, mutation/protocol execution PASS, or full exploratory attack-capability PASS.

## Test evidence

- Targeted unit: 24 passed (`test_exploratory_compile`, `test_execute_exploratory_hypothesis`, SD-G16).
- Full unit: **1344 passed**, 4 skipped, 44 subtests, 0 failed (was 1328 + 4 skipped before this slice; +16 new).
- Full integration (real PostgreSQL): **189 passed**, 18 subtests, **1 failed** — same pre-existing `test_sd_g4_token_economy` CHECK (`ck_budget_consumption_resource_type` / `MODEL_TOKENS_IN`). Slice 7 postgres tests passed.
- Isolated E2E gates 14–17 (known-family path): **131 passed**.
- Full E2E: **152 passed**, 5 skipped, **4 failed** — same pre-existing `cli_session` module-isolation failures on gate14–17 `no_model` tests when the full suite runs. Isolated, those four pass. Not a Slice 7 regression.

## Explicitly unfinished after this slice

- Canonical PromotionPipeline beyond Evidence admission (Candidate → Verification → FindingProposal).
- Mutation-matrix payload contracts and protocol wire-level execution.
- Exploratory hunting as a real attack class (non-diagnostic compilers, anomaly-backed discriminating experiments, verification/finding chain).

## Next

No further locked reconnection slice. Phase J (`research-osd`) remains deferred — `PHASE_J_DEFERRED.md`. Campaign remainder is recorded in `MAJORITY_CAMPAIGN_COMPLETION_REPORT.md` without treating those unfinished items as closed.
