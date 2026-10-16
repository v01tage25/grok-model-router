# Transport qualification

This package is a **read-only qualification tool**, not an installer and not a supported transport patch.

It can fingerprint an explicitly supplied host bundle, classify source evidence, and optionally project the Bot roster from the loopback gateway's `POST /api/listAgents`. It does not execute the host bundle, call a model provider, send a chat prompt, modify `/opt/sand`, or create a compatibility entry.

## Local fixture tests

```bash
python -m pip install -e ".[test]"
python -m pytest tests/qualification -q
```

## VM collection

Run the operator script from a checked-out copy:

```bash
bash scripts/collect-qualification.sh
```

The script writes redacted reports under `/tmp/grok-router-qualification`. To enable the optional roster probe, set `GATEWAY_TOKEN` in the shell without printing it. The tool does not discover tokens from `/proc` and never writes the token to a report.

An `inconclusive` or `blocked` report is not an install authorization. A later patched transport plan may be written only after a human reviews a `qualified` report proving the ordinary-turn inference boundary, request/response/tool-stream contract, and quota independence.
