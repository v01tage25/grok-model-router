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
