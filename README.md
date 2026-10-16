# Grok Model Router

This repository is currently in the **transport qualification** stage for a future reversible Model Router. It is not an installer and does not patch a Grok Bot host.

The approved target is a Linux-local, version-gated transport adapter that can route a selected Bot UUID through xKiro or another configured OpenAI-compatible provider, with explicit native pause/resume. The project must prove the ordinary-turn inference boundary before implementing that adapter.

## Current commands

```bash
python -m pip install -e ".[test]"
python -m pytest tests/qualification -q
python -m grok_model_router.qualification.cli scan --help
```

For a user-run VM collection, see [docs/qualification/README.md](docs/qualification/README.md). It fingerprints a supplied host, performs bounded source analysis, and can optionally project the loopback `/api/listAgents` roster. It does not read `/proc` for secrets, call a model provider, send chat prompts, or modify the host.

An `inconclusive` or `blocked` report is not an installation authorization. A human must review a `qualified` report before a transport patch plan is written.
