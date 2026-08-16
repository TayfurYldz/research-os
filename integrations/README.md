# Integrations

Replaceable **adapters** (tools, model providers, optional runtimes). Not the system.

Core and Research must not import this tree. Workers may use an adapter only after Core has authorized the job.

## `strix/`

Reserved slot for a Strix adapter. Strix is optional, not a v1 commitment, not Core, not Research Memory, not ModelPort owner, and not an authorization principal.

If implemented later, Strix-as-reasoning-runtime output re-enters as an untrusted structured proposal. Strix-as-tool-runtime output returns as `WorkerResult`.
