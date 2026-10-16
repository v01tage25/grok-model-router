# Model Router implementation roadmap

**Date:** 2026-10-16
**State:** Specification approved; execution has not started.
**Spec:** [Approved design](specs/2026-10-16-model-router-design.md)
**First executable plan:** [Transport qualification](plans/2026-10-16-transport-qualification.md)

## Outcome

Preserve the ordinary Grok Bot chat and tool/permission behavior while routing all inference for a selected Bot UUID to the chosen external provider. Supply a Bot → provider → model wizard, a managing skill, persistent rules, explicit native pause/resume, reversible install, and reviewed update repair. Publish only original code, tests, and sanitized diagnostics to a new GitHub repository.

## Evidence and corrections

The user performed all VM commands; there is no direct VM connection in this session. The following are observed evidence, not compatibility guarantees:

- `POST http://127.0.0.1:1340/api/listAgents` returned HTTP 200.
- It returned 12 rows: ten individual Bots and two groups. Every row reported `harness: "temporal"`.
- Sunny UUID: `4c3499aa-126a-4b8a-89cb-bf9e1b4c48b7`. This is installation-specific data and must not be hardcoded into product defaults or published fixtures.
- The observed host version was `885e54d`, size 30009308 bytes, SHA-256 `c58f16da00fca0bf48effad74295c735deee10377753fb5f50afc290e3af29e6`. A later restart occurred. Re-fingerprint before using this evidence.
- `sendPromptFields` has no provider, endpoint, model ID, or model-parameter fields.
- `buildCloudAgentRequestedModel` is used in a background-composer path; that does not establish a transport for the ordinary Bot turn.
- Declared protobuf types are not proof of implemented handlers, custom endpoint support, or an independently usable BYOK path.
- A successful `/models` call to xKiro is not proof that chat completions, tool calls, or native Bot routing work.
- Absence of a named SQLite column is not proof that metadata never contains model information.
- OpenGrok was removed from the VM. The failed dry-run did not modify the live host.

The approved design's goal is a requirement, **not a claim that the current VM supports it**. No product may claim quota independence based only on the roster API or provider catalog. In particular, an instruction-only skill that calls a provider after a native model turn still depends on that native turn and does not satisfy this project.

## Why separate plans

There are three independently reviewable deliverables: transport qualification, the routing runtime, and the integration/release. The production patch cannot be specified honestly until its input/output contract and execution location are known. The first plan therefore produces a bounded qualification report and no host modification. A failure leaves the full product scope open; it does not silently substitute a standalone chat UI or CLI relay.

## Stage Q — qualify the real ordinary-turn transport

**Execute:** `plans/2026-10-16-transport-qualification.md`.

**Deliverables:** read-only bundle inspector, compact redacted report, user-run VM collection procedure, source-derived trace of `sendPrompt → temporal/server-agent proxy → actual inference boundary`, and a written verdict.

**Go condition:** a specific accessible boundary exists for ordinary selected-Bot turns, carries UUID, and can replace inference without invoking a quota-gated native model first. Its request, text/reasoning/tool-stream, cancellation, permissions, maintenance calls, and transcript-return contracts are identified. A reviewed local mock can exercise the same contract without live provider calls.

**Blocked condition:** the VM only forwards turns to inaccessible server-side execution, the required boundary is not present, or the transport is unknown. Preserve evidence, state the missing capability, and ask whether to change scope or provide a supported integration. Do not invent an endpoint, bypass a server entitlement, or label a failed qualification supported.

**Next user gate:** review the qualification report. Production adapter planning is authorized only for a demonstrated boundary.

## Stage R — provider routing runtime, API, and UX

Write a separate executable TDD plan after Stage Q succeeds. No host patch in this stage.

### Proposed file ownership

```text
pyproject.toml                       Python >=3.11; package and CLI metadata
src/grok_model_router/domain.py      immutable Agent/Route/Provider/Error DTOs
src/grok_model_router/config.py      explicit provider URLs, env names, paths
src/grok_model_router/secrets.py     secret lookup; never exposes secret values
src/grok_model_router/store.py       SQLite migrations, transactions, epochs
src/grok_model_router/catalog.py     roster projection and freshness
src/grok_model_router/gateway.py     authenticated, allowlisted roster call only
src/grok_model_router/providers/     OpenAI-compatible and xKiro adapters
src/grok_model_router/streaming.py    bounded SSE framing and cancellation
src/grok_model_router/routing.py      external/native decision and epoch checks
src/grok_model_router/api.py          versioned authenticated loopback API
src/grok_model_router/cli.py          shared CLI for operators and skill
src/grok_model_router/static/        wizard assets; no external CDN
skills/model-router/SKILL.md         configuration workflow, not inference relay
skills/model-router/scripts/         CLI wrapper with explicit agent identity
examples/providers.example.json     configuration names, not credentials
```

Python dependencies are chosen in that stage's plan from requirements, not installed speculatively. Prefer a single maintained streaming HTTP client and a small tested ASGI stack over a custom security-sensitive HTTP parser. Pin dependencies and include a lockfile. No Node frontend build is required merely to offer the wizard.

### R1 — state and configuration

- UUID-keyed routes; SQLite schema version; transactional compare-and-swap using `expected_epoch`.
- State: provider ID, exact upstream model ID, active/paused, epoch, timestamps, optional validated parameters, health code.
- Preserve history/transcript outside route state. `/router reset` increments epoch and invalidates only router-owned provider continuation; it must not clear native chat history.
- Secrets are env values or explicitly configured private secret storage. Never store a raw key in route/provider DB records.
- A malformed config is a failure, not an automatic default route. Provider URL must end in `/v1` with no userinfo, query, or fragment. HTTPS required except explicit loopback providers.
- Test concurrent UI/skill writes, stale epoch, interrupted transaction, file permissions, Unicode/duplicate Bot names, and unknown UUID.

### R2 — roster and providers

- `POST /api/listAgents` through the gateway with a user-provisioned credential; do not discover tokens by scraping `/proc` in the product.
- Project responses to `id`, `name`, `isGroup`, `memberIds`, `harness`, freshness. Do not log/store last messages, description, or avatars for the picker.
- Exclude group-room rows from single-Bot routing; group configuration resolves individual member UUIDs explicitly. No name-only ambiguous updates.
- Use `Authorization: Bearer` only to the configured provider origin. Do not follow cross-origin redirects with credentials.
- xKiro User-Agent configurable as a compatibility header; GET `/models` success alone does not establish the exact cause of earlier Python 403 responses.
- `/models` listing, strict non-streaming completion, chunk-safe SSE completion, multiple tool calls, Unicode boundaries, usage, cancellation, EOF-before-DONE, content-size and time limits.
- Tests use a local mock provider. Paid network probes are opt-in with an explicit token/output cap; no retries after output/tool side effects.

### R3 — control/inference API

Candidate route names (freeze exact schemas in the Stage R plan):

- `GET /healthz` process liveness, no private state;
- `GET /readyz` structured readiness, including unsupported host vs missing key;
- `GET /v1/agents`, `/v1/providers`, `/v1/providers/{id}/models`;
- `GET /v1/routes/{uuid}`;
- `PUT /v1/routes/{uuid}` with provider/model/validated params and `expected_epoch`;
- `POST /v1/routes/{uuid}/pause`, `/resume`, `/reset` with `expected_epoch`;
- `GET /v1/doctor` safe codes and fingerprints only;
- authenticated transport endpoint whose envelope is derived in Q, not assumed OpenAI-compatible on the host-facing side.

Separate admin and inference credentials. UI requires session auth and CSRF/origin checks. Reject arbitrary browser origins; loopback is not authentication. CLI and skill use the same validated control operations, never arbitrary gateway passthrough.

Route choices: unconfigured → native; paused → native; active and ready → external; active with provider/router failure → explicit error, never native fallback. The patched shim must make this decision safe even if routerd is down; it must have trusted persisted activation information or another proven mechanism. Freeze that mechanism in Stage I; a network failure must not be treated as pause.

Epoch transitions cancel old requests. Already delivered text or tool effects cannot be undone; the UI must state that a change takes effect for new inference and cancels the ongoing external generation, rather than promise retroactive removal. Do not retry completed/partially emitted tool calls.

### R4 — web wizard and skill

- Bot → provider → model → disclosure/summary → save; show UUID, epoch, freshness, compatibility, credential-present status, and effective route.
- On an unsupported host, allow configuration drafts but never display a route as live/active.
- Pause/resume affects future turns; never pauses the vendor service or changes its tool permissions.
- Accessible keyboard controls, inline validation, conflict refresh, loading/error state, no pure black, local assets.
- Skill calls CLI/API deterministically. It can configure routing while a model is available, but the native chat slash command interception needed to operate after quota exhaustion must run before inference at the qualified boundary. A prompt skill by itself is not that interceptor.
- Provider ID and upstream model ID are separate structured fields. For `/model provider-id/model-id`, split only the first slash, preserving `x-ai/grok-4.7` intact.
- Provider-only changes require model choice; never keep a model from another provider silently.
- Test browser auth/CSRF, XSS via Bot/model names, multiple concurrent tabs, stale roster, duplicate names, per-member targeting in groups, and absence of keys in DOM or command history.

## Stage I — qualified host adapter and reversible installer

Write a separate executable plan using Q's actual contracts and R's frozen interfaces.

### Proposed file ownership

```text
adapter/host-shim.cjs                minimal host-side adapter; actual interface from Q
compatibility/registry.json          reviewed fingerprints and adapter recipe IDs
compatibility/recipes/              version-specific deterministic transforms
src/grok_model_router/patching/      check, backup, stage, activate, restore
src/grok_model_router/service.py     user-owned VM lifecycle integration
scripts/install.sh                  reviewed local installer, no curl|bash chain
tests/fixtures/transport/            independently authored contract fixtures only
```

### I1 — offline patch and contract proof

- Exact stock fingerprint plus anchors plus supported semantic structure. No production allowlist entry from regex similarity alone.
- Fingerprint the observed host afresh. Never import/execute vendor bundle in analysis or public CI.
- Proprietary originals/backups stay on the user's VM, excluded from Git. Public tests use independently authored fixtures. Verify reference repository license before copying anything; initial approach is independent code only.
- Adapter must preserve native text/reasoning/tool definitions, result mapping, permissions, cancellation, heartbeats, usage, and transcript path. Unsupported protocol cases fail explicitly.
- Inspect maintenance/summarization/tool-side inference separately. If native quota is still required for a necessary maintenance call, the quota-independence requirement is not met. Do not ship with a hidden maintenance dependency.
- Unit tests prove unknown hash/anchor refusal, idempotence, exact stock restore, adapter/native branch, epoch cancellation, stream/tool mapping, and router unavailable while active.

### I2 — transactional installation and repair

- Resolve canonical paths and refuse symlinks or unexpected owner/type; check free space and executable permissions; no sudo as an automatic fallback.
- Under a single installer lock: fingerprint, immutable timestamped backup + digest, stage in the target filesystem, syntax check, mock adapter smoke, re-fingerprint live target, atomic rename.
- Precondition: user-approved idle host/supervisor-aware restart method, independently verified for this VM. Never raw-kill host/supervisor or edit authentication/attestation/security logic.
- Journal before/after hashes and ownership manifest. A crash leaves diagnosable state; no success receipt before readiness.
- Repeated install is a no-op for the exact reconstructed adapter output; foreign modified hosts are refused.
- `repair` can activate only a reviewed stock input or exactly identified previously installed output. Never restore an old stock over an unknown vendor update.
- Unknown update: warn, mark compatibility unavailable, leave vendor host untouched; do not promise persistent enforcement while a vendor replacement is unpatched. Hard quota-independent routing cannot be guaranteed during unsupported updates.
- Restore verifies the current installed output and stock-backup digest, stages and syntax-checks stock, disables repair, atomically restores, verifies readiness.
- Uninstall removes only owned files after restore; unknown files and Bot data survive. Credentials are preserved or removed only by explicit operator choice.
- Service integration uses the supported user lifecycle discovered in Q. Automatic startup/repair is explicit opt-in; watchdog health must be separate from router health.

### I3 — acceptance and release

On a disposable or backed-up VM, use an explicitly selected test Bot, not an entire fleet:

1. Read-only preflight and fresh fingerprint.
2. Dry-run and reviewed patch on a local copy.
3. Install, supervisor-safe restart, readiness.
4. Normal native UI message → external provider evidence (opaque request IDs/counts, not transcript logs).
5. Tool round trip with approval preserved; attachments where supported.
6. Provider error and router outage → explicit error, zero native inference attempts.
7. Native quota exhausted/unavailable test in a controlled test fixture and, when an account naturally reaches the condition, actual UI evidence. Do not modify billing/entitlement controls to simulate it.
8. Pause → native path; resume → external path; epoch cancels old generation.
9. Restart service and host → route preserved.
10. Reviewed update fixture → repair; unknown update fixture → refusal.
11. Restore stock → byte-identical reviewed input, native readiness; uninstall preserves Bot data.

Publish source only after secret/data scanning and the user's review of repository metadata. The user requested GitHub creation/push; choose exact owner/name/visibility at release (private recommended for initial validation), do not infer public publication consent. Never include VM profiles, proprietary host bytes, dumps, conversation text, tokens, or backup archives. Use `gh`; show repository URL and commit SHA. After any PR, bind desktop PR status and use its monitoring instead of polling CI.

## Requirement coverage

| Spec sections | Owning stage |
|---|---|
| 1, 2, 3.5: ordinary Bot inference and actual boundary | Q; then I1/I3 |
| 3.1: daemon, health, readiness, versioned local API | R3 |
| 3.2: Bot UUID roster, freshness, names | R2/R4 |
| 3.3: persistence, atomicity, epochs, late replies | R1/R3 |
| 3.4: providers, exact models, auth, streaming/errors | R2 |
| 4: lifecycle, update repair, stock restore, uninstall | I2/I3 |
| 5: wizard, pause/resume, skill and scope | R4; pre-inference interceptor I1 |
| 6: credentials, origin checks, pins, data boundary | R1–R4/I1–I3 |
| 7: unit/provider/patch/VM evidence | Every stage; end-to-end I3 |
| 8, 9: Linux scope and release acceptance | Q gates; R/I completion gates |

## State and remaining gates

- VM OpenGrok cleanup: user-confirmed complete.
- Scope specification: user-approved 2026-10-16.
- Transport qualification package: implemented and tested in the native worktree; VM verdict is still pending.
- Runtime/adapter implementation: not started.
- GitHub creation/publication: not started.
- Canonical work-state MCP: two HTTP 400 ValidationError responses in planning turn; no successful task-state entry. Do not claim state convergence. This document is the visible progress record until the MCP schema issue is reconciled.
- Next action: run the qualification package against the VM and review its sanitized verdict. No host changes until qualified input and explicit installation approval.
