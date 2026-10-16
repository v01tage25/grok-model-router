# Transport qualification verdict

**status:** `inconclusive`
**installable: false**
**collected_at:** `<UTC timestamp>`

## Host fingerprint

- Path: `<operator-supplied path>`
- Version: `<version or unknown>`
- Size bytes: `<integer>`
- SHA-256: `<64 hex characters>`
- Collection changed host files: `false`

## Static evidence

| kind | confidence | source | detail |
|---|---|---|---|
| `<kind>` | `confirmed` / `candidate` / `schema_only` / `missing` | `<bounded source label>` | `<redacted detail>` |

A `modelId` or `RequestedModel` declaration without a call in the ordinary-turn path is **schema_only** and cannot qualify a transport.

## Gateway roster

- ordinary-turn roster probe: `<not run / failed / passed>`
- rows projected: `<count>`
- prompt, description, last-message, and credential values stored: `false`

## ordinary-turn evidence

- entry point: `<exact source evidence or unknown>`
- Bot UUID propagation: `<confirmed / missing / unknown>`
- model selection injection point: `<confirmed / missing / unknown>`
- response text/reasoning stream: `<confirmed / missing / unknown>`
- tool calls/results and permissions: `<confirmed / missing / unknown>`
- cancellation/heartbeat/usage: `<confirmed / missing / unknown>`

## Execution boundary

- inference location: `<local / remote / unknown>`
- external endpoint control: `<confirmed / missing / unknown>`
- provider credentials boundary: `<confirmed / missing / unknown>`
- native maintenance/summary model path: `<confirmed / missing / unknown>`

## quota-independence

- active external route prevents native inference: `<confirmed / missing / unknown>`
- native Grok is used only when explicitly paused/restored: `<confirmed / missing / unknown>`
- verdict: `<not proven / proven by evidence>`

## Blockers

- `<exact blocker or none>`

## Next gate

A `qualified` verdict is required before writing a production transport adapter or installer. `blocked` and `inconclusive` reports authorize no host modification and require an owner decision or new evidence.
