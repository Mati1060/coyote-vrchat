"""Local HTTP API (127.0.0.1) for an AI to control frequency and intensity.

Safety — the device delivers shocks, so anything that can talk to this port has "hands on the
controls". Therefore:
  * it listens on 127.0.0.1 only;
  * it requires `Authorization: Bearer <token>` (the token lives in settings.json and is shown in the
    GUI). Web pages cannot learn the token, so a site open in the browser cannot send a shock;
  * it checks the Host header (DNS rebinding protection) and requires JSON bodies on POST;
  * control commands only work if the user enabled "Allow AI control" in the GUI, and they are
    limited by the AI ceiling and the rise ramp (see control.py);
  * there is no route to clear the emergency stop — that can only be done from the GUI.
"""
from __future__ import annotations

import hmac
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import patterns
from .control import ControlError, ControlForbidden

MAX_BODY = 8192
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


class _ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class ApiServer:
    def __init__(self, engine, host: str, port: int, token: str):
        self.engine, self.host, self.port, self.token = engine, host, port, token
        self.httpd: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    # ------------------------------------------------------------------ routes
    def status(self) -> dict:
        return {"ble": self.engine.link.status(), "control": self.engine.control.snapshot()}

    def dispatch(self, method: str, path: str, body: dict) -> dict:
        c = self.engine.control
        if method == "GET":
            if path == "/status":
                return self.status()
            if path == "/patterns":
                return {"patterns": [
                    {"name": p.key, "label": p.label, "description": p.description}
                    for p in patterns.PATTERNS.values()
                ]}
        elif method == "POST":
            if path == "/stop":
                self.engine.emergency_stop("ai")
                return {"ok": True, "estopped": True,
                        "note": "everything zeroed; only the user can re-enable, from the GUI"}
            if path == "/intensity":
                return c.set_intensity(body.get("channel", "AB"), body.get("value"), "ai")
            if path == "/frequency":
                return c.set_frequency(body.get("channel", "AB"), body.get("hz"), "ai")
            if path == "/width":
                return c.set_width(body.get("channel", "AB"), body.get("width"), "ai")
            if path == "/pattern":
                return c.set_pattern(body.get("name"), body.get("speed"), body.get("channels"),
                                     body.get("alternate"), "ai")
        raise _ApiError(404, "route not found")

    # ------------------------------------------------------------------ server
    def start(self) -> None:
        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "CoyoteVRC"

            def log_message(self, *_args):  # silent
                pass

            def _send(self, status: int, obj: dict) -> None:
                raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def _host_ok(self) -> bool:
                host = (self.headers.get("Host") or "").strip().lower()
                name = host.rsplit(":", 1)[0] if not host.startswith("[") else host.split("]")[0] + "]"
                return name in ALLOWED_HOSTS

            def _auth_ok(self) -> bool:
                got = (self.headers.get("Authorization") or "").encode("utf-8")
                want = f"Bearer {api.token}".encode("utf-8")
                return bool(api.token) and hmac.compare_digest(got, want)

            def _read_json(self) -> dict:
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    raise _ApiError(400, "invalid Content-Length") from None
                if length > MAX_BODY:
                    raise _ApiError(413, "body too large")
                if length == 0:
                    return {}
                if "application/json" not in (self.headers.get("Content-Type") or "").lower():
                    raise _ApiError(415, "use Content-Type: application/json")
                try:
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    raise _ApiError(400, "invalid JSON") from None
                if not isinstance(data, dict):
                    raise _ApiError(400, "the body must be a JSON object")
                return data

            def _route(self, method: str) -> None:
                try:
                    if not self._host_ok():
                        raise _ApiError(403, "Host not allowed")
                    if not self._auth_ok():
                        raise _ApiError(401, "missing or invalid token")
                    path = self.path.split("?", 1)[0]
                    body = self._read_json() if method == "POST" else {}
                    self._send(200, api.dispatch(method, path, body))
                except _ApiError as exc:
                    self._send(exc.status, {"error": str(exc)})
                except ControlForbidden as exc:
                    self._send(403, {"error": str(exc)})
                except ControlError as exc:
                    self._send(400, {"error": str(exc)})
                except Exception as exc:  # never takes the server down
                    self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

            def do_GET(self):
                self._route("GET")

            def do_POST(self):
                self._route("POST")

        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]  # allows port 0 in the tests
        self.thread = threading.Thread(
            target=self.httpd.serve_forever, kwargs={"poll_interval": 0.2}, name="api-http", daemon=True
        )
        self.thread.start()

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
