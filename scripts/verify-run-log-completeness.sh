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
        case "$_rel" in
            *..*)
                printf 'verify-run-log-completeness.sh: LARCH_VERIFY_MANIFEST relative path must not contain .. segments\n' >&2
                exit 1
                ;;
        esac
        MANIFEST="$REPO_ROOT/$_rel"
        while [[ "$MANIFEST" == *//* ]]; do
            MANIFEST="${MANIFEST//\/\//\/}"
        done
        case "$MANIFEST" in
            "$REPO_ROOT"/*) ;;
            *)
                printf 'verify-run-log-completeness.sh: LARCH_VERIFY_MANIFEST resolves outside repository root\n' >&2
                exit 1
                ;;
        esac
        if [[ -d "$(dirname "$MANIFEST")" ]]; then
            _manifest_dir="$(cd "$(dirname "$MANIFEST")" && pwd -P)"
            MANIFEST="$_manifest_dir/$(basename "$MANIFEST")"
            case "$MANIFEST" in
                "$REPO_ROOT"/*) ;;
                *)
                    printf 'verify-run-log-completeness.sh: LARCH_VERIFY_MANIFEST resolves outside repository root\n' >&2
                    exit 1
                    ;;
            esac
        fi
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

# True when manifest records an explicit Step 9a.1 skip (matches audit-scan-run
# required-file-presence gate: only explicit false suppresses step9a1 rows).
manifest_step9a1_explicitly_skipped() {
    python3 - "$RUN_DIR/manifest.json" <<'PY'
import json
import sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    sr = data.get("steps_ran") or {}
    if isinstance(sr, dict) and sr.get("step9a1") is False:
        sys.exit(0)
except Exception:
    pass
sys.exit(1)
PY
}

# True when steps_ran is absent or an empty object (matches audit-scan-run bail fallback).
manifest_steps_ran_empty() {
    python3 - "$RUN_DIR/manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    sr = data.get("steps_ran")
    if not isinstance(sr, dict):
        sys.exit(1)
    sys.exit(0 if len(sr) == 0 else 1)
except Exception:
    sys.exit(1)
PY
}

# First non-empty line of final-summary.md ends with bailed / bailed-needs-user-input.
final_summary_heading_bail_signal() {
    python3 - "$RUN_DIR/final-summary.md" <<'PY'
import re
import sys

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip():
                if re.search(r"bailed(-needs-user-input)?$", line.rstrip("\r\n")):
                    sys.exit(0)
                break
except Exception:
    pass
sys.exit(1)
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
            if manifest_steps_ran_empty && final_summary_heading_bail_signal &&
                ! {
                    has_file token-report.json || has_file timing-report.json ||
                        has_file execution-issues.ndjson || has_file session-transcript.jsonl
                }; then
                return 1
            fi
            has_file token-report.json ||
                has_file timing-report.json ||
                has_file execution-issues.ndjson ||
                has_file session-transcript.jsonl ||
                condition_reached step8
            ;;
        step8)
            if manifest_steps_ran_empty && final_summary_heading_bail_signal &&
                ! { has_file version-bump-reasoning.md || has_file final-summary.md; }; then
                return 1
            fi
            has_file version-bump-reasoning.md ||
                has_file final-summary.md ||
                [ -n "$MANIFEST_PR_NUMBER" ] ||
                condition_reached step9a1
            ;;
        step9a1)
            if manifest_step9a1_explicitly_skipped; then
                return 1
            fi
            if manifest_steps_ran_empty && final_summary_heading_bail_signal &&
                ! { has_file run-statistics.md || has_file oos-issues.ndjson; }; then
                return 1
            fi
            has_file run-statistics.md ||
                has_file oos-issues.ndjson ||
                [ -n "$MANIFEST_PR_NUMBER" ] ||
                [ "$MANIFEST_STATUS" = "done" ] ||
                has_file final-summary.md
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
        _star_count="${relative_path//[^*]/}"
        if [ "${#_star_count}" -gt 1 ]; then
            printf 'verify-run-log-completeness.sh: relative_path must contain at most one * wildcard: %s\n' "$relative_path" >&2
            exit 1
        fi
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
