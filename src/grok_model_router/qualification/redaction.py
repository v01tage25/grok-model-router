from __future__ import annotations

import re

_AUTH = re.compile(r"(\b(?:Authorization\s*:\s*)?(?:Bearer|Basic)\s+)[^\s,;]+", re.IGNORECASE)
_ASSIGNMENT = re.compile(
    r"(\b(?:[A-Za-z_][A-Za-z0-9_-]*(?:api[_-]?key|token|secret|password|credential)|api[_-]?key|token|secret|password|credential)\s*[:=]\s*)([\"']?)([^\s,;\"']+)",
    re.IGNORECASE,
)
_JSON = re.compile(
    r"(\"(?:api[_-]?key|token|secret|password|credential|cookie)\"\s*:\s*\")([^\"]+)(\")",
    re.IGNORECASE,
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def redact_text(text: str) -> str:
    result = _AUTH.sub(r"\1<redacted>", text)
    result = _ASSIGNMENT.sub(r"\1\2<redacted>", result)
    result = _JSON.sub(r"\1<redacted>\3", result)
    return _JWT.sub("<redacted>", result)


def safe_presence(value: str | None) -> bool:
    return value is not None and bool(value.strip())
