"""Loopback HTTP fixture for GATE 20 identity/session tests. Not a product server."""

from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

ALICE_USERNAME = "alice"
BOB_USERNAME = "bob"
ALICE_PASSWORD = "alice-pass-value"
BOB_PASSWORD = "bob-pass-value"
SESSION_COOKIE_NAME = "sid"


class Gate20AuthLab:
    def __init__(self) -> None:
        self.sessions: dict[str, str] = {}
        handler = _handler_for(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
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

    def __enter__(self) -> Gate20AuthLab:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.stop()


def _handler_for(lab: Gate20AuthLab):
    class _Gate20Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/login-redirect":
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return
            if parsed.path == "/me":
                user = self._user_from_cookie()
                if user is None:
                    self._send(401, {"error": "unauthenticated"})
                    return
                self._send(200, {"user": user, "ok": True})
                return
            self._send(404, {"error": "not found"})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/login-redirect":
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return
            if parsed.path != "/login":
                self._send(404, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            form = parse_qs(body.decode("utf-8"))
            username = (form.get("username") or [""])[0]
            password = (form.get("password") or [""])[0]
            expected = {ALICE_USERNAME: ALICE_PASSWORD, BOB_USERNAME: BOB_PASSWORD}.get(username)
            if expected is None or password != expected:
                self._send(401, {"error": "invalid"})
                return
            token = secrets.token_hex(16)
            lab.sessions[token] = username
            payload = json.dumps({"ok": True, "user": username}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Set-Cookie", f"{SESSION_COOKIE_NAME}={token}; Path=/")
            self.end_headers()
            self.wfile.write(payload)

        def _user_from_cookie(self) -> str | None:
            header = self.headers.get("Cookie") or ""
            prefix = f"{SESSION_COOKIE_NAME}="
            for part in header.split(";"):
                item = part.strip()
                if item.startswith(prefix):
                    return lab.sessions.get(item[len(prefix) :])
            return None

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return _Gate20Handler
