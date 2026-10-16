# Model Router — patched transport design

**Date:** 2026-10-16  
**Status:** Approved by user on 2026-10-16; production transport compatibility remains unverified
**Reference:** `promptadvisers/grokrouter` reviewed as an architectural reference; no code copied.

## 1. Goal

Build a Linux-first Model Router for the current Grok Bot VM that lets a user choose a Bot by its real UUID, choose an external provider and model, and route that Bot's model requests through the selected provider while preserving the native Grok Bot surface (conversation, transcript, tools, permissions, and computer access).

When a route is active, inference must use the configured external provider **100%**. Native Grok inference is used only while the route is explicitly paused or restored. A provider failure is not silently converted into native Grok fallback.

The first provider set is:

- xKiro;
- any configured OpenAI-compatible endpoint.

The implementation must not put provider keys in Git, route state, host bundles, logs, diagnostic output, or chat transcripts.

## 2. Confirmed environment constraints

The current VM runs a packaged host and exposes a loopback gateway that was probed during discovery. Live paths, versions, hashes, and Bot identifiers are kept in local qualification evidence and are not part of this public repository.

The gateway's `sendPrompt` contract does not accept `modelId`, `modelParams`, provider, or endpoint fields. Therefore the router cannot achieve transparent model switching by calling `/api/sendPrompt` or by editing `model-bindings.json`.

The host bundle contains a separate cloud-agent `RequestedModel` path, but its direct accessibility for ordinary native Bot turns is not established. The patched-transport implementation must locate and patch the actual model transport in a supported, version-gated host fixture rather than assume that the cloud-agent path controls native turns.

The previous `OnlyTerp/opengrok` project was removed from the VM and is not a dependency of this design.

## 3. Architecture

```text
                 loopback only
  skill ───────┐
               ├── routerd ─── provider adapter ─── xKiro/OpenAI-compatible API
  web wizard ──┘       │
                       ├── agent catalog: /api/listAgents
                       ├── route store: UUID → provider/model/state
                       ├── patch manager: host fingerprint + anchors + backup
                       └── repair/restore/doctor

  Grok host model transport ── patched route decision ── routerd
                                      │
                           paused ───┴── native Grok transport
```

### 3.1 `routerd`

A small local service, bound to `127.0.0.1` by default. It owns:

- provider registry and model catalog;
- per-Bot route state;
- credential lookup by environment variable or an explicitly configured local secret mechanism;
- OpenAI-compatible request/stream translation;
- pause/resume state;
- request and route diagnostics without prompt or credential logging;
- a versioned local API consumed by the skill, web wizard, and patched transport.

The service must expose a health endpoint and a readiness signal. It must reject non-loopback binds unless an explicit authenticated HTTPS mode is configured later.

### 3.2 Agent catalog

The router must call the native loopback gateway's `POST /api/listAgents` to discover the current roster. It must use the returned UUID as the stable key and treat the display name as mutable UI data. A cached catalog may be used only when the gateway is temporarily unavailable, and stale entries must be marked as stale.

### 3.3 Route store

Use an atomic, versioned local store (SQLite is preferred for concurrent UI/skill/transport access). Each route record contains:

- `agent_id`;
- provider ID;
- exact model ID;
- active/paused state;
- `thread_epoch` or equivalent generation counter;
- created/updated timestamps;
- last known provider health status;
- optional provider parameters, validated against provider capabilities.

Changing provider, model, or pause state increments the epoch. Late responses from an older epoch must be rejected or ignored so an old request cannot overwrite a newer route.

Route state contains no credentials and no prompt/transcript content.

### 3.4 Provider adapters

Define a narrow adapter interface:

- list models;
- validate model ID;
- send non-streaming completion;
- send streaming completion;
- normalize provider errors;
- report capabilities;
- provide safe health metadata.

The xKiro adapter uses an environment-provided key and a browser-compatible User-Agent where required. The generic OpenAI-compatible adapter requires an explicit base URL ending in `/v1`, a key environment-variable name, and a model ID. The adapter must never guess a provider URL or credential.

### 3.5 Patched transport

The patch manager will modify only the smallest verified transport boundary in the current host. It must:

1. identify the exact stock host using version, byte count, and SHA-256;
2. verify all source anchors and expected surrounding structure;
3. create an immutable, timestamped stock backup before replacement;
4. add a narrow route decision that carries the current Bot UUID and request context to `routerd`;
5. preserve native behavior when the route is paused;
6. return real external-provider errors when the route is active;
7. run syntax checks and a fixture-level smoke test before activation;
8. atomically replace the live host only after all checks pass.

The patch must not use broad regex replacement, blind `sed`, unknown-host overrides, or heuristic matching. It must not alter agent profiles, stores, permissions, tool definitions, or transcript files.

The exact patch anchors are intentionally **not** specified until a fixture of the current host transport is isolated. An unknown host must be rejected, not patched.

## 4. Update and recovery behavior

The installed project must provide:

- `router status` — host hash, patch state, router health, backup health, current routes;
- `router check` — read-only compatibility and dry-run checks;
- `router install` — install runtime and a supported patch;
- `router repair` — reapply only to a known supported updated host;
- `router restore-stock` — restore the verified stock host and disable the patch watchdog;
- `router uninstall` — restore stock, stop routerd, remove only Model Router-owned files;
- `router pause <agent-id>` / `router resume <agent-id>`;
- `router doctor` — redacted diagnostics.

On host update:

1. detect hash drift;
2. stop routing changes;
3. preserve the new stock host as an unmodified candidate;
4. run compatibility and anchor checks;
5. require a reviewed compatibility entry before repair;
6. apply atomically only after tests pass;
7. otherwise leave the host untouched and report the blocker.

A watchdog may notify or repair only when the compatibility entry is exact. It must never substitute an old backup for an unknown live host.

## 5. User interfaces

### Web wizard

Loopback web UI flow:

1. refresh Bot catalog;
2. choose Bot by name, showing UUID and stale status;
3. choose provider;
4. fetch provider models;
5. choose exact model and optional validated parameters;
6. show the effective route and credential status without revealing the key;
7. confirm and save;
8. show active/paused state and last health result.

The UI must make the distinction between `active external route` and `paused/native Grok` explicit.

### Grok Bot skill

Provide a skill that calls the same router API. Initial commands:

- `/provider`;
- `/provider <provider>`;
- `/models`;
- `/model <provider>/<model>`;
- `/router status`;
- `/router pause`;
- `/router resume`;
- `/router doctor`;
- `/router reset`.

In group contexts, the skill must resolve the mentioned Bot UUID and refuse ambiguous or unscoped changes. The skill must never ask the Bot to print or paste credentials.

## 6. Security requirements

- loopback-only by default;
- no secrets in Git, JSON route state, host bundle, logs, screenshots, or diagnostics;
- redact Authorization headers, keys, cookies, prompt bodies, tool inputs/outputs, and provider responses from logs;
- atomic permissions for state and backup files;
- exact host hash and anchor gates;
- signed or hash-pinned compatibility registry for releases;
- explicit stock restore;
- no `--allow-unknown-host` in user-facing installers;
- display a disclosure warning that routed prompts, attachments, tool results, and model outputs may leave the VM;
- never silently fall back from an active external route to native Grok.

## 7. Testing strategy

### Unit tests

- route selection by UUID;
- pause/resume and epoch increments;
- ambiguous/missing agent handling;
- provider/model validation;
- secret redaction;
- atomic store recovery;
- stale response rejection;
- normalized provider errors.

### Provider contract tests

- models catalog;
- authenticated request;
- streaming `[DONE]` handling;
- xKiro browser-compatible request headers;
- invalid key, 401/403, 429, 5xx, timeout, and malformed stream behavior;
- no key or prompt leakage in diagnostics.

### Patch fixture tests

- known current host fixture: exact hash and anchors pass;
- wrong hash refuses;
- changed anchor refuses;
- generated code passes Node syntax check;
- patch is idempotent;
- restore returns byte-identical stock fixture;
- route active, route paused, and router unavailable behavior;
- upgrade from a reviewed host version requires the new compatibility entry.

### VM acceptance tests

Only after fixture tests pass:

1. install on a disposable/current VM backup;
2. list agents through `/api/listAgents`;
3. route one test Bot to a low-cost model;
4. verify a normal message reaches the provider;
5. verify tools and transcript still work;
6. pause and verify native Grok path;
7. resume and verify external path;
8. run doctor and capture only redacted diagnostics;
9. test restore-stock.

## 8. Scope boundaries for v1

Included:

- Linux VM installer;
- xKiro and generic OpenAI-compatible providers;
- local router API;
- web wizard;
- Grok Bot skill;
- one exact current-host compatibility entry after the transport probe;
- pause/resume, doctor, repair, restore-stock, uninstall;
- test fixtures and redacted diagnostics.

Excluded until a later version:

- Windows/macOS support;
- arbitrary remote router exposure;
- automatic provider failover chains;
- direct modification of native Bot profiles or `store.db`;
- copying proprietary Grok source;
- unknown-host bypasses;
- model-specific prompt rewriting without recorded capability evidence.

## 9. Acceptance criteria

The v1 release is successful only if all are true:

1. A user can select a real Bot by name and UUID in the wizard or skill.
2. With an active route, a normal Bot turn uses the selected external provider and does not silently use native Grok.
3. With the route paused, the same Bot uses native Grok.
4. The route survives router and host restarts without storing credentials in route state.
5. An unknown or changed host is refused by `check`/`repair`.
6. `restore-stock` produces the exact reviewed stock host.
7. A host update can be detected and repaired only after a reviewed compatibility entry is available.
8. All tests and VM acceptance evidence are reproducible from the GitHub repository.
