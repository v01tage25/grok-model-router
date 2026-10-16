from __future__ import annotations

import json
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .store import RouteConflict, RouteState, RouteStore


def _route_payload(route: RouteState) -> dict[str, Any]:
    return {
        "agentId": route.agent_id,
        "providerId": route.provider_id,
        "modelId": route.model_id,
        "paused": route.paused,
        "epoch": route.epoch,
        "parameters": route.parameters,
    }


def create_server(store: RouteStore, *, host: str = "127.0.0.1", port: int = 8767, auth_token: str | None = None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            if auth_token is None:
                return True
            return self.headers.get("Authorization") == f"Bearer {auth_token}"

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_048_576:
                raise ValueError("request body too large")
            raw = self.rfile.read(length)
            value = json.loads(raw or b"{}")
            if not isinstance(value, dict):
                raise ValueError("request body must be an object")
            return value

        def _agent_id(self, parts: list[str]) -> str:
            if len(parts) < 3 or parts[0] != "v1" or parts[1] != "routes":
                raise ValueError("invalid route path")
            agent_id = urllib.parse.unquote(parts[2])
            uuid.UUID(agent_id)
            return agent_id

        def do_GET(self):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            path = urllib.parse.urlparse(self.path).path.strip("/")
            if path == "healthz":
                return self._send(200, {"ok": True})
            try:
                agent_id = self._agent_id(path.split("/"))
                route = store.get_route(agent_id)
            except (ValueError, RouteConflict):
                return self._send(400, {"error": "invalid route"})
            if route is None:
                return self._send(404, {"error": "route not found"})
            return self._send(200, {"route": _route_payload(route)})

        def do_PUT(self):
            self._mutate("set")

        def do_POST(self):
            self._mutate("action")

        def _mutate(self, kind: str):
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"})
            try:
                path = urllib.parse.urlparse(self.path).path.strip("/").split("/")
                agent_id = self._agent_id(path)
                body = self._body()
                expected = body.get("expectedEpoch")
                if expected is not None and (not isinstance(expected, int) or isinstance(expected, bool)):
                    raise ValueError("expectedEpoch must be an integer")
                if kind == "set":
                    route = store.set_route(
                        agent_id,
                        body["providerId"],
                        body["modelId"],
                        parameters=body.get("parameters") or {},
                        expected_epoch=expected,
                    )
                else:
                    if len(path) != 4 or path[3] not in {"pause", "resume"}:
                        raise ValueError("invalid route action")
                    route = (store.pause if path[3] == "pause" else store.resume)(
                        agent_id,
                        expected_epoch=expected,
                    )
            except RouteConflict:
                return self._send(409, {"error": "conflict"})
            except (KeyError, TypeError, ValueError):
                return self._send(400, {"error": "invalid request"})
            return self._send(200, {"route": _route_payload(route)})

    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    return server
