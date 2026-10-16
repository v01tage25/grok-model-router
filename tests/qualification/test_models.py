from grok_model_router.qualification.models import Evidence, HostFingerprint, QualificationReport
from grok_model_router.qualification.redaction import redact_text


def test_report_serialization_has_stable_status_and_no_secret_field():
    report = QualificationReport(
        status="inconclusive",
        fingerprint=HostFingerprint(
            path="/tmp/host-main.cjs",
            size_bytes=1,
            sha256="a" * 64,
            version="test",
        ),
        evidence=[
            Evidence(
                kind="modelId",
                confidence="schema_only",
                source="fixture",
                detail="RequestedModel declaration only",
            )
        ],
        blockers=["ordinary transport not proven"],
        observations=[],
    )

    payload = report.to_dict()
    assert payload["status"] == "inconclusive"
    assert "secret" not in payload
    assert payload["fingerprint"]["sha256"] == "a" * 64


def test_redact_text_removes_bearer_and_api_key_values():
    text = "Authorization: Bearer super-secret API_KEY=abc123"

    cleaned = redact_text(text)

    assert "super-secret" not in cleaned
    assert "abc123" not in cleaned
    assert "<redacted>" in cleaned


def test_report_rejects_unknown_status_and_confidence():
    import pytest

    with pytest.raises(ValueError):
        QualificationReport(
            status="forged",
            fingerprint=HostFingerprint("path", 1, "a" * 64),
            evidence=[],
            blockers=[],
            observations=[],
        )
    with pytest.raises(ValueError):
        Evidence(kind="x", confidence="forged", source="x", detail="x")
