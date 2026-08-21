# Protocol execution capability design (Slice 4 / MR-4)

Status: DESIGN ONLY. No protocol Worker capability is implemented in this slice.

## Decision

`http.transaction` cannot faithfully execute protocol-specialist plans
(`HTTP_REQUEST_SMUGGLING_DESYNC`, `HTTP_CACHE_POISONING_DECEPTION`).

`ExperimentCompilerRegistry` therefore fail-closes those families with:

`BLOCKED_UNSUPPORTED_CAPABILITY` /
`PROTOCOL_WIRE_SEMANTICS_NOT_REPRESENTABLE_BY_HTTP_TRANSACTION`

An APPROVED V3 item for these families is durable, is never marked RUN or
covered, and never reaches a Worker. Approval is not authorization.

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

## Minimal typed primitive (not implemented here)

A future `http.raw_exchange` (name illustrative) would need all of the following
before it can be added to the capability registry:

1. Narrow argument schema, `additionalProperties: false`, no shell/command field.
2. Bounded connection count (1) and bounded request count per connection (explicit, small).
3. Side-effect class derived from the action (read-only probe vs mutate), never from the model.
4. Exact Core/network-envelope interaction: origin still authorized as `http_origin` /
   compiled scope; no raw IP escape.
5. Deterministic normalization of *observations* (what bytes were written/read), not of
   the on-wire request — the request bytes are the experiment.
6. Vulnerable / secure / deceptive fixtures for CL.TE and TE.CL at minimum.
7. Per-step fresh Core authorization: ProtocolPlan is not a one-shot execution token.
   Each `ProtocolParserPlanStep` compiles separately and is re-authorized.
8. No arbitrary raw command/payload escape hatch (no `argv`, no `connect(any_host)`).

Until that contract exists and is fixture-proven, protocol V3 items remain
`BLOCKED_UNSUPPORTED_CAPABILITY`.

## What this slice does implement

- Persist protocol `steps` on the V3 queue row so a future executor has the plan.
- V3 consumer compiles, fail-closes, sets `BLOCKED`, audits the reason.
- No Worker dispatch, no coverage reduction, no silent success.
