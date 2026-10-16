
def test_configured_providers_registers_xkiro_from_environment(monkeypatch):
    from grok_model_router.routing.service import configured_providers

    monkeypatch.setenv("XKIRO_API_KEY", "test-secret")
    monkeypatch.delenv("XKIRO_BASE_URL", raising=False)

    providers = configured_providers()

    assert set(providers) == {"xkiro"}
    assert providers["xkiro"].config.base_url == "https://api.xkiro.com/v1"
    assert providers["xkiro"].config.api_key_env == "XKIRO_API_KEY"


def test_configured_providers_does_not_register_missing_credentials(monkeypatch):
    from grok_model_router.routing.service import configured_providers

    monkeypatch.delenv("XKIRO_API_KEY", raising=False)

    assert configured_providers() == {}
