#!/usr/bin/env bash
# verify-run-log-completeness.sh — Check a committed run dir against the required-file manifest.
# Emits OK or MISSING=<comma-separated list of missing relative paths>.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
MANIFEST="$REPO_ROOT/docs/run-logs-required-files.tsv"

usage() {
    printf 'Usage: verify-run-log-completeness.sh <larch-logs/implement/RUN_ID/>\n' >&2
    exit 1
}

[ $# -eq 1 ] || usage
RUN_DIR="$1"

[ -f "$MANIFEST" ] || { printf 'verify-run-log-completeness.sh: manifest not found: %s\n' "$MANIFEST" >&2; exit 1; }
[ -d "$RUN_DIR" ] || { printf 'verify-run-log-completeness.sh: run dir not found: %s\n' "$RUN_DIR" >&2; exit 1; }

missing=""

while IFS='	' read -r relative_path condition _rest; do
    # skip header
    [ "$relative_path" = "relative_path" ] && continue
    # skip blank or comment lines
    [ -n "$relative_path" ] || continue
    case "$relative_path" in '#'*) continue ;; esac

    # only check "always" required files for now
    [ "$condition" = "always" ] || continue

    if [ ! -f "$RUN_DIR/$relative_path" ]; then
        if [ -n "$missing" ]; then
            missing="$missing,$relative_path"
        else
            missing="$relative_path"
        fi
    fi
done < "$MANIFEST"

if [ -n "$missing" ]; then
    printf 'MISSING=%s\n' "$missing"
    exit 1
fi

printf 'OK\n'
