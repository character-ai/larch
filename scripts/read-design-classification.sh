#!/usr/bin/env bash
# read-design-classification.sh - Resolve /design classification from run-params.json.

set -euo pipefail

warn_default() {
    printf '%s\n' "**⚠ read-design-classification: $1; defaulting to HARD**" >&2
    printf '%s\n' HARD
}

f="${1:-${DESIGN_TMPDIR:-}/run-params.json}"
if [[ -z "$f" ]]; then
    warn_default "run-params path not provided"
    exit 0
fi
if [[ ! -r "$f" ]]; then
    warn_default "run-params not readable: $f"
    exit 0
fi

if command -v python3 >/dev/null 2>&1; then
    _out=$(python3 - "$f" <<'PY' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        v = json.load(fh).get("design_classification")
except Exception:
    raise SystemExit(1)
if v in ("SIMPLE", "HARD"):
    print(v)
else:
    raise SystemExit(1)
PY
)
    case "$_out" in SIMPLE|HARD) printf '%s\n' "$_out"; exit 0 ;; esac
fi

if command -v jq >/dev/null 2>&1; then
    _out=$(jq -r 'if .design_classification=="SIMPLE" or .design_classification=="HARD" then .design_classification else empty end' "$f" 2>/dev/null || true)
    case "$_out" in SIMPLE|HARD) printf '%s\n' "$_out"; exit 0 ;; esac
fi

if grep -qE '"design_classification"[[:space:]]*:[[:space:]]*"SIMPLE"' "$f" 2>/dev/null; then
    printf '%s\n' SIMPLE
    exit 0
fi
if grep -qE '"design_classification"[[:space:]]*:[[:space:]]*"HARD"' "$f" 2>/dev/null; then
    printf '%s\n' HARD
    exit 0
fi

warn_default "design_classification missing or invalid"
