"""Localhost-only HTTP bridge for Cursor MCP <-> Unreal Editor."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from . import commands
from .game_thread import ensure_tick, mark_http_worker

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 27182

_server: ThreadingHTTPServer | None = None
_thread: threading.Thread | None = None
_started = False


class _BridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        mark_http_worker(True)
        try:
            path = urlparse(self.path).path
            if path == "/health":
                self._send(
                    200,
                    {
                        "ok": True,
                        "bridge": "CursorUnrealBridge",
                        "bridge_running": _started,
                        "url": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
                    },
                )
                return
            if path == "/status":
                try:
                    self._send(200, commands.get_status())
                except Exception as exc:
                    self._send(500, {"ok": False, "error": str(exc)})
                return
            if path == "/commands":
                self._send(200, {"commands": list(commands.COMMANDS.keys())})
                return
            self._send(404, {"error": "not found"})
        finally:
            mark_http_worker(False)

    def do_POST(self) -> None:
        mark_http_worker(True)
        try:
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send(400, {"success": False, "error": "invalid json"})
                return

            try:
                if path == "/execute_python":
                    result = commands.execute_python(data.get("code", ""))
                    self._send(200 if result.get("success") else 500, result)
                    return
                if path == "/command":
                    result = commands.dispatch(
                        data.get("command", ""), data.get("args") or {}
                    )
                    ok = result.get("success", result.get("ok", False))
                    self._send(200 if ok else 500, result)
                    return
                self._send(404, {"success": False, "error": f"unknown path {path}"})
            except Exception as exc:
                self._send(500, {"success": False, "error": str(exc)})
        finally:
            mark_http_worker(False)


def start_bridge(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> dict[str, Any]:
    global _server, _thread, _started
    if _started and _server is not None:
        return {"ok": True, "already_running": True, "url": f"http://{host}:{port}"}

    ensure_tick()
    _server = ThreadingHTTPServer((host, port), _BridgeHandler)
    _thread = threading.Thread(
        target=_server.serve_forever, name="CursorUnrealBridge", daemon=True
    )
    _thread.start()
    _started = True
    return {"ok": True, "url": f"http://{host}:{port}", "host": host, "port": port}


def stop_bridge() -> dict[str, Any]:
    global _server, _thread, _started
    if _server is not None:
        try:
            _server.shutdown()
            _server.server_close()
        except Exception:
            pass
    _server = None
    _thread = None
    _started = False
    return {"ok": True, "stopped": True}


def get_status() -> dict[str, Any]:
    return {
        "bridge_running": _started,
        "url": f"http://{DEFAULT_HOST}:{DEFAULT_PORT}" if _started else None,
    }
