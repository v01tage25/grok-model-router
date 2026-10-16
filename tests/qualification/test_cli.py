def test_cli_invalid_path_returns_code_three(tmp_path):
    from grok_model_router.qualification.cli import main

    assert main(["scan", "--host", str(tmp_path / "missing.cjs")]) == 3


def test_module_entrypoint_runs_scan(tmp_path):
    import subprocess
    import sys

    host = tmp_path / "host.cjs"
    host.write_text("class RequestedModel {}\nconst modelId = 'schema';\n", encoding="utf-8")
    output = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "grok_model_router.qualification.cli",
            "scan",
            "--host",
            str(host),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert output.is_file()


def test_doctor_rejects_external_gateway_without_network(monkeypatch):
    from grok_model_router.qualification.cli import main

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("external network must not be called")

    monkeypatch.setattr("urllib.request.urlopen", fail_if_called)
    assert main(["doctor", "--gateway", "https://example.com"]) == 3


def test_scan_missing_version_file_returns_code_three(tmp_path):
    from grok_model_router.qualification.cli import main

    host = tmp_path / "host.cjs"
    host.write_text("class RequestedModel {}\nconst modelId = 'schema';\n", encoding="utf-8")
    assert main(["scan", "--host", str(host), "--version-file", str(tmp_path / "missing")]) == 3


def test_report_rejects_forged_qualified_status(tmp_path):
    import json
    from grok_model_router.qualification.cli import main

    source = tmp_path / "report.json"
    source.write_text(
        json.dumps({
            "status": "qualified",
            "fingerprint": {"path": "x", "size_bytes": 1, "sha256": "a" * 64, "version": None},
            "evidence": [],
            "blockers": [],
            "observations": [],
        }),
        encoding="utf-8",
    )
    assert main(["report", "--input", str(source)]) == 3


def test_doctor_does_not_follow_loopback_redirect(monkeypatch):
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from grok_model_router.qualification.cli import main

    class Handler(BaseHTTPRequestHandler):
        target_hit = False

        def do_GET(self):
            if self.path == "/health":
                self.send_response(302)
                self.send_header("Location", "https://external.example/health")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            type(self).target_hit = True
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert main(["doctor", "--gateway", f"http://127.0.0.1:{server.server_port}"]) == 2
        assert Handler.target_hit is False
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_doctor_rejects_gateway_url_credentials(monkeypatch):
    from grok_model_router.qualification.cli import main

    assert main(["doctor", "--gateway", "http://user:secret@127.0.0.1:1340"]) == 3


def test_report_rejects_malformed_blockers(tmp_path):
    import json
    from grok_model_router.qualification.cli import main

    source = tmp_path / "report.json"
    source.write_text(json.dumps({
        "status": "inconclusive",
        "fingerprint": {"path": "x", "size_bytes": 1, "sha256": "a" * 64, "version": None},
        "evidence": [],
        "blockers": 42,
        "observations": [],
    }), encoding="utf-8")
    assert main(["report", "--input", str(source)]) == 3


def test_report_rejects_forged_qualified_with_confirmed_evidence(tmp_path):
    import json
    from grok_model_router.qualification.cli import main

    source = tmp_path / "report.json"
    source.write_text(json.dumps({
        "status": "qualified",
        "fingerprint": {"path": "x", "size_bytes": 1, "sha256": "a" * 64, "version": None},
        "evidence": [{"kind": "ordinary-turn", "confidence": "confirmed", "source": "input", "detail": "claimed"}],
        "blockers": [],
        "observations": [],
    }), encoding="utf-8")
    assert main(["report", "--input", str(source)]) == 3
