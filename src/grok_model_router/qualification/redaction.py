from __future__ import annotations

import re

_BEARER = re.compile(r"(\bAuthorization\s*:\s*Bearer\s+)[^\s,;]+", re.IGNORECASE)
_ASSIGNMENT = re.compile(
    r"(\b(?:api[_-]?key|token|secret|password|credential)\s*[:=]\s*)([\"']?)([^\s,;\"']+)",
    re.IGNORECASE,
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def redact_text(text: str) -> str:
    result = _BEARER.sub(r"\1<redacted>", text)
    result = _ASSIGNMENT.sub(r"\1\2<redacted>", result)
    return _JWT.sub("<redacted>", result)


def safe_presence(value: str | None) -> bool:
    return value is not None and bool(value.strip())
