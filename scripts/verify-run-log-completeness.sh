#!/usr/bin/env bash
# verify-run-log-completeness.sh — Check a committed run dir against the required-file manifest.
# Emits OK or MISSING=<comma-separated list of missing relative paths>.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
if [[ -n "${LARCH_VERIFY_MANIFEST:-}" ]]; then
    if [[ "$LARCH_VERIFY_MANIFEST" = /* ]]; then
        MANIFEST="$LARCH_VERIFY_MANIFEST"
    else
        # Relative paths resolve from repository root, not the process cwd.
        _rel="${LARCH_VERIFY_MANIFEST#./}"
        MANIFEST="$REPO_ROOT/$_rel"
        while [[ "$MANIFEST" == *//* ]]; do
            MANIFEST="${MANIFEST//\/\//\/}"
        done
    fi
else
    MANIFEST="$REPO_ROOT/docs/run-logs-required-files.tsv"
fi

usage() {
    printf 'Usage: verify-run-log-completeness.sh <larch-logs/implement/RUN_ID/>\n' >&2
    exit 1
}

manifest_field() {
    python3 - "$RUN_DIR/manifest.json" "$1" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        data = json.load(fh)
except Exception:
    sys.exit(0)

key = sys.argv[2]
value = data.get(key)

if key == "pr_number":
    if isinstance(value, bool):
        sys.exit(0)
    if isinstance(value, int):
        print(value)
    elif isinstance(value, str) and value.strip():
        print(value)
elif key == "status":
    if isinstance(value, str):
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
        exn-agg-validate-fail)
            [ -f "$RUN_DIR/execution-issues.ndjson" ] &&
                grep -Fq 'merged output failed validation' "$RUN_DIR/execution-issues.ndjson" 2>/dev/null
            ;;
        exn-agg-dispatch-fail)
            [ -f "$RUN_DIR/execution-issues.ndjson" ] && {
                grep -Fq 'dispatch-with-waterfall exited non-zero' "$RUN_DIR/execution-issues.ndjson" 2>/dev/null ||
                    grep -Fq 'DISPATCH_OK=false' "$RUN_DIR/execution-issues.ndjson" 2>/dev/null
            }
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

MANIFEST_STATUS="$(manifest_field status)"
MANIFEST_PR_NUMBER="$(manifest_field pr_number)"

missing=""

while IFS='	' read -r relative_path condition _rest; do
    # skip header
    [ "$relative_path" = "relative_path" ] && continue
    # skip blank or comment lines
    [ -n "$relative_path" ] || continue
    case "$relative_path" in '#'*) continue ;; esac

    condition_reached "$condition" || continue

    case "$relative_path" in
        *..*)
            printf 'verify-run-log-completeness.sh: invalid relative_path (..): %s\n' "$relative_path" >&2
            exit 1
            ;;
    esac

    if ! printf '%s' "$relative_path" | LC_ALL=C grep -qE '^[A-Za-z0-9_./*-]+$'; then
        printf 'verify-run-log-completeness.sh: invalid characters in relative_path: %s\n' "$relative_path" >&2
        exit 1
    fi

    if printf '%s' "$relative_path" | grep -q '\*'; then
        found_glob=0
        shopt -s nullglob
        for _gf in "$RUN_DIR"/$relative_path; do
            if [ -f "$_gf" ]; then
                found_glob=1
                break
            fi
        done
        shopt -u nullglob
        if [ "$found_glob" -eq 0 ]; then
            if [ -n "$missing" ]; then
                missing="$missing,$relative_path"
            else
                missing="$relative_path"
            fi
        fi
    elif [ ! -f "$RUN_DIR/$relative_path" ]; then
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
