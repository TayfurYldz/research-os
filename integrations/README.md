# Integrations

Replaceable **adapters** (tools, model providers, optional runtimes). Not the system.

Core and Research must not import this tree. Workers may use an adapter only after Core has authorized the job.

## `models/`

Replaceable ModelPort adapters (OpenAI, Anthropic, Gemini). Research, Core, Application, and the benchmark package must not import provider SDKs.

Missing SDK or credential is **UNAVAILABLE**, not a benchmark failure and not a research-quality failure. Secrets are composition-root environment references and must not enter ResearchContext, ModelCallRequest content, SoR, logs, or benchmark reports.

## `strix/`

Reserved slot for a Strix adapter. Strix is optional, not a v1 commitment, not Core, not Research Memory, not ModelPort owner, and not an authorization principal.

If implemented later, Strix-as-reasoning-runtime output re-enters as an untrusted structured proposal. Strix-as-tool-runtime output returns as `WorkerResult`.
