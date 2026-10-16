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
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from grok_model_router.qualification.gateway_probe import probe_list_agents

    class Handler(BaseHTTPRequestHandler):
        target_hit = False

        def do_POST(self):
            if self.path == "/api/listAgents":
                self.send_response(302)
                self.send_header("Location", "/target")
                self.end_headers()
                return
            if self.path == "/target":
                type(self).target_hit = True
                body = json.dumps([]).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import pytest

        with pytest.raises(ValueError, match="HTTP 302"):
            probe_list_agents(f"http://127.0.0.1:{server.server_port}", "secret")
        assert Handler.target_hit is False
    finally:
        server.shutdown()
        thread.join(timeout=2)
