from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class ProviderRequestError(RuntimeError):
    """A provider request failed without retaining response secrets."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    base_url: str
    api_key_env: str
    user_agent: str = "grok-model-router/0.1"
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.provider_id.strip() or not self.api_key_env.strip():
            raise ValueError("provider_id and api_key_env are required")
        parsed = urllib.parse.urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("provider base URL must be HTTP(S)")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("provider base URL cannot contain credentials, query, or fragment")
        if parsed.path.rstrip("/") != "/v1":
            raise ValueError("provider base URL must end in /v1")
        if self.timeout_seconds <= 0:
            raise ValueError("provider timeout must be positive")

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")


class OpenAICompatibleProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    def _credential(self) -> str:
        value = os.environ.get(self.config.api_key_env, "").strip()
        if not value:
            raise ProviderRequestError("provider credential is not configured")
        return value

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        credential = self._credential()
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.config.normalized_base_url + path,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {credential}",
                "Accept": "application/json",
                "User-Agent": self.config.user_agent,
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            opener = urllib.request.build_opener(_NoRedirect())
            with opener.open(request, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise ProviderRequestError(
                f"provider {self.config.provider_id} returned HTTP {exc.code}"
            ) from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderRequestError(
                f"provider {self.config.provider_id} request failed: {type(exc).__name__}"
            ) from None
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ProviderRequestError(
                f"provider {self.config.provider_id} returned invalid JSON"
            ) from None

    def list_models(self) -> tuple[str, ...]:
        payload = self._request("GET", "/models")
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ProviderRequestError("provider returned an invalid models catalog")
        model_ids = tuple(
            item.get("id")
            for item in payload["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
        if len(model_ids) != len(payload["data"]):
            raise ProviderRequestError("provider returned a malformed models catalog")
        return model_ids

    def chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict) or not isinstance(payload.get("model"), str):
            raise ValueError("chat completion payload requires a model")
        response = self._request("POST", "/chat/completions", payload)
        if not isinstance(response, dict):
            raise ProviderRequestError("provider returned a malformed completion")
        return response
