# Transport Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only qualification tool that identifies whether the current Grok Bot VM exposes a usable ordinary-turn inference boundary for a future patched transport, without changing the VM or claiming support from schema declarations alone.

**Architecture:** A local Python CLI reads an explicitly supplied host bundle and optional redacted runtime metadata, fingerprints the host, extracts source-derived transport candidates, and produces a sanitized JSON/Markdown verdict. A separate user-run probe can call the loopback gateway with an already supplied token to inventory Bots and validate response shape; it must never discover credentials from `/proc`, log request bodies, or send a chat prompt. The tool ends in `qualified`, `blocked`, or `inconclusive`; only `qualified` may feed the later adapter plan.

**Tech Stack:** Python 3.11+, standard library only for the qualification package, pytest for tests, JSON/Markdown reports, SHA-256, optional `curl`-compatible loopback probe invoked by the user. No production host patch, provider request, or GitHub publication in this plan.

**Spec:** [docs/superpowers/specs/2026-10-16-model-router-design.md](../specs/2026-10-16-model-router-design.md)

## Global Constraints

- Linux-first; current host candidate is `/opt/sand/sand-host/host-main.cjs`, but paths must be CLI arguments and no path is hardcoded as a supported production target.
- The qualification tool is read-only with respect to the host, agent stores, provider APIs, and GitHub.
- Never discover, print, persist, or transmit credential values; accepted inputs may contain credentials only through an environment variable used for a local authenticated probe, and reports must contain only `present: true/false`.
- Do not read or publish proprietary host bytes; local reports contain hashes, bounded token names, counts, and short redacted context, not bundle dumps.
- `sendPrompt` is not considered model-routable unless its verified contract carries provider/model data or the qualification traces a pre-inference boundary that can inject it.
- A declared `RequestedModel` protobuf type is evidence of a schema only, never evidence of an ordinary-turn transport.
- Unknown hash, missing anchor, ambiguous boundary, server-side-only execution, or an unverified quota path yields `blocked`/`inconclusive`; never guess or silently downgrade to a standalone runner.
- No network calls except an explicitly invoked loopback `listAgents` probe; no provider calls, paid calls, chat prompts, tool calls, or external HTTP calls.

## Review Focus

- A host bundle containing `modelId` only in protobuf declarations must be reported as schema-only, not qualified; test in Task 2.
- A changed/unknown host hash or duplicated/ambiguous transport anchor must refuse qualification and never produce an installable compatibility entry; test in Task 2.
- A loopback gateway response containing Bot descriptions or last-message previews must be projected to UUID/name/group/harness only; test in Task 3.
- Missing/invalid gateway credentials must produce a redacted status and no secret text in reports or exceptions; test in Task 3.
- Static evidence without a proof that ordinary turns cross the candidate boundary must end `inconclusive` and block patch planning; test in Task 4.

---

### Task 1: Qualification package and evidence data model

**Files:**
- Create: `pyproject.toml`
- Create: `src/grok_model_router/__init__.py`
- Create: `src/grok_model_router/qualification/__init__.py`
- Create: `src/grok_model_router/qualification/models.py`
- Create: `src/grok_model_router/qualification/redaction.py`
- Create: `tests/qualification/test_models.py`
- Create: `tests/qualification/test_redaction.py`

**Interfaces:**
- Produces `HostFingerprint(path: str, size_bytes: int, sha256: str, version: str | None)`.
- Produces `Evidence(kind: str, confidence: Literal["confirmed", "candidate", "schema_only", "missing"], source: str, detail: str)`.
- Produces `QualificationReport(status: Literal["qualified", "blocked", "inconclusive"], fingerprint: HostFingerprint, evidence: list[Evidence], blockers: list[str], observations: list[str])`.
- Produces `redact_text(text: str) -> str` and `safe_presence(value: str | None) -> bool`.
- Consumes no earlier task output.

- [ ] **Step 1: Write the failing tests**

```python
from grok_model_router.qualification.models import Evidence, QualificationReport
from grok_model_router.qualification.redaction import redact_text


def test_report_serialization_has_stable_status_and_no_secret_field():
    report = QualificationReport(
        status="inconclusive",
        fingerprint={"path": "/tmp/host-main.cjs", "size_bytes": 1, "sha256": "a" * 64, "version": "test"},
        evidence=[Evidence(kind="token", confidence="schema_only", source="fixture", detail="RequestedModel")],
        blockers=["ordinary transport not proven"],
        observations=[],
    )
    assert report.to_dict()["status"] == "inconclusive"
    assert "token" not in report.to_dict()


def test_redact_text_removes_bearer_and_api_key_values():
    text = "Authorization: Bearer super-secret API_KEY=abc123"
    cleaned = redact_text(text)
    assert "super-secret" not in cleaned
    assert "abc123" not in cleaned
    assert "<redacted>" in cleaned
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/qualification/test_models.py tests/qualification/test_redaction.py -q`
Expected: FAIL with import errors because the package and functions do not exist.

- [ ] **Step 3: Write the minimal implementation**

Implement dataclasses with strict literal status/confidence validation, `to_dict()` output containing only the declared public fields, and redaction patterns for `Authorization: Bearer`, common `*_API_KEY`, token/secret/password assignments, and long JWT-like values. Redaction must be deterministic and must not log the original value. Configure the package in `pyproject.toml` with a `grok-router-qualify` console entry point placeholder that Task 4 implements; do not add runtime dependencies.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/qualification/test_models.py tests/qualification/test_redaction.py -q`
Expected: PASS with all tests green.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/grok_model_router tests/qualification/test_models.py tests/qualification/test_redaction.py
git commit -m "feat: add qualification evidence model"
```

---

### Task 2: Read-only host fingerprint and source evidence scanner

**Files:**
- Create: `src/grok_model_router/qualification/host_scan.py`
- Create: `tests/qualification/fixtures/host-schema-only.cjs`
- Create: `tests/qualification/fixtures/host-ordinary-boundary.cjs`
- Create: `tests/qualification/test_host_scan.py`

**Interfaces:**
- Consumes `Evidence`, `HostFingerprint`, and `QualificationReport` from Task 1.
- Produces `fingerprint_host(path: Path, version_path: Path | None = None) -> HostFingerprint`.
- Produces `scan_host_source(path: Path) -> list[Evidence]`.
- Produces `evaluate_static_evidence(fingerprint: HostFingerprint, evidence: list[Evidence]) -> QualificationReport`.

- [ ] **Step 1: Write the failing tests**

```python
from pathlib import Path
from grok_model_router.qualification.host_scan import evaluate_static_evidence, fingerprint_host, scan_host_source


def test_schema_only_model_type_is_not_an_ordinary_transport(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_text(Path("tests/qualification/fixtures/host-schema-only.cjs").read_text(), encoding="utf-8")
    evidence = scan_host_source(host)
    report = evaluate_static_evidence(fingerprint_host(host), evidence)
    assert report.status == "inconclusive"
    assert any(item.confidence == "schema_only" for item in report.evidence)
    assert any("ordinary" in blocker for blocker in report.blockers)


def test_unknown_or_ambiguous_transport_is_blocked(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_text("function transport(){}\nfunction transport(){}\n", encoding="utf-8")
    report = evaluate_static_evidence(fingerprint_host(host), scan_host_source(host))
    assert report.status == "blocked"
    assert any("ambiguous" in blocker for blocker in report.blockers)


def test_fingerprint_is_sha256_and_version_is_optional(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_bytes(b"known fixture")
    fingerprint = fingerprint_host(host)
    assert fingerprint.size_bytes == len(b"known fixture")
    assert len(fingerprint.sha256) == 64
    assert fingerprint.version is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/qualification/test_host_scan.py -q`
Expected: FAIL because the scanner functions and fixtures do not exist.

- [ ] **Step 3: Write the minimal implementation**

Implement streaming SHA-256 and byte count; read a separate version file only when supplied. Scan bounded snippets and counts for request construction, actual outbound model call, response stream, tool/result mapping, Bot UUID propagation, and model fields. Classify protobuf/type declarations as `schema_only`. A candidate may not become `confirmed` from token presence alone. Treat zero matches as `missing`, one structurally matching boundary as `candidate`, and duplicates or conflicting boundaries as `blocked` evidence. `evaluate_static_evidence()` must return `inconclusive` unless an explicit ordinary-turn boundary is confirmed by a later dynamic evidence item; it must return `blocked` for ambiguous or malformed scan conditions.

Use fixture files that are independently authored and contain no vendor code. The schema-only fixture must include `RequestedModel` and `modelId` declarations but no request path. The ordinary-boundary fixture must include an explicit synthetic `ordinaryTurn -> transport.send(modelId, agentId)` path and a response stream marker.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/qualification/test_host_scan.py -q`
Expected: PASS; no test may inspect or execute a real vendor bundle.

- [ ] **Step 5: Commit**

```bash
git add src/grok_model_router/qualification/host_scan.py tests/qualification/fixtures tests/qualification/test_host_scan.py
git commit -m "feat: scan host fingerprints and transport evidence"
```

---

### Task 3: Redacted loopback agent catalog probe

**Files:**
- Create: `src/grok_model_router/qualification/gateway_probe.py`
- Create: `tests/qualification/fixtures/list-agents-response.json`
- Create: `tests/qualification/test_gateway_probe.py`

**Interfaces:**
- Consumes `redact_text`, `Evidence`, and `QualificationReport` from Tasks 1–2.
- Produces `AgentSummary(agent_id: str, name: str, is_group: bool, member_ids: tuple[str, ...], harness: str | None)`.
- Produces `project_agent_rows(payload: object) -> tuple[AgentSummary, ...]`.
- Produces `probe_list_agents(base_url: str, token: str | None, timeout_seconds: float = 5.0) -> tuple[AgentSummary, ...]`.
- Produces `catalog_evidence(rows: tuple[AgentSummary, ...], http_status: int | None, error: str | None) -> Evidence`.

- [ ] **Step 1: Write the failing tests**

```python
import json
from pathlib import Path
from grok_model_router.qualification.gateway_probe import project_agent_rows


def test_projection_discards_last_message_and_description():
    payload = json.loads(Path("tests/qualification/fixtures/list-agents-response.json").read_text())
    rows = project_agent_rows(payload)
    assert rows[0].agent_id == "agent-a"
    assert rows[0].name == "Sunny"
    assert rows[0].harness == "temporal"
    assert not hasattr(rows[0], "last_message_preview")
    assert not hasattr(rows[0], "description")


def test_invalid_payload_is_rejected_without_echoing_input():
    try:
        project_agent_rows({"token": "do-not-echo"})
    except ValueError as exc:
        assert "do-not-echo" not in str(exc)
    else:
        raise AssertionError("invalid payload must fail")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/qualification/test_gateway_probe.py -q`
Expected: FAIL because the projection and probe module do not exist.

- [ ] **Step 3: Write the minimal implementation**

Implement a strict projection that requires an array of objects with valid non-empty UUID-like `id` and string `name`; preserve only the declared summary fields. Use `urllib.request` with an explicit loopback URL check, `POST /api/listAgents`, JSON `{}`, and a bounded timeout. The token is accepted only as an in-memory function argument; never read `/proc`, never include it in an exception, and never log response bodies. On missing/invalid token return a redacted evidence item rather than attempting keyless retries. Reject non-loopback base URLs in this qualification tool.

The fixture must contain two synthetic rows, including one group and deliberately sensitive/large fields to prove projection removes them. The public report must contain only counts and safe identifiers supplied by the operator; do not save real VM rows in Git.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/qualification/test_gateway_probe.py -q`
Expected: PASS, including the no-echo assertion.

- [ ] **Step 5: Commit**

```bash
git add src/grok_model_router/qualification/gateway_probe.py tests/qualification/fixtures/list-agents-response.json tests/qualification/test_gateway_probe.py
git commit -m "feat: add redacted loopback agent probe"
```

---

### Task 4: Qualification report, CLI, and user-run VM procedure

**Files:**
- Create: `src/grok_model_router/qualification/report.py`
- Create: `src/grok_model_router/qualification/cli.py`
- Create: `scripts/collect-qualification.sh`
- Create: `tests/qualification/test_report.py`
- Create: `tests/qualification/test_cli.py`
- Create: `tests/qualification/test_verdict_template.py`
- Create: `README.md`
- Modify: `pyproject.toml` console entry point
- Create: `docs/qualification/README.md`

**Interfaces:**
- Consumes scanner/probe/report DTOs from Tasks 1–3.
- Produces `render_markdown(report: QualificationReport) -> str`.
- Produces CLI commands `scan`, `probe`, `report`, and `doctor` with exit codes: `0` qualified, `2` blocked/inconclusive, `3` invalid input.
- Produces sanitized reports at a caller-selected output path; never writes under `/opt/sand` by default.

- [ ] **Step 1: Write the failing tests**

```python
from grok_model_router.qualification.models import Evidence, QualificationReport
from grok_model_router.qualification.report import render_markdown


def test_markdown_is_explicitly_not_installable_when_inconclusive():
    report = QualificationReport(
        status="inconclusive",
        fingerprint={"path": "/safe/host.cjs", "size_bytes": 10, "sha256": "b" * 64, "version": "885e54d"},
        evidence=[Evidence(kind="modelId", confidence="schema_only", source="fixture", detail="declaration only")],
        blockers=["ordinary transport not proven"],
        observations=[],
    )
    text = render_markdown(report)
    assert "INCONCLUSIVE" in text
    assert "not installable" in text
    assert "b" * 64 in text
    assert "schema_only" in text


def test_cli_invalid_path_returns_code_three(tmp_path):
    from grok_model_router.qualification.cli import main
    assert main(["scan", "--host", str(tmp_path / "missing.cjs")]) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/qualification/test_report.py tests/qualification/test_cli.py -q`
Expected: FAIL because report/CLI modules do not exist.

- [ ] **Step 3: Write the minimal implementation**

Implement JSON and Markdown report output with status, fingerprint, evidence, blockers, and observations. Use uppercase status headings and an explicit `not installable` statement for anything other than `qualified`. Add CLI parsing with no hidden defaults: `--host` is required for `scan`, `--gateway` defaults only to `http://127.0.0.1:1340`, `--token-env` names an environment variable but its value is never printed, and `--output` is required for report-producing commands. `doctor` must be read-only and report process/gateway/credential presence without retrieving secret values.

The shell procedure must be an operator guide, not a pipe-to-shell installer. It must:

1. compute the current host PID/port/hash and version without printing environment values;
2. run `grok-router-qualify scan --host /opt/sand/sand-host/host-main.cjs --version-file /opt/sand/sand-host/version`;
3. optionally run `probe` only with a user-supplied `GATEWAY_TOKEN` environment variable;
4. write sanitized output under `/tmp/grok-router-qualification` or a caller-selected safe directory;
5. state that no host file is changed and no chat prompt is sent;
6. explain that an `inconclusive` verdict blocks transport implementation.

Do not include live VM UUIDs, descriptions, output dumps, or token-bearing commands in documentation or fixtures.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/qualification -q`
Expected: PASS for all qualification tests.

Run: `python -m grok_model_router.qualification.cli scan --help`
Expected: help text exits `0` and contains no installer or patch command.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/grok_model_router/qualification scripts/collect-qualification.sh docs/qualification tests/qualification
git commit -m "feat: add read-only transport qualification CLI"
```

---

### Task 5: Qualification review gate and handoff

**Files:**
- Create: `docs/qualification/VERDICT-template.md`
- Modify: `README.md`
- Modify: `docs/superpowers/2026-10-16-implementation-roadmap.md`

**Interfaces:**
- Consumes the report format and CLI from Task 4.
- Produces a reviewable qualification packet with explicit status and evidence boundaries.

- [ ] **Step 1: Write the failing documentation check**

Create a test that loads `docs/qualification/VERDICT-template.md` and asserts it contains all three allowed statuses (`qualified`, `blocked`, `inconclusive`), a `ordinary-turn` evidence section, a `quota-independence` section, and a `next gate` section. The test must also assert that the word `install` appears only in a negative statement for non-qualified reports; the qualification packet cannot accidentally present itself as an installer.

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/qualification/test_verdict_template.py -q`
Expected: FAIL because the template and test do not exist.

- [ ] **Step 3: Write the template and handoff docs**

The template must require:

- host fingerprint/version and collection timestamp;
- exact static evidence and confidence tier;
- gateway roster probe status/count only;
- ordinary-turn boundary proof or exact missing proof;
- whether the inference execution is local, remote, or unknown;
- provider request/response/tool/stream contract status;
- maintenance/summary/model path status;
- quota independence status;
- explicit blockers and next owner decision;
- `installable: false` unless all qualification conditions are proven.

README must state that the repository is currently a qualification tool, not an installer or supported transport patch. The roadmap must mark Tasks Q1–Q5 as the first gate and keep runtime/patch tasks unstarted until a human reviews a `qualified` packet.

- [ ] **Step 4: Run documentation and full tests**

Run: `python -m pytest tests/qualification -q`
Expected: PASS.

Run: `git diff --check`
Expected: no whitespace errors.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/qualification docs/superpowers/2026-10-16-implementation-roadmap.md tests/qualification/test_verdict_template.py
git commit -m "docs: define transport qualification handoff"
```

## Completion contract

The plan is complete only when:

- all Tasks 1–5 commits exist and `python -m pytest tests/qualification -q` passes;
- a sanitized report was generated from the current host without modifying it;
- the report status is explicitly `qualified`, `blocked`, or `inconclusive`;
- no production patch, provider request, chat prompt, or GitHub publication was performed;
- if status is not `qualified`, the user sees the exact blocker and the next decision before any runtime/patch plan is written.

## Handoff

This is the first plan, not the full Model Router implementation. After the user reviews it, choose **Native** execution for the local qualification package or **Subagent-driven** execution if an independent reviewer is desired. The next plan may be written only after the qualification report proves a patchable ordinary-turn boundary.
