# Research OS — Research Lifecycle Reconnection Audit

**Companion to:** `CURRENT_ARCHITECTURE_SNAPSHOT.md`, reconciles against `RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md`
**Status:** AUDIT — no production code changed.

---

## 1. Path A (ARC) — actual call graph

```text
LocalRunSupervisor._run() [thread loop]
  → LocalRunSupervisor.tick()                                          local_run_supervisor.py:73-98
    → AutonomousResearchController.step(command)                       autonomous_research_controller.py:299
      → SelectResearchOpportunities.execute()                          select_research_opportunities.py:56-58
          → propose_diagnostic_opportunities()                         research/exploration.py
          → select_research_opportunities()                           research/exploration.py
          [PERSISTED HANDOFF: ResearchOpportunityRecord, ResearchSelectionRecord]
      → ProposeResearchHypothesis.execute()                            propose_research_hypothesis.py:112
          → ResearchContextBuilder.build()                             research/context.py
          → generate_proposal() → ModelPort.complete(GENERATOR)        research/cycle.py:144-168   [IMPLEMENTED CALL]
          → generate_challenge() → ModelPort.complete(FALSIFIER)       research/cycle.py:171-197   [IMPLEMENTED CALL]
          → admit_hypothesis()                                        research/admission.py
          → plan_admitted_hypothesis()                                 research/planning.py
          [PERSISTED HANDOFF: HypothesisRecord, ResearchReasoningRecord, ResearchAdmissionRecord]
      → PreparePlannedExperiment.execute()                             prepare_planned_experiment.py
          [PERSISTED HANDOFF: ExperimentRecord(PLANNED), ExperimentPlanRecord]
      → ExecutePlannedExperiment.execute()                             execute_planned_experiment.py:201-213
          → evaluate_execution()  [CORE, fresh per attempt]            core/execution.py:84-171    [IMPLEMENTED CALL]
          [PERSISTED HANDOFF: ExecutionAttemptRecord(AUTHORIZED) — only on ALLOW]
          → dispatch(): attempt→DISPATCHING (committed) → WorkerPort.invoke()   [IMPLEMENTED CALL]
          → IngestCompletedWorkerInvocation.execute()                  ingest_worker_invocation.py
          [PERSISTED HANDOFF: WorkerResultRecord, ObservationRecord]
      → EvaluateExperimentFeedback.execute()                           evaluate_experiment_feedback.py
          [PERSISTED HANDOFF: HypothesisAssessmentRecord]               ← ARC's automatic progression STOPS here
      → _complete_cycle() / _stop()
          [PERSISTED HANDOFF: ResearchOrchestrationRecord, ResearchCycleRecord]
```

**Edge labels applied per the requested taxonomy:** every arrow above is `IMPLEMENTED CALL` (a real Python call happens in the current process) followed in most cases by a `PERSISTED HANDOFF` (a durable record is written that the next step reloads). No `MANUAL TRIGGER` or `PLANNED ONLY` edges exist inside this graph — the ARC's own path, up to `HypothesisAssessmentRecord`, is fully wired and automatic. What is `MISSING` is everything downstream of the assessment (see §7).

Recovery re-entry uses the same functions keyed off `current_phase` (`autonomous_research_controller.py:311-360`); it is not a separate code path, just a different starting point in the same graph.

---

## 2. Hunter/Coverage — actual call graph and exact divergence point

```text
[no production caller exists for this graph — see below]
RunHuntScheduler.execute()                        run_hunt_scheduler.py:73          [MANUAL TRIGGER — test/CLI only]
  → build_coverage_hypothesis_view()              application/coverage/hypothesis_view.py
  → compute_coverage_debt()                       research/coverage/debt.py
  → schedule_cells() → HunterScore per cell        research/scheduler/score.py
  [PERSISTED HANDOFF: none automatic — schedule is returned in-process]
RunHuntCycle.execute(schedule=...)                run_hunt_cycle.py:57              [MANUAL TRIGGER — caller must pass schedule]
  → GenerateHuntHypotheses.execute()               generate_hunt_hypotheses.py
      [PERSISTED HANDOFF: HypothesisRecord — SAME table/type ARC uses, origin_reference=family_id]
  → ValidateHuntTiers.execute()                    hunt_validation.py
      → V1/V2 evaluators; if V3 tier required:
      → uow.hunt_v3_queue.insert(HuntV3QueueRecord(state="PENDING"))   [PERSISTED HANDOFF — terminus]
ApproveHuntV3Queue.execute()                       hunt_v3_queue_approval.py:88     [MANUAL TRIGGER — human approval only]
  → uow.hunt_v3_queue.set_state(queue_id, "APPROVED")                  [PERSISTED HANDOFF — terminus, MISSING beyond here]
```

**First shared object, not shared caller:** ARC and the Hunter path both read/write `hypothesis` (same `HypothesisRecord` type, same table) and both live under one `research_run_id`. They share **no orchestrating function call**. The exact divergence:

- ARC's first decision call: `AutonomousResearchController.step()` → `SelectResearchOpportunities.execute()` (`autonomous_research_controller.py:389`).
- Hunter's first decision call: an external caller (today: only test code) → `RunHuntScheduler.execute()` (`run_hunt_scheduler.py:73`) and/or `RunHuntCycle.execute()` (`run_hunt_cycle.py:57`).

Neither function calls the other, and nothing calls both in one production path. Confirmed by repo-wide constructor search: `RunHuntCycle(` and `RunHuntScheduler(` appear only in `tests/integration/test_sd_g5_hunt_cycle.py`, `tests/integration/test_sd_g9_hunterscore_scheduler.py`, `tests/unit/application/test_hunt_cycle.py`, `tests/unit/application/test_run_hunt_scheduler.py`.

**Verdict: Hunter/Coverage path IS NOT currently connected to ARC's execution lifecycle.** (`EXISTING_BUT_DISCONNECTED`)

---

## 3. V3 queue — current lifecycle

```text
HuntV3QueueRecord.state ∈ {"PENDING", "APPROVED", "RUN", "BLOCKED"}     data/records.py:2647; a29 CHECK constraint
insert(state="PENDING")             hunt_validation.py:233                        [only producer]
set_state(_, "APPROVED")            hunt_v3_queue_approval.py:88                  [only mutator found]
set_state(_, "RUN")                 — ZERO occurrences anywhere in src/           [MISSING]
```

Exhaustive `rg` across `src/research_os` for: `APPROVED`, `HUNT_V3_QUEUE_APPROVED`, `hunt_v3_queue`, `state == "APPROVED"`, `.set_state(..., "RUN")`, `list_pending_for_research_run(` found:
- `HUNT_V3_QUEUE_APPROVED` audit event emitted only by `hunt_v3_queue_approval.py`.
- `list_pending_for_research_run()` exists as a repository method with **zero application-layer callers**.
- No code anywhere converts an `APPROVED` (or any) V3 queue item into `ExperimentIntent`, `ExperimentPlan`, `PreparePlannedExperiment`, `ExecutePlannedExperiment`, or `WorkerPort.invoke`.
- The module docstring for `hunt_v3_queue_approval.py` itself states it "does not dispatch Workers", and the implementation matches: only `set_state` + an audit event on approval.

**Verdict: V3 queue post-approval has no execution consumer today. `RUN` is a declared-but-unreachable state value. Classification: `MISSING`.**

---

## 4. Mutation — current lifecycle

Two distinct, non-interoperating generations exist:

**Generation 1 — `MutationMatrix` (SD-G12 planning artifact):**
```text
build_mutation_matrix(family) → MutationMatrixPlan{cells: tuple[MutationMatrixCell,...], matrix_hash}
                                                                       research/mutation/matrix.py:53-86  [PLANNED ONLY]
  → only production caller: hunt_validation._v3_arguments_for_family()  hunt_validation.py:271-284
      → discards all cells, stores only {matrix_hash, matrix_version, cell_count, dimension_count,
         control_count, "worker_dispatch": "forbidden_until_operator_approval"}   [PERSISTED HANDOFF — into V3 queue metadata, terminus]
```

**Generation 2 — `MutationEngine` (SD-G6, older, actually produces per-node variants):**
```text
MutationEngine.mutate() / mutate_for_node() → tuple[MutationVariant, ...]         research/mutation/engine.py:39-63
  MutationVariant carries: capability_id, action, arguments, target_reference (a genuinely concrete,
  executable-shaped payload — NOT metadata-only, unlike MutationMatrixPlan)       research/mutation/types.py:34-47
  → RecordMutationVariants.execute()                                             record_mutation_variants.py:51-74
      → persists only AuditEventRecord(event_type="MUTATION_VARIANT_PLANNED", payload=summary)  [terminus]
  → mutation_variant_to_intent() converts a MutationVariant → ExperimentIntent    research/mutation/intent.py:10-32
      [PLANNED ONLY / test-only bridge: only caller is
       tests/unit/research/test_mutation_engine.py:184-192, which itself then calls
       compile_experiment_intent() → ExperimentPlan and stops. No application use case performs
       this conversion in production, and PreparePlannedExperiment would reject the resulting plan
       because mutation_variant_to_intent() uses variant.variant_id as hypothesis_id, and no real
       Hypothesis row with that id exists (prepare_planned_experiment.py:57-62 requires one).]
```

**Do not collapse these two generations into one statement:** `MutationEngine`/`MutationVariant` (older, SD-G6) is closer to "executable-shaped" than `MutationMatrixPlan` (newer, SD-G12), which is explicitly metadata-only planning ("Does not create payloads or dispatch" — `research/mutation/matrix.py:81-86` docstring). Neither reaches Core/WorkerPort in production. The generic `compile_experiment_intent()` bridge (`research/compiler.py:84-142`) exists and works when unit-tested directly, but nothing in `run_hunt_cycle.py`, `hunt_validation.py`, or the ARC calls it for mutation output.

**Verdict: `MutationMatrix` = `PLANNING_ONLY`. `MutationEngine` = produces concrete variants but they terminate as audit-event summaries; the intent→plan bridge exists in isolation and is not connected to any production caller.**

---

## 5. Protocol specialist — current lifecycle

```text
build_protocol_parser_plan(family) → ProtocolParserPlan{steps: tuple[ProtocolParserPlanStep,...], plan_hash}
                                                                    research/protocol/parser_plan.py:63-68  [PLANNED ONLY]
  → only production caller: hunt_validation._v3_arguments_for_family() (protocol.parser branch) hunt_validation.py:285-309
      → discards all steps, stores only {protocol_plan_hash, plan_version, protocol_lane, step_count,
         dimension_count, control_count, "approval_required": "SE3",
         "worker_dispatch": "forbidden_until_se3_approval"}       [PERSISTED HANDOFF — into V3 queue metadata, terminus]
```

No code iterates `ProtocolParserPlan.steps`, converts a step to `ExperimentIntent`/`ExperimentPlan`, creates a per-step Experiment, or performs per-step Core reauthorization. The design intent in `docs/plans/sd_g13_protocol_parser_specialist_plan.md:21` ("active execution remains Core-authorized per step") describes a slice that was never implemented; per this audit's rules that gap is recorded here, not implemented.

**Verdict: `PLANNING_ONLY`.** Terminus is identical in shape to Mutation's terminus: a metadata summary embedded in a `PENDING` V3 queue row that (per §3) has no consumer beyond `APPROVED`.

---

## 6. Exploratory hypothesis generator — current lifecycle

```text
DraftExploratoryHypothesis.execute()                draft_exploratory_hypothesis.py:71-96
  → draft_registry_external_hypothesis()             research/exploratory.py
  [PERSISTED HANDOFF: HypothesisRecord — SAME table/type as ARC and Hunter use, origin_reference=audit_event_id]
  [PERSISTED HANDOFF: AuditEventRecord("EXPLORATORY_HYPOTHESIS_DRAFTED", carrying status="HYPOTHESIZED",
   registry_external=True, requires_human_family_approval=True, may_write_hunter_registry=False,
   not_evidence=True, not_candidate=True, not_finding=True — research/exploratory.py:107-119)]
```

Because it writes a normal `HypothesisRecord`, ARC's own opportunity selector (`select_research_opportunities.py:69` reads `uow.hypotheses.list_for_research_run(...)`) can see it and could in principle use it as context for a *new* model-generated hypothesis — but ARC does not compile or execute the exploratory draft itself; it can only influence future model reasoning. There is no code path `DraftExploratoryHypothesis.execute() → compiler → PreparePlannedExperiment → ExecutePlannedExperiment`. The stated invariants (`requires_human_family_approval`, `may_write_hunter_registry=False`) are metadata fields carried into an audit payload — no consumer reads `requires_human_family_approval` or enforces it, and no application use case ever calls `uow.hunter_families.insert(...)` (the only writer of that table is the `a29` migration's `op.bulk_insert`). The "promote validated exploratory pattern → permanent HunterFamily, human-reviewed" step described in `RESEARCH_OS_HUNTER_RECONNECTION_PLAN.md §11` and `sd_g16_exploratory_hypothesis_generator_plan.md` is **not implemented** — there is no code that turns a repeated exploratory success into a `HunterFamily` row.

**Verdict: `PARTIAL_EXECUTION`** — a genuine shared-type Hypothesis is created and is visible to ARC's context, but there is no direct compile/execute path for it and no implemented permanent-family-promotion gate.

---

## 7. Promotion — current lifecycle (Assessment → Finding)

| Transition | Domain logic | Application use case | ARC-automatic? | Durable? | Restart-safe? |
|---|---|---|---|---|---|
| Assessment → EvidenceProposal | `research/evidence.py:252-372` (per-classification proposal builders) | proposal built inline inside `AdmitDiagnosticEvidence` (`admit_diagnostic_evidence.py:105-118`) — no standalone use case | **No.** ARC's last automatic write is `HypothesisAssessmentRecord` (`evaluate_experiment_feedback.py:95-113`); zero callers of `AdmitDiagnosticEvidence` from ARC. | Assessment: yes (append-only). Proposal itself: process-memory only, no "pending proposal" table. | Assessment: yes. Proposal: not independently resumable. |
| EvidenceProposal → Evidence | admission gates `research/evidence.py:375-563` | `AdmitDiagnosticEvidence.execute()` (`admit_diagnostic_evidence.py:70-201`) | **No** (zero callers from ARC or dashboard; only test callers). | Yes — `evidence`, `evidence_observation`, `evidence_admission` all append-only (`a10_001_evidence_admission.py`). | Completed/rejected admissions reload cleanly; **not idempotent on retry** (no existing-admission check before insert). |
| Evidence → Candidate | `research/candidate.py:242-489` (`OPEN` only, direct `OPEN→VALIDATED` illegal) | `ProposeCandidateFromEvidence` (`propose_candidate.py:60-115`) | **No** (zero ARC/dashboard callers). | Yes — `candidate`, `candidate_admission` (`a11_001_candidate_verification.py`). | Not idempotent on retry (can create a second Candidate from the same Evidence). |
| Candidate → Independent Verification | lifecycle legality `research/candidate.py:47-78`; independence rule requires different Evidence/experiment/request/observation ids `research/verification.py:388-397,707-727` | `StartCandidateVerification` (`start_candidate_verification.py:43-68`), `CompleteCandidateVerification` (`complete_candidate_verification.py:74-204`) | **No** (zero ARC/dashboard callers; ARC never schedules a reproduction experiment for a Candidate). | Candidate state + `verification` row durable (append-only). | **Partially.** `VerificationPlan` itself and the Candidate→reproduction-experiment binding are **not persisted** — a DB read can identify a `VERIFYING` Candidate but not which experiment was intended as its reproduction; `CompleteCandidateVerificationCommand` requires an externally supplied `reproduction_experiment_id`. |
| Verification → FindingProposal | `research/finding_proposal.py:377-566` (requires `VALIDATED` Candidate, exact Evidence/Verification set match, ImpactChain validation) | `SubmitFindingProposal` (`submit_finding_proposal.py:68-172`) | **No** (zero ARC/dashboard callers). | Yes — `finding_proposal` (`a12_001_finding_acceptance.py`). | Reloadable; **not idempotent** (no existing-proposal guard against duplicate submission). |
| FindingProposal → HumanReview | `research/finding_proposal.py:99-105,588-596` | `StartHumanReview` (`start_human_review.py:31-43`), `RecordHumanReview` (`record_human_review.py:49-116`) | **No — but this is the first stage with a wired dashboard entrypoint.** `POST /api/finding-proposals/{id}/review` (`dashboard.py:977-1008`), operator-triggered, requires `HUMAN_OPERATOR` actor. | Yes — `human_review` append-only, unique on `(proposal_id, content_fingerprint)`. | `RecordHumanReview` is idempotent (reloads existing review); `StartHumanReview` is not retry-idempotent once state has changed, but committed state is unambiguous. |
| HumanReview → Core Approval → Finding | `core/approval.py` (subject/actor/decision validation) + `research/finding_proposal.py:599-693` (full Finding-creation gate) | `FinalizeFinding` (`finalize_finding.py:58-245`) | **No — dashboard-wired.** `POST /api/finding-proposals/{id}/finalize` (`dashboard.py` route table). | Yes — `approval`, `finding` append-only; unique proposal constraint on `finding`. | **Explicitly idempotent** — existing Finding/rejected-proposal return the same result on retry (`finalize_finding.py:63-90`). |

**Definitive verdict (matches both direct verification and the dedicated sub-agent audit):** There is no true autonomous `PromotionPipeline` today. ARC's automatic authority ends at `HypothesisAssessmentRecord` + cycle completion. Every later step is an independently-invokable, well-built, well-tested domain/application use case that currently requires an external caller — for Evidence/Candidate/Verification/FindingProposal that caller is **only test code**; for HumanReview/Finalize it is a manual dashboard operator action.

### ImpactGraph specifics
- Consumed at `FindingProposal` submission time only (`submit_finding_proposal.py:181-208`) — validated for structural correctness and evidence-backed proof on **nodes**.
- Every node requires non-empty `proof_refs` (`research/impact/chain.py:36-53`), resolved against admitted Evidence/Observation/Experiment (`application/impact/proof_resolver.py:23-64`).
- **Edges carry no proof_refs** (`research/impact/chain.py:66-82`; DB schema confirms, `a31_001_impact_graph.py:68-86`) — a causal/escalation relationship between two proven nodes can be asserted without independent proof of that specific relationship.
- Severity is **not** fully evidence-bounded: `ScoreFindingSeverity` accepts caller-supplied `data_sensitivity`/`affected_scope` (`score_finding_severity.py:28-32`) that can independently drive a P0 score (`research/validation/severity.py:158-165`) without additional Evidence. The severity result is an audit-event attachment on the proposal, not a field on `FindingRecord` (`data/records.py:1152-1167` has no severity column).

---

## 8. Missing bridges (ranked by blocking severity for the "smallest correct reconnection")

1. **No `ResearchOpportunity`-level unification** — ARC only ever produces diagnostic opportunities (`propose_diagnostic_opportunities`); Hunter/Coverage opportunities never enter the ARC opportunity pool. This is the single highest-leverage bridge: everything else in the Hunter plan depends on it.
2. **No family→compiler registry** — known `HunterFamily` rows never become typed `ExperimentPlan`s; only the generic `compile_experiment_intent()` exists and it is unused in production for Hunter/Mutation/Protocol output.
3. **No V3 post-approval consumer** — `APPROVED` is a dead-end state.
4. **No Assessment→Evidence auto-trigger** — the entire promotion chain below `HumanReview` requires an external caller; nothing decides "this SUPPORTED assessment should now attempt Evidence admission."
5. **No permanent-family-promotion workflow** for exploratory hypotheses.
6. **No proof requirement on ImpactGraph edges** and **no evidence-bound ceiling on caller-supplied severity fields** — these are genuine epistemic defects, independent of the reconnection work, that should be fixed in the same generation of change since they touch the same files (`impact/chain.py`, `score_finding_severity.py`).

---

## 9. Proposed minimal reconnection (design only — do not implement in this phase)

This section states direction, not code. It follows the master plan's `MR-1..MR-6` sequence and reuses every existing component identified above; it does not introduce a second lifecycle owner.

- **MR-1 (Unified Opportunity):** Add a `HunterCoverageOpportunitySource` that wraps `RunHuntScheduler`/`build_coverage_hypothesis_view`/`compute_coverage_debt` and emits `ResearchOpportunityRecord` rows into the *same* table ARC's `SelectResearchOpportunities` already reads. ARC's selector already unions arbitrary opportunity rows for a run — the diagnostic-only behavior is a property of what currently *writes* that table, not of the read path (`select_research_opportunities.py:95-119` reads generically). This is the lowest-duplication bridge: no change to ARC's read side is strictly required, only a new opportunity producer.
- **MR-2 (Compiler registry):** Add a small `ExperimentCompilerRegistry` keyed by `HunterFamily.family_id`/capability id, with `compile_experiment_intent()` (already exists, `research/compiler.py`) as the generic fallback for anything without a specific compiler. First concrete compilers: authorization-differential and state-transition (evaluators already exist under `research/evaluators/`), mutation-matrix-cell (bridges `MutationMatrixCell` → concrete arguments instead of discarding cells in `hunt_validation.py:271-284`), protocol-step (bridges one `ProtocolParserPlanStep` at a time instead of discarding all steps in `hunt_validation.py:285-309`).
- **MR-3 (V3/mutation/protocol bridge):** A new Application use case (not a second ARC) that: reads `APPROVED` `hunt_v3_queue` rows for a run, calls the family's compiler, calls `PreparePlannedExperiment` + `ExecutePlannedExperiment` (both already exist and already do fresh Core authorization), and sets state to `RUN` only after a `DISPATCHED`/terminal outcome is recorded. This closes §3's dead end using existing execution primitives.
- **MR-4 (Promotion trigger):** A new Application use case, triggered by ARC after a `SUPPORTED` assessment (one added call in `EvaluateExperimentFeedback`'s caller, or a small `PromotionPipeline.on_assessment()` hook invoked right after `_persist_cycle` in ARC) that calls `AdmitDiagnosticEvidence`-equivalent logic for the matching classification, then stops — Candidate/Verification/FindingProposal remain separately gated exactly as they are today (this preserves the human-controlled tail; it only removes the missing *first* hop).
- **MR-5 (Exploratory execution):** Give `DraftExploratoryHypothesis` output a `run-scoped, ephemeral` compiler path through the same MR-2 registry with `may_write_hunter_registry` enforced by the *new* use case (today it is metadata only) — and add the missing permanent-family-promotion human-review use case as a genuinely new, small piece (there is nothing existing to reuse here).
- **Epistemic fix (independent of reconnection, same-generation change):** add `proof_refs` to `ImpactChainEdge` (schema-additive) and bound `ScoreFindingSeverity`'s `data_sensitivity`/`affected_scope` inputs to values derivable from admitted Evidence/ImpactGraph, not arbitrary caller input.

---

## 10. Production files likely affected in the NEXT phase (not touched in this audit)

`select_research_opportunities.py` (or a new `OpportunitySource` composition point), `run_hunt_scheduler.py`/`run_hunt_cycle.py` (new producer wiring, not rewritten), `hunt_validation.py` (stop discarding matrix cells/protocol steps once a compiler exists), a new `application/experiment_compiler_registry.py`, `hunt_v3_queue_approval.py`/a new `application/dispatch_approved_v3_queue.py`, `autonomous_research_controller.py` (one new call after assessment persistence — not a rewrite), `research/impact/chain.py` + `alembic/versions/` (new additive migration for edge `proof_refs`), `score_finding_severity.py`.

## 11. Tests required before implementation (write first, per repo discipline)

- A test proving Hunter-sourced `ResearchOpportunityRecord`s are visible to and selectable by `SelectResearchOpportunities` without changing diagnostic-opportunity behavior (regression guard for MR-1).
- A test proving a known `HunterFamily` produces a schema-valid `ExperimentPlan` via its specific compiler, and that an unknown family falls back to the generic compiler without silently understating `side_effect_level` (MR-2).
- A test proving an `APPROVED` V3 item, once dispatched, cannot be dispatched twice (idempotent `RUN` transition) and that a stale/expired approval is rejected by fresh Core authorization even after `APPROVED` (MR-3 — this is the literal hard-fail condition "approval used as authorization" from the master plan).
- A test proving `UNSUPPORTED`/`INCONCLUSIVE` assessments do **not** trigger Evidence admission, and `SUPPORTED` ones do exactly once (no duplicate Evidence per assessment) (MR-4).
- A test proving `ImpactChainEdge` without a resolvable proof reference is rejected at admission (new invariant, additive).
- A test proving `ScoreFindingSeverity` cannot reach P0 purely from caller-supplied fields without a corresponding Evidence-backed impact node of matching severity class (new invariant, additive).
