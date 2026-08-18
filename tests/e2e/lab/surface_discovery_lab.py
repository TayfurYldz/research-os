"""Loopback hidden-ground-truth lab for GATE 22. Not imported by production code."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

SESSION_COOKIE_NAME = "sid"
ALICE_COOKIE = "alice-session-material"
BOB_COOKIE = "bob-session-material"

HIDDEN_TRUTH = {
    "hidden_page": "/hidden",
    "spa_page": "/spa/inside",
    "form_post": "/submit",
    "get_api": "/api/orders/101",
    "post_api": "/api/notes",
    "browser_only": "/api/browser-only",
    "dead_path": "/dead",
    "oos_origin": "http://example.com",
    "order_paths": ("/api/orders/101", "/api/orders/202", "/api/orders/303"),
    "workflow_path": "/ticket",
    "leakage_canary": "G22_HIDDEN_ROUTE_MAP_CANARY",
}


class Gate22SurfaceLab:
    def __init__(self) -> None:
        handler = _handler_for(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self.hits: list[str] = []
        self.ticket_state = "open"
        self.worker_origins: list[str] = []

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

    def __enter__(self) -> Gate22SurfaceLab:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.stop()


def _handler_for(lab: Gate22SurfaceLab):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            lab.hits.append("GET " + parsed.path)
            if parsed.path == "/redirect-cross":
                self.send_response(302)
                self.send_header("Location", "http://example.com/")
                self.end_headers()
                return
            if parsed.path == "/me":
                cookie = self.headers.get("Cookie") or ""
                user = "anonymous"
                if ALICE_COOKIE in cookie:
                    user = "alice"
                elif BOB_COOKIE in cookie:
                    user = "bob"
                self._html("me", f"<p id='who' name='who'>{user}</p>")
                return
            if parsed.path == "/ticket":
                self._html(
                    "ticket",
                    f"<p id='state' name='state'>{lab.ticket_state}</p>"
                    "<button name='advance' id='advance'>advance</button>"
                    "<script>document.getElementById('advance').onclick=function(){"
                    "fetch('/ticket/advance',{method:'POST'});};</script>",
                )
                return
            if parsed.path in {"/api/orders/101", "/api/orders/202", "/api/orders/303"}:
                self._json({"order_id": parsed.path.rsplit("/", 1)[-1], "status": "open"})
                return
            if parsed.path == "/api/browser-only":
                self._json({"source": "browser-fetch"})
                return
            if parsed.path == "/dead":
                self.send_response(404)
                self.end_headers()
                return
            pages = {
                "/": _home(),
                "/hidden": _page("hidden", "<p name='secret-page'>hidden-in-scope</p>"),
                "/spa": _spa(),
                "/spa/inside": _page("spa-inside", "<p name='spa-inside'>inside</p>"),
                "/form": _form(),
            }
            item = pages.get(parsed.path)
            if item is None:
                self.send_response(404)
                self.end_headers()
                return
            self._send(item)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            lab.hits.append("POST " + parsed.path)
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            if parsed.path == "/ticket/advance":
                lab.ticket_state = "closed"
                self._json({"state": lab.ticket_state})
                return
            if parsed.path == "/api/notes":
                self._json({"accepted": True})
                return
            if parsed.path == "/submit":
                self._html("posted", "<p name='posted'>posted</p>")
                return
            self.send_response(404)
            self.end_headers()

        def _html(self, title: str, body: str) -> None:
            self._send(_page(title, body))

        def _json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send(self, html: str) -> None:
            payload = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return _Handler


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><title>"
        + title
        + "</title></head><body>"
        + body
        + "</body></html>"
    )


def _home() -> str:
    return _page(
        "home",
        "<a href='/hidden' name='hidden'>hidden</a>"
        "<a href='/spa' name='spa'>spa</a>"
        "<a href='/form' name='form'>form</a>"
        "<a href='/ticket' name='ticket'>ticket</a>"
        "<a href='/me' name='me'>me</a>"
        "<a href='/dead' name='dead'>dead</a>"
        "<a href='http://example.com/' name='oos'>out</a>"
        "<a href='/redirect-cross' name='redirect'>redirect</a>"
        "<button name='fetch-hidden' id='fetch-hidden'>fetch</button>"
        "<script>"
        "fetch('/api/browser-only');"
        "fetch('/api/orders/101');"
        "fetch('/api/orders/202');"
        "fetch('/api/orders/303');"
        "document.getElementById('fetch-hidden').onclick=function(){"
        "fetch('/api/notes',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});"
        "};"
        "</script>",
    )


def _spa() -> str:
    return _page(
        "spa",
        "<button name='inside' id='inside'>inside</button>"
        "<script>document.getElementById('inside').onclick=function(){"
        "history.pushState({},'', '/spa/inside');};</script>",
    )


def _form() -> str:
    return _page(
        "form",
        "<form method='POST' action='/submit'>"
        "<button type='submit' name='send' id='send'>send</button></form>",
    )
