import json
import threading
import urllib.error
import urllib.request

import pytest

from grok_model_router.routing.api import create_server
from grok_model_router.routing.store import RouteStore


@pytest.fixture
def api_server(tmp_path):
    server = create_server(RouteStore(tmp_path / "routes.db"), host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=2)


def request(base, method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_route_api_persists_route_and_pause_resume(api_server):
    agent_id = "11111111-1111-4111-8111-111111111111"
    status, body = request(api_server, "PUT", f"/v1/routes/{agent_id}", {
        "providerId": "xkiro",
        "modelId": "x-ai/grok-4.7",
    })
    assert status == 200
    assert body["route"]["epoch"] == 1
    status, body = request(api_server, "POST", f"/v1/routes/{agent_id}/pause", {"expectedEpoch": 1})
    assert status == 200
    assert body["route"]["paused"] is True
    status, body = request(api_server, "GET", f"/v1/routes/{agent_id}")
    assert status == 200
    assert body["route"]["paused"] is True


def test_route_api_returns_conflict_for_stale_epoch(api_server):
    agent_id = "11111111-1111-4111-8111-111111111111"
    request(api_server, "PUT", f"/v1/routes/{agent_id}", {
        "providerId": "xkiro",
        "modelId": "x-ai/grok-4.7",
    })
    status, body = request(api_server, "POST", f"/v1/routes/{agent_id}/pause", {"expectedEpoch": 0})
    assert status == 409
    assert "conflict" in body["error"]


def test_health_does_not_expose_routes_or_credentials(api_server):
    status, body = request(api_server, "GET", "/healthz")
    assert status == 200
    assert body == {"ok": True}


def test_chat_completion_endpoint_uses_active_route(tmp_path):
    class Provider:
        def __init__(self):
            self.payloads = []

        def chat_completion(self, payload):
            self.payloads.append(payload)
            return {"choices": [{"message": {"content": "routed"}}]}

    provider = Provider()
    store = RouteStore(tmp_path / "routes.db")
    agent_id = "11111111-1111-4111-8111-111111111111"
    store.set_route(agent_id, "xkiro", "x-ai/grok-4.7")
    server = create_server(store, providers={"xkiro": provider}, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = request(server_url := f"http://127.0.0.1:{server.server_port}", "POST", f"/v1/routes/{agent_id}/chat/completions", {"model": "wrong", "messages": []})
        assert status == 200
        assert body["choices"][0]["message"]["content"] == "routed"
        assert provider.payloads[0]["model"] == "x-ai/grok-4.7"
    finally:
        server.shutdown()
        thread.join(timeout=2)
