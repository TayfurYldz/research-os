"""Project maturity flags. These are not research conclusions and are not auto-advanced.

ARCHITECTURE_VALIDATED means Decisions 001–050 and GATE 01–13 architecture exist.

GATE 01 PASS means Research OS can compile authorized program scope and policy into a
fail-closed dispatch envelope that differentiates loopback fixtures from real IN_SCOPE
targets, while keeping UNKNOWN targets observable-but-not-probed. It was validated on
Kali against dedicated PostgreSQL with the full suite (1225 passed, 9 skipped). It does
not prove autonomous vulnerability discovery, arbitrary external internet targeting,
live bug-bounty performance, platform sync to live HackerOne/Bugcrowd endpoints,
OAST callbacks, program-policy actions beyond DENY, or production readiness.

GATE 02 PENDING means the Sensor/Acquisition Plane (SD-G2) is implemented locally
but formal PASS requires Kali + real PostgreSQL validation. This is the Attack
Period sensor plane: passive/semi-passive external census (DNS, certificate
transparency, archive, certificate metadata, technology fingerprint) that produces
SensorObservation records marked UNTRUSTED_EXTERNAL. Sensors never write domain
truth; observations become DiscoveryFact only after deterministic admission
(forbidden-key rejection, scope provenance binding, capped at OBSERVED, admission
receipt). SD-G2 is NOT the old infrastructure GATE 02 (Bounded Research Reasoning
Cycle, a8_001_research_reasoning, closed 2026-08-16); those are separate eras and
must never be confused. GATE 02 does not prove autonomous vulnerability discovery,
active probing, live internet reconnaissance, bug-bounty performance, or production
readiness.

GATE 14 PASS means the controlled authorized local HTTP authorization-differential
pipeline E2E ran on Kali against dedicated PostgreSQL. It does not mean live models,
autonomous discovery quality, bug-bounty performance, or production readiness.

GATE 15 PASS means the controlled multi-scenario ground-truth / false-positive
benchmark passed on Kali against dedicated PostgreSQL. It does not mean live
models, autonomous discovery quality, bug-bounty performance, production
readiness, or broad security-research validation.

GATE 16 PASS means the controlled workflow/state-transition authorization
benchmark plus cross-class discrimination against HTTP_AUTHORIZATION_DIFFERENTIAL
passed on Kali against dedicated PostgreSQL. It does not mean live models,
autonomous discovery quality, bug-bounty performance, production readiness,
or broad security-research validation.

GATE 17 PASS means controlled local multi-hypothesis closed-loop research
selection and adaptive experiment choice were validated against the dedicated
real PostgreSQL test database with truth-blind benchmark execution. It does
not prove general autonomous vulnerability discovery, live model quality, or
production readiness.

GATE 18 PASS means Research OS can transform an admitted research intent into
a typed, per-action capability-bound and scope-evaluated experiment whose
risk level and capability definition are independently verified by Core,
durably bound across restart, and independently rejected by the Worker if
its executable definition does not match. It does not prove autonomous
vulnerability discovery, broad security-research capability, real-world bug
bounty performance, live model quality, production readiness,
crawler/browser/recon capability, or XBOW/Edra parity.

GATE 19 PASS means Research OS can construct and execute typed, capability-bound,
Core-authorized general HTTP experiments using bounded request methods, paths,
queries, headers and bodies, while preserving exact scope evaluation, redirect
reauthorization, capability fingerprint enforcement and Worker execution bounds.
It does not prove autonomous endpoint discovery, crawler/recon capability,
browser automation, arbitrary internet HTTP, broad vulnerability discovery,
real-world bug bounty performance, or production readiness.

GATE 20 PASS means Research OS can establish and isolate authenticated sessions
for explicitly configured identities and execute authorized HTTP experiments
under the correct identity/session context without storing raw credential or
session material in the authoritative research state. It does not prove
autonomous account discovery, browser authentication, arbitrary authentication
mechanisms, durable session-secret recovery after restart, autonomous
vulnerability discovery, real-world bug bounty performance, or production
readiness.

GATE 21 PENDING means the browser/application-state capability implementation
exists locally but formal PASS requires later Kali + real PostgreSQL + real
Chromium validation. It does not prove autonomous discovery, crawler behavior,
bug-bounty performance, browser-based vulnerability discovery, general internet
browsing, or production readiness.

GATE 22 PASS means Research OS can autonomously build and maintain a bounded,
provenance-rich, identity/state-aware attack-surface model of an authorized local
target using real Browser/HTTP observations. It does not prove autonomous
vulnerability discovery, bug-bounty capability, production readiness, generalized
internet reconnaissance, or GATE 23.

PRODUCTION_READY must stay false until operational and live-research gates
that this environment has not passed actually pass.
"""

from __future__ import annotations

ARCHITECTURE_VALIDATED = True
DIAGNOSTIC_E2E_VALIDATED = True
LIVE_MODEL_VALIDATED = False
SECURITY_RESEARCH_VALIDATED = False
PRODUCTION_READY = False

GATE_01_STATUS = "PASS"
GATE_02_STATUS = "PENDING"
GATE_12_STATUS = "PASS"
GATE_13_STATUS = "PASS"
GATE_14_STATUS = "PASS"
GATE_15_STATUS = "PASS"
GATE_16_STATUS = "PASS"
GATE_17_STATUS = "PASS"
GATE_18_STATUS = "PASS"
GATE_19_STATUS = "PASS"
GATE_20_STATUS = "PASS"
GATE_21_STATUS = "PENDING"
GATE_22_STATUS = "PASS"
GATE_04B_STATUS = "PENDING"
SUBSCRIPTION_OAUTH_STATUS = "NOT_IMPLEMENTED"


def maturity_mapping() -> dict[str, object]:
    return {
        "ARCHITECTURE_VALIDATED": ARCHITECTURE_VALIDATED,
        "DIAGNOSTIC_E2E_VALIDATED": DIAGNOSTIC_E2E_VALIDATED,
        "LIVE_MODEL_VALIDATED": LIVE_MODEL_VALIDATED,
        "SECURITY_RESEARCH_VALIDATED": SECURITY_RESEARCH_VALIDATED,
        "PRODUCTION_READY": PRODUCTION_READY,
        "GATE_01": GATE_01_STATUS,
        "GATE_02": GATE_02_STATUS,
        "GATE_04B": GATE_04B_STATUS,
        "GATE_12": GATE_12_STATUS,
        "GATE_13": GATE_13_STATUS,
        "GATE_14": GATE_14_STATUS,
        "GATE_15": GATE_15_STATUS,
        "GATE_16": GATE_16_STATUS,
        "GATE_17": GATE_17_STATUS,
        "GATE_18": GATE_18_STATUS,
        "GATE_19": GATE_19_STATUS,
        "GATE_20": GATE_20_STATUS,
        "GATE_21": GATE_21_STATUS,
        "GATE_22": GATE_22_STATUS,
        "SUBSCRIPTION_OAUTH": SUBSCRIPTION_OAUTH_STATUS,
        "contains_secrets": False,
    }
