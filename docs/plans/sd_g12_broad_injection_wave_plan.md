# SD-G12 Plan — Broad Injection Wave

**Status:** PENDING — P1/P2 implemented; seal pending
**Previous gate:** SD-G11 PASS (`39313ac`)
**Do not confuse with:** old infrastructure `GATE 12` or old `GATE 13`.

## Purpose

SD-G12 opens the broad injection wave without turning the system into a payload
sprayer. The first slice is registry/coverage readiness: input-bearing surfaces
must create explicit coverage debt for high-value injection families before any
active mutation lane can claim coverage.

## Non-Negotiables

- HunterFamily rows are hypotheses, not findings.
- Seed rows must not carry severity, confidence, vulnerability, finding, ground
  truth, or benchmark truth keys.
- Every family remains IN_SCOPE-gated. P1 rows stop at V2 coverage readiness;
  active V3 execution/admission mapping is a later SD-G12 slice.
- Active payload execution remains a later slice and must re-enter Core per
  experiment.

## P1 — Injection HunterFamily Registry

Files:

- `src/research_os/data/postgres/hunter_family_seed.py`
- `tests/unit/data/test_sd_g12_hunter_family_seed.py`

Families:

- SQL injection
- SSTI
- LFI/RFI/path traversal
- Mass assignment
- JWT crypto/claim confusion
- CORS credential-exfiltration chain
- GraphQL authorization/injection
- DOM taint/client-side execution
- AI/LLM prompt-injection, context leakage, and tool abuse

Behavior:

- seeds append-only HunterFamily rows for SD-G12 families;
- targets existing AttackSurfaceGraph node kinds (`HTTP_OPERATION`, `FORM`,
  `API_SPEC`, `ORIGIN`, `TECH`, `JS_BUNDLE`, `PAGE_STATE`);
- requires IN_SCOPE preconditions and V2 validation tier for P1 coverage
  readiness;
- expresses negative controls, metamorphic controls, read-back controls, or
  matrix dimensions as evidence requirements;
- creates coverage-debt cells for input-bearing surfaces without creating
  Evidence, Candidates, Findings, or Worker dispatches.

Evidence:

- Focused checks (2026-08-20): `4 passed`.
- Affected checks (2026-08-20): `39 passed`.
- Full suite (2026-08-20): `1488 passed, 9 skipped, 53 subtests passed`.

## P2 — Bounded Mutation Matrix Planning

Files:

- `src/research_os/research/mutation/matrix.py`
- `tests/unit/research/test_sd_g12_mutation_matrix.py`

Behavior:

- builds deterministic, hash-addressed matrix plans from HunterFamily evidence
  requirements;
- enforces a 30-cell minimum so P1 surfaces cannot be marked exhausted after a
  shallow probe;
- caps generated cells to a bounded maximum and does not emit payload bodies,
  WorkerRequests, Evidence, Candidates, or Findings;
- preserves family-specific controls such as secure/deceptive/read-back,
  metamorphic variants, and tool-denial controls;
- fails closed on unknown matrix dimensions or too-small caps.

Evidence:

- Focused checks (2026-08-20): `4 passed`.
- Affected checks (2026-08-20): `46 passed`.
- Full suite (2026-08-20): `1492 passed, 9 skipped, 53 subtests passed`.
