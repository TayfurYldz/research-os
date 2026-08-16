# Application

Use-case coordination for the Control Plane.

Application **sequences** Core decisions, Platform ports, Data Unit of Work, and Transition A.

It does **not** own:

- authorization / scope / budget policy (Core)
- hypothesis semantics (Research)
- PostgreSQL or subprocess implementations
- Evidence / Candidate / Finding

Dependency direction:

```
Interface
  → Application
    → Core / Research
    → Data ports
    → Platform ports
```

Core and Research must not import Application. Concrete adapters are injected.
