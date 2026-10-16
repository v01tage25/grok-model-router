import pytest

from grok_model_router.routing.store import RouteConflict, RouteStore


def test_route_store_creates_and_reads_route(tmp_path):
    store = RouteStore(tmp_path / "routes.db")

    route = store.set_route("11111111-1111-4111-8111-111111111111", "xkiro", "x-ai/grok-4.7")

    assert route.agent_id == "11111111-1111-4111-8111-111111111111"
    assert route.provider_id == "xkiro"
    assert route.model_id == "x-ai/grok-4.7"
    assert route.paused is False
    assert route.epoch == 1
    assert store.get_route(route.agent_id) == route


def test_route_changes_require_expected_epoch(tmp_path):
    store = RouteStore(tmp_path / "routes.db")
    route = store.set_route("11111111-1111-4111-8111-111111111111", "xkiro", "x-ai/grok-4.7")

    with pytest.raises(RouteConflict):
        store.set_route(route.agent_id, "xkiro", "x-ai/grok-4.6", expected_epoch=0)

    changed = store.set_route(route.agent_id, "xkiro", "x-ai/grok-4.6", expected_epoch=1)
    assert changed.epoch == 2


def test_pause_and_resume_increment_epoch(tmp_path):
    store = RouteStore(tmp_path / "routes.db")
    route = store.set_route("11111111-1111-4111-8111-111111111111", "xkiro", "x-ai/grok-4.7")

    paused = store.pause(route.agent_id, expected_epoch=route.epoch)
    resumed = store.resume(route.agent_id, expected_epoch=paused.epoch)

    assert paused.paused is True
    assert resumed.paused is False
    assert resumed.epoch == route.epoch + 2


def test_route_store_never_persists_credentials(tmp_path):
    store = RouteStore(tmp_path / "routes.db")
    store.set_route(
        "11111111-1111-4111-8111-111111111111",
        "xkiro",
        "x-ai/grok-4.7",
        parameters={"effort": "high"},
    )

    raw = (tmp_path / "routes.db").read_bytes()
    assert b"sk-" not in raw
    assert b"api_key" not in raw
