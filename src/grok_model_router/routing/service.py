from __future__ import annotations

import argparse
import os

from ..providers.openai_compatible import OpenAICompatibleProvider, ProviderConfig
from .api import create_server
from .store import RouteStore


def configured_providers() -> dict[str, OpenAICompatibleProvider]:
    providers: dict[str, OpenAICompatibleProvider] = {}
    if os.environ.get("XKIRO_API_KEY", "").strip():
        providers["xkiro"] = OpenAICompatibleProvider(
            ProviderConfig(
                provider_id="xkiro",
                base_url=os.environ.get("XKIRO_BASE_URL", "https://api.xkiro.com/v1"),
                api_key_env="XKIRO_API_KEY",
                user_agent=os.environ.get(
                    "XKIRO_USER_AGENT",
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                ),
            )
        )
    generic_key_env = os.environ.get("MODEL_ROUTER_PROVIDER_KEY_ENV", "").strip()
    generic_base_url = os.environ.get("MODEL_ROUTER_PROVIDER_BASE_URL", "").strip()
    generic_id = os.environ.get("MODEL_ROUTER_PROVIDER_ID", "openai-compatible").strip()
    if generic_key_env and generic_base_url and os.environ.get(generic_key_env, "").strip():
        providers[generic_id] = OpenAICompatibleProvider(
            ProviderConfig(
                provider_id=generic_id,
                base_url=generic_base_url,
                api_key_env=generic_key_env,
                user_agent=os.environ.get("MODEL_ROUTER_PROVIDER_USER_AGENT", "grok-model-router/0.1"),
            )
        )
    return providers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grok-routerd")
    parser.add_argument("--db", default=os.environ.get("MODEL_ROUTER_DB", "router.db"))
    parser.add_argument("--host", default=os.environ.get("MODEL_ROUTER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MODEL_ROUTER_PORT", "8767")))
    parser.add_argument("--auth-token-env", default="MODEL_ROUTER_AUTH_TOKEN")
    args = parser.parse_args(argv)
    token = os.environ.get(args.auth_token_env) or None
    server = create_server(
        RouteStore(args.db),
        providers=configured_providers(),
        host=args.host,
        port=args.port,
        auth_token=token,
    )
    print(f"grok-routerd listening on http://{args.host}:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
