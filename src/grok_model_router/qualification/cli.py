from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Sequence

from .gateway_probe import _NoRedirect, _assert_loopback, catalog_evidence, probe_list_agents
from .host_scan import evaluate_static_evidence, fingerprint_host, scan_host_source
from .models import Evidence, HostFingerprint, QualificationReport
from .report import render_markdown


def _status_code(status: str) -> int:
    return 0 if status == "qualified" else 2


def _write(path: str | None, text: str) -> None:
    if path is None:
        print(text, end="")
    else:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _scan(args: argparse.Namespace) -> int:
    host = Path(args.host)
    if not host.is_file():
        print(f"invalid host path: {host}")
        return 3
    version = Path(args.version_file) if args.version_file else None
    try:
        report = evaluate_static_evidence(
            fingerprint_host(host, version),
            scan_host_source(host),
        )
    except (OSError, ValueError):
        print("invalid host or version input")
        return 3
    payload = json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
    _write(args.output, payload)
    return _status_code(report.status)


def _probe(args: argparse.Namespace) -> int:
    token = os.environ.get(args.token_env)
    try:
        rows = probe_list_agents(args.gateway, token, args.timeout)
        evidence = catalog_evidence(rows, 200, None)
        payload = {"count": len(rows), "evidence": evidence.__dict__}
        _write(args.output, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        return 0
    except ValueError as exc:
        evidence = catalog_evidence((), None, str(exc))
        _write(args.output, json.dumps({"count": 0, "evidence": evidence.__dict__}, indent=2) + "\n")
        return 2


def _report(args: argparse.Namespace) -> int:
    source = Path(args.input)
    if not source.is_file():
        print(f"invalid report path: {source}")
        return 3
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        fingerprint = HostFingerprint(**payload["fingerprint"])
        evidence = [Evidence(**item) for item in payload["evidence"]]
        if payload["status"] == "qualified":
            raise ValueError("qualified reports require trusted qualification provenance")
        report = QualificationReport(
            status=payload["status"],
            fingerprint=fingerprint,
            evidence=evidence,
            blockers=payload["blockers"],
            observations=payload["observations"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        print("invalid qualification report")
        return 3
    _write(args.output, render_markdown(report))
    return _status_code(report.status)


def _doctor(args: argparse.Namespace) -> int:
    try:
        health_url = _assert_loopback(args.gateway).rsplit("/api/listAgents", 1)[0] + "/health"
    except ValueError as exc:
        _write(args.output, json.dumps({"error": str(exc)}) + "\n")
        return 3
    request = urllib.request.Request(health_url)
    try:
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=args.timeout) as response:
            healthy = response.status == 200
    except (urllib.error.URLError, TimeoutError):
        healthy = False
    payload = {"gateway": args.gateway, "health": "ok" if healthy else "unreachable"}
    _write(args.output, json.dumps(payload, indent=2) + "\n")
    return 0 if healthy else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="grok-router-qualify")
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan")
    scan.add_argument("--host", required=True)
    scan.add_argument("--version-file")
    scan.add_argument("--output")
    scan.set_defaults(handler=_scan)

    probe = commands.add_parser("probe")
    probe.add_argument("--gateway", default="http://127.0.0.1:1340")
    probe.add_argument("--token-env", required=True)
    probe.add_argument("--timeout", type=float, default=5.0)
    probe.add_argument("--output")
    probe.set_defaults(handler=_probe)

    report = commands.add_parser("report")
    report.add_argument("--input", required=True)
    report.add_argument("--output")
    report.set_defaults(handler=_report)

    doctor = commands.add_parser("doctor")
    doctor.add_argument("--gateway", default="http://127.0.0.1:1340")
    doctor.add_argument("--timeout", type=float, default=3.0)
    doctor.add_argument("--output")
    doctor.set_defaults(handler=_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
