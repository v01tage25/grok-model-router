import pytest

from grok_model_router.routing.engine import RouteEngine, RoutePaused, RouteUnavailable
from grok_model_router.routing.store import RouteStore


class FakeProvider:
    def __init__(self):
        self.payloads = []

    def chat_completion(self, payload):
        self.payloads.append(payload)
        return {"choices": [{"message": {"content": "ok"}}]}


def test_engine_overrides_model_for_active_route(tmp_path):
    store = RouteStore(tmp_path / "routes.db")
    store.set_route("11111111-1111-4111-8111-111111111111", "xkiro", "x-ai/grok-4.7", parameters={"effort": "high"})
    provider = FakeProvider()
    engine = RouteEngine(store, {"xkiro": provider})

    response = engine.chat_completion("11111111-1111-4111-8111-111111111111", {
        "model": "wrong-model",
        "messages": [{"role": "user", "content": "ping"}],
    })

    assert response["choices"][0]["message"]["content"] == "ok"
    assert provider.payloads[0]["model"] == "x-ai/grok-4.7"
    assert provider.payloads[0]["reasoning_effort"] == "high"


def test_engine_refuses_paused_route_without_provider_call(tmp_path):
    store = RouteStore(tmp_path / "routes.db")
    route = store.set_route("11111111-1111-4111-8111-111111111111", "xkiro", "x-ai/grok-4.7")
    store.pause(route.agent_id, expected_epoch=route.epoch)
    provider = FakeProvider()

    with pytest.raises(RoutePaused):
        RouteEngine(store, {"xkiro": provider}).chat_completion(route.agent_id, {"messages": []})
    assert provider.payloads == []


def test_engine_has_no_implicit_native_fallback(tmp_path):
    store = RouteStore(tmp_path / "routes.db")
    store.set_route("11111111-1111-4111-8111-111111111111", "missing", "model")

    with pytest.raises(RouteUnavailable):
        RouteEngine(store, {}).chat_completion("11111111-1111-4111-8111-111111111111", {"messages": []})
