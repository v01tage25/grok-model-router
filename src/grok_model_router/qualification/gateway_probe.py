from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .models import Evidence
from .redaction import safe_presence


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


@dataclass(frozen=True)
class AgentSummary:
    agent_id: str
    name: str
    is_group: bool
    member_ids: tuple[str, ...]
    harness: str | None


def project_agent_rows(payload: object) -> tuple[AgentSummary, ...]:
    if not isinstance(payload, list):
        raise ValueError("agent catalog payload must be a list")

    rows: list[AgentSummary] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("agent catalog row must be an object")
        agent_id = item.get("id")
        name = item.get("name")
        member_ids = item.get("memberIds", [])
        harness = item.get("harness")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent catalog row has invalid id")
        if not isinstance(name, str):
            raise ValueError("agent catalog row has invalid name")
        if not isinstance(member_ids, list) or not all(isinstance(value, str) for value in member_ids):
            raise ValueError("agent catalog row has invalid memberIds")
        if harness is not None and not isinstance(harness, str):
            raise ValueError("agent catalog row has invalid harness")
        rows.append(
            AgentSummary(
                agent_id=agent_id,
                name=name,
                is_group=item.get("isGroup") is True,
                member_ids=tuple(member_ids),
                harness=harness,
            )
        )
    return tuple(rows)


def _assert_loopback(base_url: str) -> str:
    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"}:
        raise ValueError("gateway URL must be loopback HTTP")
    return base_url.rstrip("/") + "/api/listAgents"


def probe_list_agents(
    base_url: str,
    token: str | None,
    timeout_seconds: float = 5.0,
) -> tuple[AgentSummary, ...]:
    if not safe_presence(token):
        raise ValueError("gateway token is not set")
    request = urllib.request.Request(
        _assert_loopback(base_url),
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise ValueError(f"gateway returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError(f"gateway returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ValueError(f"gateway probe failed: {type(exc).__name__}") from None
    except json.JSONDecodeError:
        raise ValueError("gateway returned invalid JSON") from None
    return project_agent_rows(payload)


def catalog_evidence(
    rows: tuple[AgentSummary, ...],
    http_status: int | None,
    error: str | None,
) -> Evidence:
    if error is not None:
        return Evidence(
            kind="agent-catalog",
            confidence="missing",
            source="loopback gateway",
            detail="agent catalog probe failed",
        )
    if http_status != 200:
        return Evidence(
            kind="agent-catalog",
            confidence="missing",
            source="loopback gateway",
            detail="agent catalog did not return HTTP 200",
        )
    return Evidence(
        kind="agent-catalog",
        confidence="confirmed",
        source="loopback gateway",
        detail=f"projected {len(rows)} agent rows without transcript fields",
    )
