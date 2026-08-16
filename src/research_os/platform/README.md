# Platform

Ports and first adapters for Control Plane infrastructure.

## WorkerPort

`research_os.platform.worker.WorkerPort` is the invocation contract.

`LocalProcessWorkerAdapter` is the **first local transport**:

- one-shot child process
- JSON WorkerRequest on stdin
- JSON WorkerResult on stdout
- stderr diagnostics
- `shell=False`

This adapter is **not** architecture. Remote Workers may use another transport with the same canonical schemas.

Core and Research must not import `local_process_worker` or `subprocess`.

Development defaults (configurable): stdout protocol payload 1 MiB; stderr diagnostics 64 KiB; timeout 30s. Overflow of stdout is a protocol failure, not a truncated WorkerResult.

Cancellation: first implementation is local process termination (timeout/kill). Distributed cancellation is a later runtime slice, not a protocol product now.

Child environment is constructed explicitly. Database URLs, model API keys, and application credentials are not forwarded. `RESEARCH_OS_WORKER_ID` is the configured opaque identity. PID is diagnostic only.

## Invocation vs WorkerResult

`WorkerInvocationOutcome.invocation_status` is a Control Plane runtime outcome.

It is **not** `WorkerResult.status`.

A crash, timeout, invalid JSON, or correlation mismatch does **not** produce a WorkerResult for Transition A.

## Contract validation

Runtime Draft 2020-12 validation loads `contracts/v1` and resolves URN `$id` locally. It does not fetch the network. `scripts/check_contracts.py` remains structural lint only.
