from __future__ import annotations

from .models import QualificationReport
from .redaction import redact_text


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
        f"- Path: `{redact_text(report.fingerprint.path)}`",
        f"- Size: `{report.fingerprint.size_bytes}` bytes",
        f"- SHA-256: `{report.fingerprint.sha256}`",
        f"- Version: `{redact_text(report.fingerprint.version or 'unknown')}`",
        "",
        "## Evidence",
        "",
    ]
    lines.extend(
        f"- `{redact_text(item.kind)}` / `{item.confidence}` — {redact_text(item.detail)} (`{redact_text(item.source)}`)"
        for item in report.evidence
    )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {redact_text(blocker)}" for blocker in report.blockers or ["none"])
    lines.extend(["", "## Observations", ""])
    lines.extend(f"- {redact_text(observation)}" for observation in report.observations or ["none"])
    return "\n".join(lines) + "\n"
