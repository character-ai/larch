#!/usr/bin/env bash
# persist-implement-run-flags.sh — Write $IMPLEMENT_TMPDIR/run-flags.sh (KV) atomically.
#
# Sanctioned writer for QUICK_MODE, NO_ISSUES, WORKFLOW_PATH used by
# write-final-report.sh. Do not compose this file from prompt-side shell.
#
# Usage:
#   persist-implement-run-flags.sh --implement-tmpdir PATH \
#       [--quick-mode true|false] --no-issues true|false --workflow-path SIMPLE|HARD|N/A
#
# When --quick-mode is omitted, QUICK_MODE=false is written (quick mode was removed from /implement).
#
# Exit 2 on validation failure.

set -euo pipefail

fail() { printf 'persist-implement-run-flags.sh: %s\n' "$1" >&2; exit 2; }

IMPLEMENT_TMPDIR=""
QUICK_MODE=""
NO_ISSUES=""
WORKFLOW_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail "--implement-tmpdir requires a value"
            IMPLEMENT_TMPDIR="$2"
            shift 2
            ;;
        --quick-mode)
            [[ $# -ge 2 ]] || fail "--quick-mode requires a value"
            QUICK_MODE="$2"
            shift 2
            ;;
        --no-issues)
            [[ $# -ge 2 ]] || fail "--no-issues requires a value"
            NO_ISSUES="$2"
            shift 2
            ;;
        --workflow-path)
            [[ $# -ge 2 ]] || fail "--workflow-path requires a value"
            WORKFLOW_PATH="$2"
            shift 2
            ;;
        *) fail "unknown option: $1" ;;
    esac
done

[[ -n "$IMPLEMENT_TMPDIR" ]] || fail "--implement-tmpdir is required"
[[ -d "$IMPLEMENT_TMPDIR" ]] || fail "--implement-tmpdir not a directory"
[[ -n "$QUICK_MODE" ]] || QUICK_MODE="false"
case "$QUICK_MODE" in true|false) ;; *) fail "--quick-mode must be true or false" ;; esac
case "$NO_ISSUES" in true|false) ;; *) fail "--no-issues must be true or false" ;; esac
case "$WORKFLOW_PATH" in SIMPLE|HARD|N/A) ;; *) fail "--workflow-path must be SIMPLE, HARD, or N/A" ;; esac

out="$IMPLEMENT_TMPDIR/run-flags.sh"
tmp="$(mktemp "${out}.tmp.XXXXXX")"
cleanup() { rm -f "$tmp"; }
trap cleanup EXIT

{
    printf 'QUICK_MODE=%s\n' "$QUICK_MODE"
    printf 'NO_ISSUES=%s\n' "$NO_ISSUES"
    printf 'WORKFLOW_PATH=%s\n' "$WORKFLOW_PATH"
} > "$tmp"

mv "$tmp" "$out"
trap - EXIT

printf 'RUN_FLAGS_PERSISTED=true\n'
