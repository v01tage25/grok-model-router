from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .redaction import redact_text

Confidence = Literal["confirmed", "candidate", "schema_only", "missing"]
Status = Literal["qualified", "blocked", "inconclusive"]


@dataclass(frozen=True)
class HostFingerprint:
    path: str
    size_bytes: int
    sha256: str
    version: str | None = None

    def __post_init__(self) -> None:
        if not self.path or self.size_bytes < 0 or len(self.sha256) != 64:
            raise ValueError("invalid host fingerprint")


@dataclass(frozen=True)
class Evidence:
    kind: str
    confidence: Confidence
    source: str
    detail: str

    def __post_init__(self) -> None:
        if self.confidence not in {"confirmed", "candidate", "schema_only", "missing"}:
            raise ValueError("invalid evidence confidence")


@dataclass(frozen=True)
class QualificationReport:
    status: Status
    fingerprint: HostFingerprint
    evidence: list[Evidence]
    blockers: list[str]
    observations: list[str]

    def __post_init__(self) -> None:
        if self.status not in {"qualified", "blocked", "inconclusive"}:
            raise ValueError("invalid qualification status")
        if not isinstance(self.blockers, list) or not all(isinstance(item, str) for item in self.blockers):
            raise ValueError("invalid blockers")
        if not isinstance(self.observations, list) or not all(isinstance(item, str) for item in self.observations):
            raise ValueError("invalid observations")
        if self.status == "qualified":
            if self.blockers or not any(
                item.kind == "ordinary-turn" and item.confidence == "confirmed"
                for item in self.evidence
            ):
                raise ValueError("qualified report lacks confirmed ordinary-turn evidence")

    def to_dict(self) -> dict[str, object]:
        fingerprint = asdict(self.fingerprint)
        fingerprint["path"] = redact_text(fingerprint["path"])
        fingerprint["version"] = redact_text(fingerprint["version"] or "") or None
        return {
            "status": self.status,
            "fingerprint": fingerprint,
            "evidence": [
                {
                    **asdict(item),
                    "kind": redact_text(item.kind),
                    "source": redact_text(item.source),
                    "detail": redact_text(item.detail),
                }
                for item in self.evidence
            ],
            "blockers": [redact_text(item) for item in self.blockers],
            "observations": [redact_text(item) for item in self.observations],
        }
