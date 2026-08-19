# Research OS Operations Notes

## SD-G6 — Mutation Engine + OAST Core

### Scope

SD-G6 adds the attacker's planning teeth while keeping every tooth inside the
scope muzzle:

- **Mutation Engine** (`research_os.research.mutation`): deterministic
  variation generation from observed `HTTP_OPERATION` / `EXACT_PATH` nodes.
- **OAST Core** (`research_os.research.oast`): out-of-band callback token
  lifecycle for blind-vulnerability proof-of-concepts.
- **Rate-limit enforcement**: `program_policy.rate_limit_profile` is enforced by
  `ExecutePlannedExperiment` before any Core execution decision.

### Mutation Families

| Family | Rule | Description |
|--------|------|-------------|
| `param_pollution` | duplicate_param / array_param | Duplicate or array-style query parameters. |
| `type_juggling` | type_juggling | Numeric/boolean/float-like string values. |
| `boundary_value` | boundary | Boundary values for numeric/identifier parameters. |
| `auth_header_variation` | auth_header | Authorization and forwarding header variants. |
| `method_override` | override | Method override via header or query parameter. |
| `content_type_confusion` | content_type | Content-Type confusion for mutating requests. |
| `id_or_traversal` | traversal | Path traversal / identifier manipulation candidates. |

All variants are plans only; execution still flows through the existing
`capability → envelope → approval` gate. Variants are confined to
`IN_SCOPE` nodes; `UNKNOWN` and `OUT_OF_SCOPE` nodes produce no variants.

### Audit Payload Rules

- Each variant's `to_public_summary()` produces a size-bounded payload
  (≤ 2 KB total) with no secrets, no full response bodies, and no raw token
  values.
- Forbidden argument keys: `token`, `secret`, `password`, `api_key`,
  `private_key`, `session`, `cookie`.

### OAST Token Lifecycle

1. `AdmitOastCallback` expects the token to exist in `oast_token` table.
2. The callback timestamp is checked against `expires_at`.
3. Expired callbacks are rejected (`OAST_TOKEN_EXPIRED`) but still audited.
4. Valid callbacks are persisted as `sensor_observation` records with
   `sensor_id = "oast.loopback"` and `epistemic_status = UNTRUSTED_EXTERNAL`.
5. `AdmitSensorObservations` then admits the observation as a `DiscoveryFact`
   with `source_status = UNTRUSTED_EXTERNAL`, preserving the epistemic boundary.

### Rate-limit Enforcement

- `RateLimitProfile` is stored in `rate_limit_profile` table.
- `ProgramResearchContext.policy.rate_limit_profile` exposes it to dispatch.
- `ExecutePlannedExperiment._check_rate_limit` counts authorized attempts in the
  rolling window and returns `RATE_LIMIT_DENIED` before Core execution.
- Clock is injected; production code never calls `datetime.now()` directly.

### Live Infrastructure Boundary

- All OAST tests use the `LoopbackOastPort` fixture; live internet callbacks are
  forbidden in tests.
- Real OAST callback infrastructure (HTTP ingress, token DNS, etc.) is a
  separate operational track and is not opened by this gate.

### Runbook

- To run the full SD-G6 test suite on Kali with real PostgreSQL:
  ```bash
  source .venv/bin/activate
  python -m pytest tests/unit tests/contract -q
  python -m pytest tests/integration -q
  python -m pytest tests/e2e -q
  ```
- `GATE_06_STATUS` stays `PENDING` until the independent architect audit seals
  the gate.
