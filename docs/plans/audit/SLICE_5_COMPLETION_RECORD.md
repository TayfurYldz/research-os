# Slice 5 Completion Record — Promotion trigger (lock MR-4)

Status: CLOSED / PASS.

Naming: `IMPLEMENTATION_SEQUENCE_LOCK.md` Slice 5 is **MR-4 (promotion trigger)**. Operator checkpoint 4C/MR-4 in Slice 4 was the V3 consumer, a different gate. This record is the lock's MR-4.

## Selected slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` §5, "Slice 5 — Promotion trigger (MR-4)" (campaign Phase H). Sixth slice this campaign. Depends on Slice 0 (terminal-state hygiene). Independently useful of Slices 3–4.

## Documented contradiction — audit language vs repository enum

The reconnection audit and lock speak of `SUPPORTED` / `UNSUPPORTED` / `INCONCLUSIVE` assessments.

Repository `AssessmentOutcome` (`src/research_os/research/assessment.py`) is:

- `CONSISTENT_WITH_PREDICTION`
- `CONTRADICTS_PREDICTION`
- `INCONCLUSIVE`
- `EXECUTION_UNUSABLE`
- `NEEDS_MORE_CONTEXT`

There is no `SUPPORTED` or `UNSUPPORTED` member. Repository evidence overrides the audit vocabulary.

Mapped trigger: **`CONSISTENT_WITH_PREDICTION` only**. That is the outcome `admit_evidence()` treats as supporting a diagnostic-echo match claim, and the outcome gate17 already uses as the admission predicate (`rows[-1].assessment_outcome != "CONSISTENT_WITH_PREDICTION"`).

Not auto-triggered (the audit's "none for UNSUPPORTED/INCONCLUSIVE"):

- `INCONCLUSIVE`
- `EXECUTION_UNUSABLE`
- `NEEDS_MORE_CONTEXT`
- `CONTRADICTS_PREDICTION` (closest analogue to "hypothesis not supported"; disconfirming Evidence remains available via explicit `AdmitDiagnosticEvidence`, which is unchanged)

Unknown evaluation strategies (`http.transaction.v1`, etc.) are skipped, not crashed: `AdmitDiagnosticEvidence` has no evaluator for them.

## What changed

New `src/research_os/application/promotion_pipeline.py`:

- `PromotionPipeline.on_assessment(ResearchFeedback)` — the only automatic Assessment→Evidence hop.
- Eligible → `AdmitDiagnosticEvidence` with that `assessment_id`.
- Already-attempted (any `evidence_admission` whose `assessment_ids` contain this assessment) → `SKIPPED_ALREADY_ATTEMPTED`.
- Does not import or call `ProposeCandidateFromEvidence`, `StartCandidateVerification`, `CompleteCandidateVerification`, `SubmitFindingProposal`, `StartHumanReview`, `FinalizeFinding`.

`PromoteOnAssessment` wraps `EvaluateExperimentFeedback.execute()` so every ARC evaluate path — `step()`, `_resume_after_worker()`, and `run_managed_cycle()`'s injected evaluate instance — hits the same hook. `EvaluateExperimentFeedback` itself is unchanged and still creates no Evidence (existing unit tests remain the contract for the inner use case).

`AutonomousResearchController` constructs `self._evaluate = PromoteOnAssessment(EvaluateExperimentFeedback(...), PromotionPipeline(...))`.

`AdmitDiagnosticEvidence`: if `proposal is None` and an `ADMITTED` admission already exists for the selected assessment, return that row. Caller-supplied adversarial proposals still append. This closes the audit's "not idempotent on retry" hole for the automatic hop and for e2e that still call Admit after ARC.

Schema: none.

## Files changed

Production:

- `src/research_os/application/promotion_pipeline.py` (new)
- `src/research_os/application/autonomous_research_controller.py` — wrap evaluate
- `src/research_os/application/admit_diagnostic_evidence.py` — ADMITTED-per-assessment idempotency

Tests:

- `tests/unit/application/test_promotion_pipeline.py` (new)
- `tests/unit/application/test_admit_diagnostic_evidence.py` — second admit of the same assessment is a no-op
- `tests/integration/test_gate12.py` — GATE 12 previously asserted ARC writes zero Evidence. That was the disconnected-promotion invariant this slice removes. Two diagnostic cycles now admit two Evidence rows; Candidate/Finding remain 0. Crash/restart matrix asserts evidence is not duplicated (`after == before` when already present; `<= 1` otherwise) and still never writes Candidate/Finding.

## Qualification

| Criterion | Status |
|---|---|
| Exactly one Evidence-admission attempt per CONSISTENT_WITH_PREDICTION assessment | **PASS** |
| None for INCONCLUSIVE / EXECUTION_UNUSABLE / CONTRADICTS | **PASS** |
| Duplicate trigger / retry does not duplicate Evidence | **PASS** |
| Auto Candidate / Verification / FindingProposal | **not triggered** (hard-fail avoided) |
| EvaluateExperimentFeedback still does not create Evidence by itself | **PASS** |

## Test evidence

- New Slice 5 unit tests: 9 passed (pipeline + ARC hook + wrapper + admit idempotency).
- Full unit suite: **1323 passed**, 4 skipped, 44 subtests, 0 failed.
- Full integration (real PostgreSQL): **186 passed**, 18 subtests, **1 failed** — same pre-existing `test_sd_g4_token_economy.py` `budget_consumption` CHECK. Gate 12 crash matrix 9/9 after assertion update. No new failures.
- Full e2e: **152 passed**, 5 skipped, **4 failed** — same pre-existing `cli_session` isolation failures. No new e2e failures.

## Unresolved / explicitly out of scope

- `DispatchApprovedV3Queue` still uses a raw `EvaluateExperimentFeedback` (not the ARC wrapper). V3 dispatch is not ARC; wiring promotion there is a separate call-site decision, not this slice's lock production file.
- CONTRADICTS_PREDICTION is not auto-admitted. Explicit `AdmitDiagnosticEvidence` still can admit diagnostic mismatch Evidence.
- Candidate / Verification / FindingProposal remain separately invoked.
- Slice 6 (epistemic hardening) is next.

## Next

Slice 6 — ImpactGraph edge proof + severity bound (`IMPLEMENTATION_SEQUENCE_LOCK.md` §5).
