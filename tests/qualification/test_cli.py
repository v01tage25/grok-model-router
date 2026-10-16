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
