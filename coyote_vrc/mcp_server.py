"""Minimal MCP server (stdio): lets Claude Code / Claude Desktop control the Coyote.

It is just a "translator": each tool becomes an HTTP call to the app's local API (the app has to be
open). It implements the essentials of MCP (initialize, tools/list, tools/call, ping) with
line-delimited JSON-RPC 2.0, without depending on the `mcp` SDK.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Callable, Optional, Tuple

from . import __version__
from .settings import default_settings_path

SUPPORTED_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]
SERVER_INFO = {"name": "coyote-vrchat", "version": __version__}

_CHANNEL = {
    "type": "string", "enum": ["A", "B", "AB"],
    "description": "Channel: 'A', 'B' or 'AB' (both). Default: 'AB'.",
}

TOOLS = [
    {
        "name": "coyote_status",
        "description": "Current Coyote state: Bluetooth connection, intensities (requested and actual), frequency, width, "
                       "pattern, limits (including the AI ceiling) and whether AI control is enabled.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "coyote_set_intensity",
        "description": "Sets the intensity (0–200) of a channel. It is limited by the AI ceiling the user configured "
                       "(default 50) and rises at most ~100 units/s. Start low and increase gradually. If the app "
                       "refuses (403), do NOT try to work around it: tell the user.",
        "inputSchema": {
            "type": "object",
            "properties": {"channel": _CHANNEL, "value": {"type": "number", "minimum": 0, "maximum": 200}},
            "required": ["value"],
        },
    },
    {
        "name": "coyote_set_frequency",
        "description": "Sets the pulse frequency in Hz (1–100; the Coyote 3.0 cannot exceed 100 Hz).",
        "inputSchema": {
            "type": "object",
            "properties": {"channel": _CHANNEL, "hz": {"type": "number", "minimum": 1, "maximum": 100}},
            "required": ["hz"],
        },
    },
    {
        "name": "coyote_set_pulse_width",
        "description": "Sets the pulse width (0–100): the larger it is, the stronger the sensation at the same intensity.",
        "inputSchema": {
            "type": "object",
            "properties": {"channel": _CHANNEL, "width": {"type": "number", "minimum": 0, "maximum": 100}},
            "required": ["width"],
        },
    },
    {
        "name": "coyote_list_patterns",
        "description": "Lists the available patterns (waveforms that vary frequency/width over time).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "coyote_set_pattern",
        "description": "Chooses a pattern ('const' goes back to constant mode) and optionally speed (0.25–4), "
                       "channels and whether channel B runs out of phase with A.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Pattern name (see coyote_list_patterns)."},
                "speed": {"type": "number", "minimum": 0.25, "maximum": 4},
                "channels": _CHANNEL,
                "alternate": {"type": "boolean", "description": "Channel B half a cycle out of phase with A."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "coyote_stop",
        "description": "EMERGENCY STOP: zeroes both channels and blocks new commands until the user re-enables "
                       "them from the GUI. Use it whenever the user asks to stop or if anything looks wrong.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]

_ROUTES = {
    "coyote_status": ("GET", "/status"),
    "coyote_list_patterns": ("GET", "/patterns"),
    "coyote_set_intensity": ("POST", "/intensity"),
    "coyote_set_frequency": ("POST", "/frequency"),
    "coyote_set_pulse_width": ("POST", "/width"),
    "coyote_set_pattern": ("POST", "/pattern"),
    "coyote_stop": ("POST", "/stop"),
}

ApiCall = Callable[[str, str, Optional[dict]], Tuple[int, dict]]


class McpServer:
    def __init__(self, call_api: ApiCall):
        self.call_api = call_api

    def handle(self, msg: dict) -> Optional[dict]:
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}

        def result(value: dict) -> dict:
            return {"jsonrpc": "2.0", "id": mid, "result": value}

        def error(code: int, text: str) -> dict:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": text}}

        if mid is None:  # notification (e.g. notifications/initialized): no reply
            return None
        if method == "initialize":
            asked = params.get("protocolVersion")
            version = asked if asked in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
            return result({
                "protocolVersion": version,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            })
        if method == "ping":
            return result({})
        if method == "tools/list":
            return result({"tools": TOOLS})
        if method == "tools/call":
            name = params.get("name")
            if name not in _ROUTES:
                return error(-32602, f"unknown tool: {name}")
            http_method, path = _ROUTES[name]
            args = params.get("arguments") or {}
            status, data = self.call_api(http_method, path, args if http_method == "POST" else None)
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return result({"content": [{"type": "text", "text": text}], "isError": status >= 400})
        return error(-32601, f"unsupported method: {method}")


def load_connection() -> Tuple[str, str]:
    """(base_url, token): environment variables or the app's settings.json."""
    url = os.environ.get("COYOTE_API_URL", "")
    token = os.environ.get("COYOTE_API_TOKEN", "")
    if not (url and token):
        try:
            raw = json.loads(default_settings_path().read_text(encoding="utf-8"))
            url = url or f"http://127.0.0.1:{int(raw.get('api_port', 8765))}"
            token = token or str(raw.get("api_token", ""))
        except (OSError, ValueError):
            pass
    return url or "http://127.0.0.1:8765", token


def http_call_factory(base_url: str, token: str) -> ApiCall:
    def call(method: str, path: str, body: Optional[dict]) -> Tuple[int, dict]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(base_url + path, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except ValueError:
                return exc.code, {"error": f"HTTP {exc.code}"}
        except (urllib.error.URLError, OSError) as exc:
            return 503, {"error": "the Coyote app is not open (or the port/token changed): " + str(exc)}
    return call


def main() -> None:
    url, token = load_connection()
    server = McpServer(http_call_factory(url, token))
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        for item in (msg if isinstance(msg, list) else [msg]):
            if not isinstance(item, dict):
                continue
            try:
                reply = server.handle(item)
            except Exception as exc:
                reply = {"jsonrpc": "2.0", "id": item.get("id"),
                         "error": {"code": -32603, "message": f"{type(exc).__name__}: {exc}"}}
            if reply is not None:
                sys.stdout.write(json.dumps(reply) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
