#!/usr/bin/env bash
# read-workflow-path.sh - Resolve workflow path from timing/report artifacts.

set -euo pipefail

warn_unknown() {
    printf '%s\n' "**⚠ read-workflow-path: $1; defaulting to unknown**" >&2
    printf '%s\n' unknown
}

f="${1:-}"
if [[ -z "$f" ]]; then
    warn_unknown "artifact path not provided"
    exit 0
fi
if [[ ! -r "$f" ]]; then
    warn_unknown "artifact not readable: $f"
    exit 0
fi

if command -v python3 >/dev/null 2>&1; then
    _out=$(python3 - "$f" <<'PY' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    raise SystemExit(1)
workflow = data.get("workflow_path")
if workflow in ("SIMPLE", "HARD"):
    print(workflow)
    raise SystemExit(0)
classification = data.get("design_classification")
if classification in ("SIMPLE", "HARD"):
    print(classification)
    raise SystemExit(0)
raise SystemExit(1)
PY
)
    case "$_out" in SIMPLE|HARD) printf '%s\n' "$_out"; exit 0 ;; esac
fi

if command -v jq >/dev/null 2>&1; then
    _out=$(jq -r '
      if .workflow_path=="SIMPLE" or .workflow_path=="HARD" then .workflow_path
      elif .design_classification=="SIMPLE" or .design_classification=="HARD" then .design_classification
      else empty end
    ' "$f" 2>/dev/null || true)
    case "$_out" in SIMPLE|HARD) printf '%s\n' "$_out"; exit 0 ;; esac
fi

if [[ -x "$(dirname "$0")/read-design-classification.sh" ]]; then
    _out=$("$(dirname "$0")/read-design-classification.sh" "$f" 2>/dev/null || true)
    case "$_out" in SIMPLE|HARD) printf '%s\n' "$_out"; exit 0 ;; esac
fi

warn_unknown "workflow_path/design_classification missing or invalid"
