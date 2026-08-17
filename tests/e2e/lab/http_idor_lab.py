"""Intentionally vulnerable local HTTP lab. Bind 127.0.0.1 only. Synthetic data only."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

LAB_ACCOUNTS = {
    "alice": {"account_id": "alice", "owner": "alice", "marker": "lab-alice-marker"},
    "bob": {"account_id": "bob", "owner": "bob", "marker": "lab-bob-marker"},
}
ACTOR_HEADER = "X-Lab-Actor"
EXTERNAL_REDIRECT = "http://example.com/out-of-lab"


class Gate14Lab:
    """Loopback IDOR fixture. Not a product server and not an internet target."""

    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Gate14Handler)
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

    def __enter__(self) -> Gate14Lab:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.stop()


class _Gate14Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", EXTERNAL_REDIRECT)
            self.end_headers()
            return
        actor = self.headers.get(ACTOR_HEADER)
        parts = [item for item in parsed.path.split("/") if item]
        if len(parts) != 3 or parts[1] != "accounts" or parts[0] not in {"vulnerable", "secure"}:
            self._send(404, {"error": "not found"})
            return
        area, _, account_id = parts
        account = LAB_ACCOUNTS.get(account_id)
        if account is None:
            self._send(404, {"error": "unknown account"})
            return
        if not actor or actor not in LAB_ACCOUNTS:
            self._send(401, {"error": "unauthenticated"})
            return
        if area == "secure" and actor != account["owner"]:
            self._send(403, {"error": "forbidden"})
            return
        self._send(200, account)

    def do_POST(self) -> None:
        self._send(405, {"error": "GET only"})

    def do_PUT(self) -> None:
        self._send(405, {"error": "GET only"})

    def do_PATCH(self) -> None:
        self._send(405, {"error": "GET only"})

    def do_DELETE(self) -> None:
        self._send(405, {"error": "GET only"})

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
