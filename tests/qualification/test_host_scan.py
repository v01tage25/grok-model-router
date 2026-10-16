from pathlib import Path

from grok_model_router.qualification.host_scan import (
    evaluate_static_evidence,
    fingerprint_host,
    scan_host_source,
)


def test_schema_only_model_type_is_not_an_ordinary_transport(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_text(
        Path("tests/qualification/fixtures/host-schema-only.cjs").read_text(),
        encoding="utf-8",
    )

    evidence = scan_host_source(host)
    report = evaluate_static_evidence(fingerprint_host(host), evidence)

    assert report.status == "inconclusive"
    assert any(item.confidence == "schema_only" for item in report.evidence)
    assert any("ordinary" in blocker for blocker in report.blockers)


def test_unknown_or_ambiguous_transport_is_blocked(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_text("function transport(){}\nfunction transport(){}\n", encoding="utf-8")

    report = evaluate_static_evidence(fingerprint_host(host), scan_host_source(host))

    assert report.status == "blocked"
    assert any("ambiguous" in blocker for blocker in report.blockers)


def test_fingerprint_is_sha256_and_version_is_optional(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_bytes(b"known fixture")

    fingerprint = fingerprint_host(host)

    assert fingerprint.size_bytes == len(b"known fixture")
    assert len(fingerprint.sha256) == 64
    assert fingerprint.version is None


def test_fingerprint_redacts_untrusted_version_file(tmp_path: Path):
    host = tmp_path / "host.cjs"
    version = tmp_path / "version"
    host.write_bytes(b"fixture")
    version.write_text("SAND_GATEWAY_TOKEN=do-not-echo", encoding="utf-8")

    fingerprint = fingerprint_host(host, version)

    assert fingerprint.version != "SAND_GATEWAY_TOKEN=do-not-echo"
    assert "do-not-echo" not in (fingerprint.version or "")


def test_telemetry_transport_send_is_not_model_boundary(tmp_path: Path):
    host = tmp_path / "host.cjs"
    host.write_text(
        Path("tests/qualification/fixtures/host-telemetry-transport.cjs").read_text(),
        encoding="utf-8",
    )

    evidence = scan_host_source(host)
    report = evaluate_static_evidence(fingerprint_host(host), evidence)

    assert report.status == "inconclusive"
    assert not any(item.confidence == "candidate" for item in evidence)
