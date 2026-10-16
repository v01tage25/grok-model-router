import json
from pathlib import Path

from grok_model_router.qualification.gateway_probe import project_agent_rows


def test_projection_discards_last_message_and_description():
    payload = json.loads(
        Path("tests/qualification/fixtures/list-agents-response.json").read_text()
    )

    rows = project_agent_rows(payload)

    assert rows[0].agent_id == "agent-a"
    assert rows[0].name == "Sunny"
    assert rows[0].harness == "temporal"
    assert not hasattr(rows[0], "last_message_preview")
    assert not hasattr(rows[0], "description")


def test_invalid_payload_is_rejected_without_echoing_input():
    try:
        project_agent_rows({"token": "do-not-echo"})
    except ValueError as exc:
        assert "do-not-echo" not in str(exc)
    else:
        raise AssertionError("invalid payload must fail")


def test_probe_does_not_follow_authenticated_redirect(monkeypatch):
    import urllib.error
    import urllib.request

    from grok_model_router.qualification.gateway_probe import probe_list_agents

    captured = {}

    class FakeOpener:
        def open(self, request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            raise urllib.error.HTTPError(request.full_url, 302, "redirect", {}, None)

    def build_opener(*handlers):
        captured["handlers"] = handlers
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", build_opener)

    import pytest

    with pytest.raises(ValueError, match="HTTP 302"):
        probe_list_agents("http://127.0.0.1:1340", "secret")
    assert any(type(handler).__name__ == "_NoRedirect" for handler in captured["handlers"])
    assert captured["request"].headers["Authorization"] == "Bearer secret"
