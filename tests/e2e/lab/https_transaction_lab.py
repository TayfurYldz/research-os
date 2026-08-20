"""Loopback HTTPS transaction lab for executor-fabric tests."""

from __future__ import annotations

import json
import ssl
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class _HttpsHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        del format, args

    def do_GET(self) -> None:
        if self.path != "/ok":
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = json.dumps({"ok": True, "transport": "https"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class HttpsTransactionLab:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        cert = root / "cert.pem"
        key = root / "key.pem"
        subprocess.run(
            (
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=127.0.0.1",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ),
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _HttpsHandler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=str(cert), keyfile=str(key))
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def origin(self) -> str:
        host, port = self._server.server_address[:2]
        return f"https://{host}:{port}"

    def start(self) -> str:
        self._thread.start()
        return self.origin

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
        self._tmp.cleanup()
