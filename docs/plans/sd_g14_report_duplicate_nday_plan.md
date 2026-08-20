# SD-G14 Plan — Report, Duplicate Economics, and n-day Lane

**Status:** PENDING — P1/P2 implemented; seal pending
**Previous gate:** SD-G13 PASS (`2bb0c23`)

## Purpose

SD-G14 turns approved Findings into reviewable report packages, adds duplicate
economics, and introduces the n-day lane without treating public signals as
vulnerability truth. This gate is an operations/review muscle, not a submission
bot.

## Non-Negotiables

- No package exists without an approved Finding.
- Report packages do not auto-submit to any platform.
- Internal duplicate fingerprints are deterministic and source from approved
  Finding content.
- External duplicate signals are advisory only; they do not prove or disprove a
  Finding.
- Packages must not include raw payload/body content or secrets.
- n-day mapping is a lane, not the main brain and not a finding by itself.

## P1 — Approved Finding Report Package

Files:

- `src/research_os/research/report_package.py`
- `src/research_os/application/package_finding_report.py`
- `tests/unit/research/test_sd_g14_report_package.py`
- `tests/unit/application/test_sd_g14_package_finding_report.py`

Behavior:

- builds deterministic `report.package.v1` packages from approved Findings;
- includes summary, proof anchors, reproduction anchors, duplicate-check
  metadata, and safety metadata;
- computes a normalized internal duplicate fingerprint from title, claim, and
  classification;
- accepts external duplicate signals as advisory metadata only;
- rejects secret/raw request keys in package inputs;
- writes an audit event when a package is built;
- does not create Findings, Evidence, Candidates, HumanReview, Approval, or
  platform submissions.

Evidence:

- Focused checks (2026-08-20): `7 passed`.
- Affected checks (2026-08-20): `53 passed`.
- Full suite (2026-08-20): `1514 passed, 9 skipped, 53 subtests passed`.

## P2 — External Duplicate Signal Normalization

Files:

- `src/research_os/research/report_duplicate.py`
- `src/research_os/research/report_package.py`
- `tests/unit/research/test_sd_g14_duplicate_signals.py`

Behavior:

- normalizes disclosed-report or program-page signals into advisory duplicate
  metadata;
- creates SHA-256 signal fingerprints for external duplicate signals;
- emits `POTENTIAL_MATCH` only as advisory metadata, never as a duplicate
  verdict;
- emits `NO_MATCH` for unrelated disclosed reports without changing Finding
  truth;
- rejects provider metadata containing secret/raw request keys;
- preserves external signal fingerprints inside report packages.

Evidence:

- Focused checks (2026-08-20): `11 passed`.
- Affected checks (2026-08-20): `57 passed`.
- Full suite (2026-08-20): `1518 passed, 9 skipped, 53 subtests passed`.
