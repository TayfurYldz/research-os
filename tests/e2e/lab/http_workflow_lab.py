"""Local synthetic workflow fixtures for GATE 16. Bind 127.0.0.1 only.

Fixture kind is harness-internal. HTTP responses never include expected
security classification, scenario ids, or ground-truth labels.
"""

from __future__ import annotations

import copy
import json
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

ACTOR_HEADER = "X-Lab-Actor"
EXTERNAL_REDIRECT = "http://example.com/out-of-lab"
TIMEOUT_SLEEP_SECONDS = 6.0
PROBE_REQUESTS_PER_CYCLE = 4
MAX_POST_BYTES = 512

TRUE_ROLE_BYPASS = "TRUE_ROLE_BYPASS"
TRUE_SEQUENCE_SKIP = "TRUE_SEQUENCE_SKIP"
SECURE_ROLE_ENFORCEMENT = "SECURE_ROLE_ENFORCEMENT"
SECURE_SEQUENCE_ENFORCEMENT = "SECURE_SEQUENCE_ENFORCEMENT"
DECEPTIVE_200 = "DECEPTIVE_200_NO_STATE_CHANGE"
IDEMPOTENT_REPEAT = "IDEMPOTENT_REPEAT"
LEGITIMATE_DELEGATED = "LEGITIMATE_DELEGATED_REVIEWER"
STALE_CLIENT_STATE = "STALE_CLIENT_STATE"
CONTRADICTORY = "CONTRADICTORY_VERIFICATION"
OPERATIONAL_TIMEOUT = "OPERATIONAL_TIMEOUT"
REDIRECT_BOUNDARY = "REDIRECT_BOUNDARY"

APPROVE_REQUIRES_ROLE = "reviewer"
APPROVE_FROM_STATES = ("UNDER_REVIEW",)
ACTOR_ROLES = {
    "alice": "requester",
    "bob": "requester",
    "reviewer": "reviewer",
    "admin": "admin",
}


@dataclass(frozen=True)
class LabRequestRecord:
    method: str
    path: str
    actor: str | None
    client_host: str
    status: int


def _seed(kind: str) -> dict[str, dict[str, Any]]:
    if kind == TRUE_SEQUENCE_SKIP or kind == SECURE_SEQUENCE_ENFORCEMENT:
        state = "DRAFT"
        approved_by = None
    elif kind == IDEMPOTENT_REPEAT:
        state = "APPROVED"
        approved_by = "reviewer"
    else:
        state = "UNDER_REVIEW"
        approved_by = None
    delegated_alice: list[str] = ["alice"] if kind == LEGITIMATE_DELEGATED else []
    delegated_bob: list[str] = ["bob"] if kind == LEGITIMATE_DELEGATED else []
    return {
        "R1": {
            "request_id": "R1",
            "owner": "alice",
            "state": state,
            "approved_by": approved_by,
            "delegated_reviewers": list(delegated_alice),
        },
        "R2": {
            "request_id": "R2",
            "owner": "bob",
            "state": state,
            "approved_by": approved_by,
            "delegated_reviewers": list(delegated_bob),
        },
    }


class WorkflowLab:
    """Loopback change-request workflow fixture with a request ledger."""

    def __init__(self, fixture_kind: str) -> None:
        self.fixture_kind = fixture_kind
        self.ledger: list[LabRequestRecord] = []
        self.request_count = 0
        self.records = _seed(fixture_kind)
        self._lock = threading.Lock()
        self._server = _LabServer(("127.0.0.1", 0), _WorkflowHandler, lab=self)
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

    def __enter__(self) -> WorkflowLab:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.stop()

    def http_request_count(self) -> int:
        return len(self.ledger)

    def followed_external(self) -> bool:
        return any("example.com" in item.path for item in self.ledger)

    def record(self, record: LabRequestRecord) -> None:
        self.ledger.append(record)


class _LabServer(ThreadingHTTPServer):
    def __init__(self, address, handler, *, lab: WorkflowLab) -> None:
        self.lab = lab
        super().__init__(address, handler)


class _WorkflowHandler(BaseHTTPRequestHandler):
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
        lab: WorkflowLab = self.server.lab  # type: ignore[attr-defined]
        parsed = urlparse(self.path)
        actor = self.headers.get(ACTOR_HEADER)
        client_host = self.client_address[0]
        with lab._lock:
            lab.request_count += 1
            count = lab.request_count
        try:
            status = self._respond(lab, method, parsed.path, actor, count)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError):
            status = 0
        lab.record(
            LabRequestRecord(
                method=method,
                path=parsed.path,
                actor=actor,
                client_host=client_host,
                status=status,
            )
        )

    def _respond(
        self,
        lab: WorkflowLab,
        method: str,
        path: str,
        actor: str | None,
        count: int,
    ) -> int:
        if lab.fixture_kind == REDIRECT_BOUNDARY or path == "/redirect":
            return self._redirect()
        if lab.fixture_kind == OPERATIONAL_TIMEOUT and count > PROBE_REQUESTS_PER_CYCLE:
            time.sleep(TIMEOUT_SLEEP_SECONDS)
        if method == "POST":
            length = int(self.headers.get("Content-Length") or "0")
            if length > MAX_POST_BYTES:
                return self._send(413, {"error": "payload too large"})
            if length:
                self.rfile.read(length)
        parts = [item for item in path.split("/") if item]
        if len(parts) not in {3, 4} or parts[1] != "requests" or parts[0] not in {
            "workflow",
            "control",
        }:
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
        if transition not in {"submit", "review", "approve", "reject"}:
            return self._send(404, {"error": "unknown transition"})
        return self._transition(lab, area, record, actor, transition, count)

    def _transition(
        self,
        lab: WorkflowLab,
        area: str,
        record: dict[str, Any],
        actor: str,
        transition: str,
        count: int,
    ) -> int:
        later_cycle = count > PROBE_REQUESTS_PER_CYCLE
        if lab.fixture_kind == CONTRADICTORY and later_cycle:
            return self._send(403, {"error": "forbidden", "current_state": record["state"]})
        if lab.fixture_kind == DECEPTIVE_200:
            return self._send(200, {"ok": True})
        if lab.fixture_kind == STALE_CLIENT_STATE:
            return self._send(
                409,
                {"error": "stale_or_conflict", "current_state": record["state"]},
            )
        if lab.fixture_kind == IDEMPOTENT_REPEAT:
            return self._send(200, _observed(record, actor))
        enforce = area == "control" or lab.fixture_kind in {
            SECURE_ROLE_ENFORCEMENT,
            SECURE_SEQUENCE_ENFORCEMENT,
        }
        if lab.fixture_kind == TRUE_SEQUENCE_SKIP and area == "workflow" and transition == "approve":
            record["state"] = "APPROVED"
            record["approved_by"] = actor
            return self._send(200, _observed(record, actor))
        if lab.fixture_kind == TRUE_ROLE_BYPASS and area == "workflow" and transition == "approve":
            record["state"] = "APPROVED"
            record["approved_by"] = actor
            return self._send(200, _observed(record, actor))
        if lab.fixture_kind == LEGITIMATE_DELEGATED:
            return self._apply_policy(record, actor, transition)
        if lab.fixture_kind == CONTRADICTORY and not later_cycle and area == "workflow":
            record["state"] = "APPROVED"
            record["approved_by"] = actor
            return self._send(200, _observed(record, actor))
        if lab.fixture_kind == OPERATIONAL_TIMEOUT and not later_cycle and area == "workflow":
            record["state"] = "APPROVED"
            record["approved_by"] = actor
            return self._send(200, _observed(record, actor))
        return self._apply_policy(record, actor, transition)

    def _apply_policy(
        self,
        record: dict[str, Any],
        actor: str,
        transition: str,
    ) -> int:
        role = ACTOR_ROLES[actor]
        delegated = actor in record["delegated_reviewers"]
        state = record["state"]
        if transition == "submit":
            if actor != record["owner"] or state != "DRAFT":
                return self._send(403, {"error": "forbidden", "current_state": state})
            record["state"] = "SUBMITTED"
            return self._send(200, _observed(record, actor))
        if transition == "review":
            if role not in {"reviewer", "admin"} or state != "SUBMITTED":
                code = 409 if state != "SUBMITTED" else 403
                return self._send(code, {"error": "forbidden", "current_state": state})
            record["state"] = "UNDER_REVIEW"
            return self._send(200, _observed(record, actor))
        if transition == "approve":
            if state != "UNDER_REVIEW":
                return self._send(409, {"error": "invalid_sequence", "current_state": state})
            if role not in {"reviewer", "admin"} and not delegated:
                return self._send(403, {"error": "forbidden", "current_state": state})
            record["state"] = "APPROVED"
            record["approved_by"] = actor
            return self._send(200, _observed(record, actor))
        if transition == "reject":
            if role not in {"reviewer", "admin"}:
                return self._send(403, {"error": "forbidden", "current_state": state})
            record["state"] = "REJECTED"
            return self._send(200, _observed(record, actor))
        return self._send(404, {"error": "unknown transition"})

    def _redirect(self) -> int:
        self.send_response(302)
        self.send_header("Location", EXTERNAL_REDIRECT)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return 302

    def _send(self, status: int, payload: dict[str, Any]) -> int:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return status


def _observed(record: dict[str, Any], actor: str) -> dict[str, Any]:
    snapshot = copy.deepcopy(record)
    snapshot["actor_role"] = ACTOR_ROLES[actor]
    snapshot["approve_requires_role"] = APPROVE_REQUIRES_ROLE
    snapshot["approve_from_states"] = list(APPROVE_FROM_STATES)
    return snapshot
