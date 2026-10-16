from __future__ import annotations

from typing import Any, Protocol

from .store import RouteStore


class Provider(Protocol):
    def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class RouteUnavailable(RuntimeError):
    """No active external provider route is available."""


class RoutePaused(RuntimeError):
    """The route is explicitly paused and native mode must be used."""


class RouteEngine:
    def __init__(self, store: RouteStore, providers: dict[str, Provider]):
        self.store = store
        self.providers = providers

    def chat_completion(self, agent_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        route = self.store.get_route(agent_id)
        if route is None:
            raise RouteUnavailable("route is not configured")
        if route.paused:
            raise RoutePaused("route is paused; native mode is required")
        provider = self.providers.get(route.provider_id)
        if provider is None:
            raise RouteUnavailable("configured provider is unavailable")
        body = dict(payload)
        body["model"] = route.model_id
        if "effort" in route.parameters and "reasoning_effort" not in body:
            body["reasoning_effort"] = route.parameters["effort"]
        return provider.chat_completion(body)
