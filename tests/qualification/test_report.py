from grok_model_router.qualification.models import Evidence, HostFingerprint, QualificationReport
from grok_model_router.qualification.report import render_markdown


def test_markdown_is_explicitly_not_installable_when_inconclusive():
    report = QualificationReport(
        status="inconclusive",
        fingerprint=HostFingerprint(
            path="/safe/host.cjs",
            size_bytes=10,
            sha256="b" * 64,
            version="885e54d",
        ),
        evidence=[
            Evidence(
                kind="modelId",
                confidence="schema_only",
                source="fixture",
                detail="declaration only",
            )
        ],
        blockers=["ordinary transport not proven"],
        observations=[],
    )

    text = render_markdown(report)

    assert "INCONCLUSIVE" in text
    assert "not installable" in text
    assert "b" * 64 in text
    assert "schema_only" in text


def test_markdown_redacts_evidence_and_fingerprint_metadata():
    report = QualificationReport(
        status="inconclusive",
        fingerprint=HostFingerprint(
            path="/tmp/API_KEY=path-secret",
            size_bytes=10,
            sha256="c" * 64,
            version="SAND_TOKEN=version-secret",
        ),
        evidence=[
            Evidence(
                kind="transport",
                confidence="candidate",
                source="Authorization: Bearer evidence-secret",
                detail="Authorization: Bearer detail-secret",
            )
        ],
        blockers=["ordinary transport not proven"],
        observations=["password=observation-secret"],
    )

    text = render_markdown(report)

    for value in ("path-secret", "version-secret", "evidence-secret", "detail-secret", "observation-secret"):
        assert value not in text
    assert "<redacted>" in text
