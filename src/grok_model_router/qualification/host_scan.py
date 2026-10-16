from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .models import Evidence, HostFingerprint, QualificationReport
from .redaction import redact_text

_TRANSPORT_DEF = re.compile(r"function\s+transport\s*\(")
_ORDINARY_SEND = re.compile(r"transport\.send\s*\(.*?agentId.*?modelId", re.DOTALL)


def fingerprint_host(path: Path, version_path: Path | None = None) -> HostFingerprint:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)

    version = None
    if version_path is not None:
        if not version_path.is_file():
            raise ValueError("version file not found")
        version = redact_text(version_path.read_text(encoding="utf-8", errors="replace").strip()) or None

    return HostFingerprint(
        path=str(path),
        size_bytes=size,
        sha256=digest.hexdigest(),
        version=version,
    )


def scan_host_source(path: Path) -> list[Evidence]:
    text = path.read_text(encoding="utf-8", errors="replace")
    evidence: list[Evidence] = []

    if "RequestedModel" in text and "modelId" in text and not _ORDINARY_SEND.search(text):
        evidence.append(
            Evidence(
                kind="model-schema",
                confidence="schema_only",
                source=str(path),
                detail="RequestedModel/modelId declaration without an ordinary transport call",
            )
        )

    transport_definitions = len(_TRANSPORT_DEF.findall(text))
    if transport_definitions > 1:
        evidence.append(
            Evidence(
                kind="transport",
                confidence="missing",
                source=str(path),
                detail=f"ambiguous transport anchor: {transport_definitions} matching definitions",
            )
        )
    elif _ORDINARY_SEND.search(text):
        evidence.append(
            Evidence(
                kind="ordinary-turn",
                confidence="candidate",
                source=str(path),
                detail="candidate transport call carries agentId and modelId",
            )
        )
    else:
        evidence.append(
            Evidence(
                kind="ordinary-turn",
                confidence="missing",
                source=str(path),
                detail="no source-derived ordinary-turn transport boundary",
            )
        )

    return evidence


def evaluate_static_evidence(
    fingerprint: HostFingerprint,
    evidence: list[Evidence],
) -> QualificationReport:
    blockers: list[str] = []
    observations: list[str] = []

    if any("ambiguous" in item.detail for item in evidence):
        blockers.append("ambiguous transport evidence")
        status = "blocked"
    else:
        ordinary = [item for item in evidence if item.kind == "ordinary-turn"]
        if not any(item.confidence in {"candidate", "confirmed"} for item in ordinary):
            blockers.append("ordinary transport not proven")
        else:
            blockers.append("dynamic ordinary-turn proof is still required")
        status = "inconclusive"

    if any(item.confidence == "schema_only" for item in evidence):
        observations.append("model fields were found only in schema-like declarations")

    return QualificationReport(
        status=status,
        fingerprint=fingerprint,
        evidence=evidence,
        blockers=blockers,
        observations=observations,
    )
