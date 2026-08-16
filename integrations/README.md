# Integrations

Replaceable **adapters** (tools, model providers, optional runtimes). Not the system.

Core and Research must not import this tree. Workers may use an adapter only after Core has authorized the job.

## `models/`

Replaceable ModelPort adapters (OpenAI, Anthropic, Gemini) plus runtime adapters:

- API (`INFERENCE_RUNTIME`)
- CLI/session (`AGENT_RUNTIME`; Codex CLI is not an ordinary inference-only ModelPort)
- LOCAL_MODEL contract (product deferred)
- EXTERNAL_AGENT contract (capability allowlist required; output remains untrusted)

Research, Core, Application, and the benchmark package must not import provider SDKs or spawn CLI processes.

Missing SDK, credential, or CLI is **UNAVAILABLE**, not a benchmark failure and not a research-quality failure. Secrets/session material are composition-root references and must not enter ResearchContext, ModelCallRequest content, SoR, logs, or benchmark reports. Do not scrape undocumented credentials from another application.

Same underlying model through API vs CLI is two different runtime identities. GATE 04B comparative PASS still requires >=2 real comparable runtime configurations.

## `strix/`

Replaceable Strix Integration adapter. Strix is not Research Brain, Core, Research Memory, Evidence authority, or Finding authority.

Path: Application/Core authorization → `StrixIntegration` → Strix runtime.

Returned data is untrusted boundary output. It is not Observation, Evidence, Candidate, or Finding until existing WorkerResult/normalization/admission paths admit it. Diagnostic capability only in GATE 10: `strix.diagnostic.ping`. Security scanning workflows are deferred. Unavailable Strix is PENDING/UNAVAILABLE, not an architecture failure.
