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
