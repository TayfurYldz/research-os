# Protocol execution capability design (Slice 4C)

Status: IMPLEMENTED in pair 4B+4C (`http.raw_exchange` Worker capability +
`ProtocolStepCompiler`). Specialist `ProtocolParserPlan` documents are unchanged.
See `docs/plans/audit/PAIR_4B_4C_COMPLETION_RECORD.md`.

## Decision

`http.transaction` still cannot faithfully execute protocol-specialist plans
(`HTTP_REQUEST_SMUGGLING_DESYNC`, `HTTP_CACHE_POISONING_DECEPTION`). Pair 4C
adds `http.raw_exchange` / `probe` instead of impersonating wire semantics
through the normalized HTTP client.

`ProtocolStepCompiler` binds one `ProtocolParserPlanStep` at a time onto that
capability. An APPROVED ProtocolPlan is compile admission, not an execution
token. Each step gets a fresh Core authorization, attempt/request id, and
budget/rate-limit consumption. Redirect / new origin → STOP +
`REAUTHORIZATION_REQUIRED`. `UNKNOWN_OUTCOME` does not retry the same step.

## Why `http.transaction` is insufficient

The existing capability (`src/research_os/resources/contracts/v1/capabilities/http.transaction.json`
and `worker_runtime/python/http_transaction.py`) is a single normalized HTTP
request:

- one method from a closed enum
- one origin + path
- optional query/headers/body as structured fields
- `network_policy.redirect = STOP`
- `max_requests = 1`
- loopback-only
- client stack owns framing, connection reuse, header folding, and length encoding

Protocol-plan dimensions that the current primitive abstracts away:

| Required semantic | Why `http.transaction` cannot preserve it |
|---|---|
| Conflicting `Content-Length` / `Transfer-Encoding` | Client libraries emit one canonical framing |
| Raw request boundaries / pipelined desync | One request per invocation; no byte-exact write to the socket |
| Duplicate or ambiguous length encoding | Arguments schema has no raw-head field |
| Connection reuse / keep-alive across two requests | `max_requests = 1`; no connection handle |
| Ordered multi-request CL.TE / TE.CL sequences | Would require a session-scoped connection object |
| Exact byte preservation (header case, SP vs TAB, `\n` vs `\r\n`) | Headers are a string map, not a byte buffer |
| Timing / connection state between steps | No connection-state argument |

Faking smuggling through `http.transaction` would produce a false observation
and a false coverage cell. That is forbidden.

## Minimal typed primitive

`http.raw_exchange` / `probe` is now in the capability registry. Constraints that landed:

1. Narrow argument schema, `additionalProperties: false`, closed `framing_profile` enum, no shell/command/raw-bytes field.
2. Bounded writes (max 2) per invocation; connection reuse is one profile, not an open session.
3. Side-effect class is the action minimum (probe = 0), never from the model. Queue-row SE3 remains the approval gate, not execution authorization.
4. Origin/path still authorized as compiled Core scope + loopback envelope.
5. Transition A normalizes observed status/byte counts/fingerprint, not a finding.
6. Per-step fresh Core authorization. One step's outcome does not authorize the next.
7. No argv / connect(any_host). Catalog bytes only.

Vulnerable/secure/deceptive *lab fixtures* for CL.TE vs TE.CL remain operator-owned; the worker emits the catalog profile and records the observation.

## What pair 4C adds on top of Slice 4 persistence

- `ProtocolStepCompiler` → `http.raw_exchange` for each selected step.
- `DispatchApprovedV3Queue` keeps the protocol queue item APPROVED so later steps can be authorized separately.
- Same step id cannot be blindly retried (`HUNT_V3_UNIT_INTENT`).
- Coverage is recorded only after an Observation, never after compile.
