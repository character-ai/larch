#!/usr/bin/env bash
# check-recovery-paths-in-plan-scope.sh — Fail closed when recovery paths leave plan scope.

set -euo pipefail

usage() {
    echo "Usage: check-recovery-paths-in-plan-scope.sh --plan-file PATH --paths-file PATH" >&2
}

PLAN_FILE=""
PATHS_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --paths-file) PATHS_FILE="${2:?--paths-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "check-recovery-paths-in-plan-scope.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$PLAN_FILE" || -z "$PATHS_FILE" ]]; then
    usage
    exit 2
fi
if [[ ! -f "$PLAN_FILE" ]]; then
    echo "check-recovery-paths-in-plan-scope.sh: plan file not found: $PLAN_FILE" >&2
    exit 2
fi
if [[ ! -f "$PATHS_FILE" ]]; then
    echo "check-recovery-paths-in-plan-scope.sh: recovery paths file not found: $PATHS_FILE" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN_SCOPE_FILE=$(mktemp)
trap 'rm -f "$PLAN_SCOPE_FILE"' EXIT
"$SCRIPT_DIR/extract-plan-scope-paths.sh" --plan-file "$PLAN_FILE" -z > "$PLAN_SCOPE_FILE"

python3 - "$PLAN_SCOPE_FILE" "$PATHS_FILE" <<'PY'
import sys

scope_file, paths_file = sys.argv[1:3]
scope = {p.decode("utf-8", "surrogateescape") for p in open(scope_file, "rb").read().split(b"\0") if p}
paths = [p.decode("utf-8", "surrogateescape") for p in open(paths_file, "rb").read().split(b"\0") if p]
oos = [p for p in paths if p not in scope]
if oos:
    for rel in oos:
        print(rel, file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PY
