# Workers

Out-of-process **execution** runtimes. This is the only layer allowed to perform side effects, and only after Core authorization.

Not part of the `research_os` Python package. Core and Research must not import this tree.

## Rules

- Produce `WorkerResult` only. Do not write PostgreSQL SoR.
- Do not authorize, widen scope, or change budget.
- On redirect or newly discovered assets: stop and request Core re-evaluation.
- In-process Workers are test doubles only.
- First tool-execution environment may be Kali/WSL; that is not architecture.
- Correlation id, timeout, cancellation, and duplicate/retry awareness belong on the Worker contract (`contracts/`).

`python/` is the first runtime slot. Other languages may be added later without changing Core/Research.
