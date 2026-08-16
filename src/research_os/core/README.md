# Core

Core owns execution **authorization semantics**:

- authorization source eligibility
- scope decision semantics over pre-evaluated rule matches
- budget authority / eligibility (no persistent decrement)
- human Approval eligibility
- final `ExecutionDecision`

Core does **not** own:

- target parsing, wildcard/CIDR/DNS/redirect/URL normalization
- tool execution
- Worker runtime
- database implementation
- model execution
- Strix
- transport

`ExecutionDecision` is not an execution result. It is not `WorkerResult`, Observation, Evidence, or Finding.

Python classes in this package are **not** language-neutral architectural contracts. Worker wire truth remains `contracts/`.

Models are not authorization principals. Level 3 is denied by default, including when a human Approval is present.
