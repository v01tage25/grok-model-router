# Local route API

The route API is a loopback-only control surface. It stores Bot UUID → provider/model rules and never stores provider credentials.

Start the local service from the project environment:

```bash
.venv/bin/grok-routerd --db /var/lib/grok-model-router/routes.db --port 8767
```

For first VM validation, keep it bound to `127.0.0.1`. Set `MODEL_ROUTER_AUTH_TOKEN` for an authenticated control API; otherwise do not bind outside loopback.

## Endpoints

```text
GET  /healthz
GET  /v1/routes/{agent_uuid}
PUT  /v1/routes/{agent_uuid}
POST /v1/routes/{agent_uuid}/pause
POST /v1/routes/{agent_uuid}/resume
```

Example route write:

```bash
curl -sS -X PUT http://127.0.0.1:8767/v1/routes/11111111-1111-4111-8111-111111111111 \
  -H 'Content-Type: application/json' \
  --data '{"providerId":"xkiro","modelId":"x-ai/grok-4.7","parameters":{"effort":"high"}}'
```

All writes return an `epoch`. Pause/resume/update calls must send that epoch as `expectedEpoch`; stale writes receive HTTP 409. Provider API keys are configured separately through provider adapter environment variables and never through this API.

This API does **not** yet change native Grok Bot inference. That remains gated on the transport qualification verdict.
