from __future__ import annotations

from .models import QualificationReport


def render_markdown(report: QualificationReport) -> str:
    status = report.status.upper()
    lines = [
        f"# Transport qualification: {status}",
        "",
        f"**Status:** `{report.status}`",
        "**Installable:** no — this report is not installable and is not patch authorization.",
        "",
        "## Host fingerprint",
        "",
        f"- Path: `{report.fingerprint.path}`",
        f"- Size: `{report.fingerprint.size_bytes}` bytes",
        f"- SHA-256: `{report.fingerprint.sha256}`",
        f"- Version: `{report.fingerprint.version or 'unknown'}`",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(
        f"- `{item.kind}` / `{item.confidence}` — {item.detail} (`{item.source}`)"
        for item in report.evidence
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {blocker}" for blocker in report.blockers or ["none"])
    lines.extend(["", "## Observations", ""])
    lines.extend(f"- {observation}" for observation in report.observations or ["none"])
    return "\n".join(lines) + "\n"
