from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Confidence = Literal["confirmed", "candidate", "schema_only", "missing"]
Status = Literal["qualified", "blocked", "inconclusive"]


@dataclass(frozen=True)
class HostFingerprint:
    path: str
    size_bytes: int
    sha256: str
    version: str | None = None


@dataclass(frozen=True)
class Evidence:
    kind: str
    confidence: Confidence
    source: str
    detail: str


@dataclass(frozen=True)
class QualificationReport:
    status: Status
    fingerprint: HostFingerprint
    evidence: list[Evidence]
    blockers: list[str]
    observations: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "fingerprint": asdict(self.fingerprint),
            "evidence": [asdict(item) for item in self.evidence],
            "blockers": list(self.blockers),
            "observations": list(self.observations),
        }
