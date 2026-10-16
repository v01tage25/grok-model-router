#!/usr/bin/env bash
set -euo pipefail

HOST_PATH="${HOST_PATH:-/opt/sand/sand-host/host-main.cjs}"
VERSION_PATH="${VERSION_PATH:-/opt/sand/sand-host/version}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/grok-router-qualification}"
mkdir -p "$OUTPUT_DIR"

python -m grok_model_router.qualification.cli scan \
  --host "$HOST_PATH" \
  --version-file "$VERSION_PATH" \
  --output "$OUTPUT_DIR/host.json" || scan_status=$?
scan_status="${scan_status:-0}"
python -m grok_model_router.qualification.cli report \
  --input "$OUTPUT_DIR/host.json" \
  --output "$OUTPUT_DIR/qualification.md" || report_status=$?
report_status="${report_status:-0}"

if [[ -n "${GATEWAY_TOKEN:-}" ]]; then
  python -m grok_model_router.qualification.cli probe \
    --token-env GATEWAY_TOKEN \
    --output "$OUTPUT_DIR/catalog.json" || probe_status=$?
  probe_status="${probe_status:-0}"
else
  probe_status=0
  printf '%s\n' 'GATEWAY_TOKEN is unset; skipped the optional loopback roster probe.' > "$OUTPUT_DIR/catalog-skipped.txt"
fi

printf 'Qualification files written to %s (no host file changed; no chat prompt sent).\n' "$OUTPUT_DIR"
exit "$(( scan_status > report_status ? scan_status : report_status ))"
