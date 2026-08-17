"""Combined local HTTP lab for GATE 17. Bind 127.0.0.1 only.

Exposes object-authorization and workflow-authorization surfaces on one origin.
Fixture kinds are harness-internal. Responses never include scenario ids or
ground-truth labels.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from e2e.lab.http_ground_truth_lab import (
    ACTOR_HEADER,
    CONTRADICTORY as OBJECT_CONTRADICTORY,
    DECEPTIVE_200 as OBJECT_DECEPTIVE,
    EXTERNAL_REDIRECT,
    OWNED_ACCOUNTS,
    PROBE_REQUESTS_PER_CYCLE,
    PUBLIC_OBJECT,
    SECURE_OBJECT,
    TRUE_BOLA,
)
from e2e.lab.http_workflow_lab import (
    ACTOR_ROLES,
    CONTRADICTORY as WORKFLOW_CONTRADICTORY,
    DECEPTIVE_200 as WORKFLOW_DECEPTIVE,
    SECURE_ROLE_ENFORCEMENT,
    TRUE_ROLE_BYPASS,
    _observed,
    _seed,
)

EXTRA_ACCOUNTS = {
    "carol": {"account_id": "carol", "owner": "carol", "marker": "lab-carol-marker"},
    "dave": {"account_id": "dave", "owner": "dave", "marker": "lab-dave-marker"},
}
ACCOUNTS = {**OWNED_ACCOUNTS, **EXTRA_ACCOUNTS}
ACTORS = set(ACCOUNTS) | set(ACTOR_ROLES)


class ResearchSelectionLab:
    """One loopback origin with object and workflow families."""

    def __init__(
        self,
        object_kind: str,
        workflow_kind: str,
        *,
        object_kind_b: str | None = None,
    ) -> None:
        self.object_kind = object_kind
        self.workflow_kind = workflow_kind
        self.object_kind_b = object_kind_b
        self.object_get_count = 0
        self.workflow_request_count = 0
        self.records = _seed(workflow_kind)
        self._lock = threading.Lock()
        self._server = _LabServer(("127.0.0.1", 0), _ResearchHandler, lab=self)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def origin(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> str:
        self._thread.start()
        return self.origin

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    def __enter__(self) -> ResearchSelectionLab:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.stop()


class _LabServer(ThreadingHTTPServer):
    def __init__(self, address, handler, *, lab: ResearchSelectionLab) -> None:
        self.lab = lab
        super().__init__(address, handler)


class _ResearchHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def do_PUT(self) -> None:
        self._send(405, {"error": "GET and POST only"})

    def do_PATCH(self) -> None:
        self._send(405, {"error": "GET and POST only"})

    def do_DELETE(self) -> None:
        self._send(405, {"error": "GET and POST only"})

    def _handle(self, method: str) -> None:
        lab: ResearchSelectionLab = self.server.lab  # type: ignore[attr-defined]
        parsed = urlparse(self.path)
        actor = self.headers.get(ACTOR_HEADER)
        try:
            self._respond(lab, method, parsed.path, actor)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            return

    def _respond(
        self,
        lab: ResearchSelectionLab,
        method: str,
        path: str,
        actor: str | None,
    ) -> int:
        if path == "/redirect":
            return self._redirect()
        parts = [item for item in path.split("/") if item]
        if parts and parts[0] in {"vulnerable", "secure"}:
            if method != "GET":
                return self._send(405, {"error": "GET only"})
            with lab._lock:
                lab.object_get_count += 1
                count = lab.object_get_count
            return self._object(lab, parts, actor, count)
        if parts and parts[0] in {"workflow", "control"}:
            with lab._lock:
                lab.workflow_request_count += 1
                count = lab.workflow_request_count
            return self._workflow(lab, method, parts, actor, count)
        return self._send(404, {"error": "not found"})

    def _object(
        self,
        lab: ResearchSelectionLab,
        parts: list[str],
        actor: str | None,
        count: int,
    ) -> int:
        if len(parts) != 3 or parts[1] != "accounts":
            return self._send(404, {"error": "not found"})
        area, _, account_id = parts
        kind = lab.object_kind
        if lab.object_kind_b is not None and account_id in EXTRA_ACCOUNTS:
            kind = lab.object_kind_b
        if not actor or actor not in ACTORS:
            return self._send(401, {"error": "unauthenticated"})
        account = ACCOUNTS.get(account_id)
        if account is None:
            return self._send(404, {"error": "unknown account"})
        if area == "secure":
            if actor != account["owner"]:
                return self._send(403, {"error": "forbidden"})
            return self._send(200, dict(account))
        return self._vulnerable(kind, actor, account, count)

    def _vulnerable(
        self,
        kind: str,
        actor: str,
        account: dict[str, Any],
        count: int,
    ) -> int:
        later = count > PROBE_REQUESTS_PER_CYCLE
        if kind == SECURE_OBJECT:
            if actor != account["owner"]:
                return self._send(403, {"error": "forbidden"})
            return self._send(200, dict(account))
        if kind == PUBLIC_OBJECT:
            payload = dict(account)
            if actor != account["owner"]:
                payload["visibility"] = "PUBLIC"
            return self._send(200, payload)
        if kind == OBJECT_DECEPTIVE:
            if actor == account["owner"]:
                return self._send(200, dict(account))
            return self._send(200, {"account_id": "account-2", "display_name": "foreign-like"})
        if kind == OBJECT_CONTRADICTORY and later:
            if actor != account["owner"]:
                return self._send(403, {"error": "forbidden"})
            return self._send(200, dict(account))
        if kind in {TRUE_BOLA, OBJECT_CONTRADICTORY}:
            return self._send(200, dict(account))
        if actor != account["owner"]:
            return self._send(403, {"error": "forbidden"})
        return self._send(200, dict(account))

    def _workflow(
        self,
        lab: ResearchSelectionLab,
        method: str,
        parts: list[str],
        actor: str | None,
        count: int,
    ) -> int:
        if len(parts) not in {3, 4} or parts[1] != "requests":
            return self._send(404, {"error": "not found"})
        area = parts[0]
        resource_id = parts[2]
        transition = parts[3] if len(parts) == 4 else None
        if not actor or actor not in ACTOR_ROLES:
            return self._send(401, {"error": "unauthenticated"})
        record = lab.records.get(resource_id)
        if record is None:
            return self._send(404, {"error": "unknown request"})
        if method == "GET":
            if transition is not None:
                return self._send(404, {"error": "not found"})
            return self._send(200, _observed(record, actor))
        if method != "POST" or transition not in {"submit", "review", "approve", "reject"}:
            return self._send(404, {"error": "unknown transition"})
        return self._transition(lab, area, record, actor, transition, count)

    def _transition(
        self,
        lab: ResearchSelectionLab,
        area: str,
        record: dict[str, Any],
        actor: str,
        transition: str,
        count: int,
    ) -> int:
        later = count > PROBE_REQUESTS_PER_CYCLE
        kind = lab.workflow_kind
        if kind == WORKFLOW_CONTRADICTORY and later:
            return self._send(403, {"error": "forbidden", "current_state": record["state"]})
        if kind == WORKFLOW_DECEPTIVE:
            return self._send(200, {"ok": True})
        enforce = area == "control" or kind == SECURE_ROLE_ENFORCEMENT
        if (
            kind in {TRUE_ROLE_BYPASS, WORKFLOW_CONTRADICTORY}
            and area == "workflow"
            and transition == "approve"
            and not enforce
        ):
            record["state"] = "APPROVED"
            record["approved_by"] = actor
            return self._send(200, _observed(record, actor))
        role = ACTOR_ROLES[actor]
        delegated = actor in record["delegated_reviewers"]
        state = record["state"]
        if transition != "approve":
            return self._send(403, {"error": "forbidden", "current_state": state})
        if state != "UNDER_REVIEW":
            return self._send(409, {"error": "invalid_sequence", "current_state": state})
        if role not in {"reviewer", "admin"} and not delegated:
            return self._send(403, {"error": "forbidden", "current_state": state})
        record["state"] = "APPROVED"
        record["approved_by"] = actor
        return self._send(200, _observed(record, actor))

    def _redirect(self) -> int:
        self.send_response(302)
        self.send_header("Location", EXTERNAL_REDIRECT)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return 302

    def _send(self, status: int, payload: dict[str, Any]) -> int:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return status
