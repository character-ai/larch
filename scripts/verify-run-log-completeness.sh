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

manifest_pr_number() {
    python3 - "$RUN_DIR/manifest.json" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

value = data.get("pr_number")
if isinstance(value, int):
    print(value)
PY
}

has_file() {
    [ -f "$RUN_DIR/$1" ]
}

condition_reached() {
    local condition="$1"
    case "$condition" in
        always)
            return 0
            ;;
        step5)
            has_file code-review-tally.json ||
                has_file review-findings-full.jsonl ||
                condition_reached step7a
            ;;
        step7a)
            has_file token-report.json ||
                has_file timing-report.json ||
                has_file execution-issues.ndjson ||
                has_file session-transcript.jsonl ||
                condition_reached step8
            ;;
        step8)
            has_file version-bump-reasoning.md ||
                has_file final-summary.md ||
                [ -n "$MANIFEST_PR_NUMBER" ] ||
                condition_reached step9a1
            ;;
        step9a1)
            has_file run-statistics.md ||
                has_file oos-issues.ndjson ||
                [ -n "$MANIFEST_PR_NUMBER" ] ||
                [ "$MANIFEST_STATUS" = "done" ]
            ;;
        *)
            printf 'verify-run-log-completeness.sh: unsupported manifest condition: %s\n' "$condition" >&2
            exit 1
            ;;
    esac
}

[ $# -eq 1 ] || usage
RUN_DIR="$1"

[ -f "$MANIFEST" ] || { printf 'verify-run-log-completeness.sh: manifest not found: %s\n' "$MANIFEST" >&2; exit 1; }
[ -d "$RUN_DIR" ] || { printf 'verify-run-log-completeness.sh: run dir not found: %s\n' "$RUN_DIR" >&2; exit 1; }

MANIFEST_STATUS="$(awk -F'"' '/"status"[[:space:]]*:/ { print $4; exit }' "$RUN_DIR/manifest.json" 2>/dev/null || true)"
MANIFEST_PR_NUMBER="$(manifest_pr_number)"

missing=""

while IFS='	' read -r relative_path condition _rest; do
    # skip header
    [ "$relative_path" = "relative_path" ] && continue
    # skip blank or comment lines
    [ -n "$relative_path" ] || continue
    case "$relative_path" in '#'*) continue ;; esac

    condition_reached "$condition" || continue

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
