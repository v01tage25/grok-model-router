def test_cli_invalid_path_returns_code_three(tmp_path):
    from grok_model_router.qualification.cli import main

    assert main(["scan", "--host", str(tmp_path / "missing.cjs")]) == 3
