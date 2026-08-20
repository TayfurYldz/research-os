# SD-G11 Plan — Production Executor Fabric

**Status:** PENDING
**Previous gate:** SD-G10 PASS (`f5b08c0`)
**Do not confuse with:** old infrastructure `GATE 11 — Runtime Routing Integrity`.
**Also not:** `GATE 21 — browser / application state`.

## Purpose

SD-G11 starts the production executor fabric muscle. The goal is to make
authorized Worker execution more field-replayable and evidence-rich without
expanding scope, bypassing Core, or weakening any in-scope capability.

The first slice is deterministic replay manifesting. It does not redispatch a
Worker and does not create Evidence or Findings.

## Non-Negotiables

- Core remains the only authority for scope, budget, side-effect level, and
  capability authorization.
- Replay tooling must never rerun a side-effectful action automatically.
- Secrets and raw session material must not appear in replay manifests.
- Browser/stateful results must be marked environment-sensitive unless a later
  slice proves deterministic replay.
- This work must not modify old infrastructure `GATE 11` status or G21/G22
  maturity.

## P1 — Executor Replay Manifest

Files:

- `src/research_os/application/executor_replay_manifest.py`

Behavior:

- reads persisted Experiment, ExecutionAttempt, WorkerResult, and Observation
  rows;
- produces a deterministic canonical manifest and SHA-256 hash;
- includes correlation, authorization reference, capability/action, side-effect
  level, WorkerResult status, artifact descriptor count, and observation
  payload digests;
- stores raw result, diagnostics, artifacts, and observations as redacted
  digests only;
- classifies replay as:
  - `DETERMINISTIC_REPLAY`;
  - `ENVIRONMENT_SENSITIVE`;
  - `HUMAN_REVIEW_REQUIRED`;
  - `NOT_REPLAYABLE`.

Evidence:

- Unit: deterministic manifest, secret-free output, missing WorkerResult
  fail-closed, browser/stateful environment-sensitive.
- PostgreSQL: G19 authorized HTTP execution now proves deterministic replay
  manifest generation from real ledger rows.
- Focused checks (2026-08-20): `6 passed`.
- Affected checks (2026-08-20): `35 passed, 5 skipped`.
- Full suite (2026-08-20): `1474 passed, 9 skipped, 53 subtests passed`.

## P2 — Replay Bundle Artifacts

Add controlled artifact bundle assembly after the manifest model is stable:
request templates, response digests, screenshot/trace descriptors where present,
and privacy-preserving redaction metadata.

## P3 — Production Executor Vertical Slice

Extend the manifest contract to HTTPS/browser/API workers with secure,
vulnerable, deceptive, and scope-escape fixtures. No worker can reach outside
the Core-issued envelope; every redirect still requires reauthorization.

## G21 Boundary Note

Current local check (2026-08-20):

- real Chromium G21 browser lab ran: `22 passed, 5 skipped`;
- required cgroup mode failed closed because `/sys/fs/cgroup/init.scope` is not
  a writable delegated subtree.

Therefore G21 remains `PENDING`. SD-G11 P1 does not claim or depend on G21 PASS.
