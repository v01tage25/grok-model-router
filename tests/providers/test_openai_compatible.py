import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from grok_model_router.providers.openai_compatible import (
    OpenAICompatibleProvider,
    ProviderConfig,
    ProviderRequestError,
)


class FakeProviderHandler(BaseHTTPRequestHandler):
    requests = []
    response_status = 200
    response_body = {"data": [{"id": "x-ai/grok-4.7"}]}

    def do_GET(self):
        self.__class__.requests.append((self.command, self.path, dict(self.headers), b""))
        payload = json.dumps(self.response_body).encode()
        self.send_response(self.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self.__class__.requests.append((self.command, self.path, dict(self.headers), body))
        payload = json.dumps(self.response_body).encode()
        self.send_response(self.response_status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


@pytest.fixture
def fake_provider(monkeypatch):
    FakeProviderHandler.requests = []
    FakeProviderHandler.response_status = 200
    FakeProviderHandler.response_body = {"data": [{"id": "x-ai/grok-4.7"}]}
    server = HTTPServer(("127.0.0.1", 0), FakeProviderHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("TEST_PROVIDER_KEY", "test-secret")
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_list_models_sends_bearer_and_user_agent(fake_provider):
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            provider_id="xkiro",
            base_url=f"http://127.0.0.1:{fake_provider.server_port}/v1",
            api_key_env="TEST_PROVIDER_KEY",
            user_agent="Mozilla/5.0 qualification-test",
        )
    )

    models = provider.list_models()

    assert models == ("x-ai/grok-4.7",)
    method, path, headers, _ = FakeProviderHandler.requests[-1]
    assert method == "GET"
    assert path == "/v1/models"
    assert headers["Authorization"] == "Bearer test-secret"
    assert headers["User-Agent"] == "Mozilla/5.0 qualification-test"


def test_chat_completion_posts_json_without_logging_secret(fake_provider):
    FakeProviderHandler.response_body = {"choices": [{"message": {"content": "ok"}}]}
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            provider_id="xkiro",
            base_url=f"http://127.0.0.1:{fake_provider.server_port}/v1",
            api_key_env="TEST_PROVIDER_KEY",
        )
    )

    response = provider.chat_completion(
        {"model": "x-ai/grok-4.7", "messages": [{"role": "user", "content": "ping"}]}
    )

    assert response["choices"][0]["message"]["content"] == "ok"
    body = FakeProviderHandler.requests[-1][3]
    assert json.loads(body)["model"] == "x-ai/grok-4.7"


def test_provider_rejects_url_with_credentials_or_query():
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(
            ProviderConfig("x", "https://user:secret@example.com/v1", "KEY")
        )
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(
            ProviderConfig("x", "https://example.com/v1?key=secret", "KEY")
        )


def test_missing_key_is_a_safe_error(fake_provider, monkeypatch):
    monkeypatch.delenv("MISSING_PROVIDER_KEY", raising=False)
    provider = OpenAICompatibleProvider(
        ProviderConfig(
            provider_id="x",
            base_url=f"http://127.0.0.1:{fake_provider.server_port}/v1",
            api_key_env="MISSING_PROVIDER_KEY",
        )
    )

    with pytest.raises(ProviderRequestError, match="credential is not configured"):
        provider.list_models()
