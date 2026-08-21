# Phase J — `research-osd` deferred

Status: **DEFERRED**. Not implemented. Not qualified. Not a locked Slice 7 deliverable.

## Why this is not the next code slice

`IMPLEMENTATION_SEQUENCE_LOCK.md` and `CAMPAIGN_BASELINE.md` place persistent `research-osd` (RT-5 / dashboard-as-client / systemd / Operator API / SSE) **outside** the locked majority-implementation sequence. Slices 0–7 reconnect research lifecycle and harden runtime fencing/preflight that a daemon would otherwise race.

A daemon that supervised unleased runs was explicitly called out as making the race worse. Slices 0–1 added terminal-state hygiene and lease/fencing. That removes the original blocker, but it does **not** constitute a design for:

- `runtime_instance` identity and crash ownership
- Operator API transport
- SSE / dashboard-as-client contract
- systemd unit vs process supervisor
- how `LocalRunSupervisor` yields to a persistent owner

Project rules forbid treating the stack as decided and forbid silently adding a major architectural component. Phase J needs an explicit design pass before any production daemon, Docker, or new framework work.

## What already exists (do not rebuild)

- `LocalRunSupervisor` — process-local, does not survive restart.
- Dashboard HTTP process as today's operational owner.
- Slice 1 lease/fencing on `research_orchestration`.
- Slice 2 Preflight.

## What must not happen in a freelance Phase J

- Second lifecycle owner beside ARC.
- Dashboard payload overriding authoritative run config.
- Daemon that dispatches Workers without Core authorization.
- Treating process liveness as research Evidence.

## Resume condition

Operator requests an explicit Phase J design (interfaces, ownership, schema) after this campaign's completion report. Until then, `research-osd` remains `NOT_PRESENT`.
