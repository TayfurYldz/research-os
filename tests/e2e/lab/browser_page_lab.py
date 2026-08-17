"""Loopback HTML/JS lab for GATE 21 browser.page tests. Not a product server."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

SESSION_COOKIE_NAME = "sid"
ALICE_COOKIE = "alice-session-material"
BOB_COOKIE = "bob-session-material"


class Gate21BrowserLab:
    def __init__(self) -> None:
        handler = _handler_for(self)
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self.hits: list[str] = []

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

    def __enter__(self) -> Gate21BrowserLab:
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        self.stop()


def _handler_for(lab: Gate21BrowserLab):
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            del format, args

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            lab.hits.append(parsed.path)
            pages = {
                "/": _page("home", "<p>home</p><button id='go'>go</button>"),
                "/app": _page(
                    "app",
                    "<input name='q' placeholder='search'>"
                    "<button type='submit' id='save'>save</button>"
                    "<input type='password' name='pw' value='hidden-password'>"
                    "<input type='hidden' name='csrf' value='hidden-token'>",
                ),
                "/assets/app.js": ("application/javascript", "window.__g21 = true;"),
                "/assets/app.css": ("text/css", "body{color:#111}"),
                "/assets/pixel.png": ("image/png", b"\x89PNG\r\n\x1a\n"),
                "/excluded/secret": _page("excluded", "<p>secret</p>"),
                "/redirect-same": None,
                "/redirect-cross": None,
                "/post-form": _page(
                    "form",
                    "<form method='POST' action='/submit'>"
                    "<button type='submit' id='send'>send</button></form>"
                    "<button id='xhr'>xhr</button>"
                    "<script>document.getElementById('xhr').onclick=function(){"
                    "fetch('/submit',{method:'POST',body:'x=1'});};</script>",
                ),
                "/spa": _page(
                    "spa",
                    "<button id='inside'>inside</button>"
                    "<button id='outside'>outside</button>"
                    "<script>"
                    "document.getElementById('inside').onclick=function(){"
                    "history.pushState({},'', '/spa/inside');};"
                    "document.getElementById('outside').onclick=function(){"
                    "history.pushState({},'', '/excluded/secret');};"
                    "</script>",
                ),
                "/spa/inside": _page("spa-inside", "<p>inside</p>"),
                "/popup": _page(
                    "popup",
                    "<button id='open'>open</button>"
                    "<script>document.getElementById('open').onclick=function(){"
                    "window.open('/excluded/secret');};</script>",
                ),
                "/iframe-excluded": _page(
                    "iframe-excluded",
                    "<iframe src='/excluded/secret'></iframe>",
                ),
                "/iframe-cross": _page(
                    "iframe-cross",
                    "<iframe src='http://example.com/'></iframe>",
                ),
                "/schemes": _page(
                    "schemes",
                    "<a href='javascript:alert(1)'>js</a>"
                    "<iframe src='data:text/html,hi'></iframe>"
                    "<a href='blob:http://127.0.0.1/x'>blob</a>"
                    "<a href='file:///etc/passwd'>file</a>",
                ),
                "/download": (
                    "application/octet-stream",
                    b"binary-bytes",
                    {"Content-Disposition": "attachment; filename=g21.bin"},
                ),
                "/me": None,
                "/ws": _page(
                    "ws",
                    "<script>try{new WebSocket('ws://127.0.0.1/socket')}catch(e){}</script>",
                ),
            }
            if parsed.path == "/redirect-same":
                self.send_response(302)
                self.send_header("Location", "/app")
                self.end_headers()
                return
            if parsed.path == "/redirect-cross":
                self.send_response(302)
                self.send_header("Location", "http://example.com/")
                self.end_headers()
                return
            if parsed.path == "/me":
                cookie = self.headers.get("Cookie") or ""
                user = "unknown"
                if ALICE_COOKIE in cookie:
                    user = "alice"
                elif BOB_COOKIE in cookie:
                    user = "bob"
                body = _page("me", f"<p id='who'>{user}</p>")
                self._send_page(body)
                return
            item = pages.get(parsed.path)
            if item is None:
                self.send_response(404)
                self.end_headers()
                return
            self._send_page(item)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            lab.hits.append("POST " + parsed.path)
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            self._send_page(_page("posted", "<p>posted</p>"))

        def _send_page(self, item: object) -> None:
            extra: dict[str, str] = {}
            if isinstance(item, tuple) and len(item) == 3:
                content_type, body, extra = item
            elif isinstance(item, tuple):
                content_type, body = item
            else:
                content_type, body = "text/html; charset=utf-8", str(item)
            payload = body if isinstance(body, bytes) else str(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", str(content_type))
            self.send_header("Content-Length", str(len(payload)))
            for name, value in extra.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(payload)

    return _Handler


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><title>"
        + title
        + "</title>"
        "<link rel='stylesheet' href='/assets/app.css'>"
        "<script src='/assets/app.js'></script>"
        "</head><body>"
        + body
        + "<img src='/assets/pixel.png' alt=''>"
        "</body></html>"
    )
