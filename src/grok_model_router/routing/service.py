from __future__ import annotations

import argparse
import os

from .api import create_server
from .store import RouteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grok-routerd")
    parser.add_argument("--db", default=os.environ.get("MODEL_ROUTER_DB", "router.db"))
    parser.add_argument("--host", default=os.environ.get("MODEL_ROUTER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("MODEL_ROUTER_PORT", "8767")))
    parser.add_argument("--auth-token-env", default="MODEL_ROUTER_AUTH_TOKEN")
    args = parser.parse_args(argv)
    token = os.environ.get(args.auth_token_env) or None
    server = create_server(RouteStore(args.db), host=args.host, port=args.port, auth_token=token)
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
