#!/usr/bin/env bash
# check-clean-tree.sh — Cleanliness predicate for working-tree gates.
#
# Default behavior is fail-open: a failing `git status --porcelain` is
# reported as clean, preserving preflight.sh's historical behavior. With
# --fail-closed, a failing probe emits CLEAN=unknown and exits 1.
#
# Usage:
#   check-clean-tree.sh [--fail-closed]
#
# Stdout contract:
#   CLEAN=true
#   CLEAN=false
#   DIRTY_OUT=<one-line summary>
#   CLEAN=unknown
#   PROBE_ERROR=<one-line summary>
#
# Exit codes:
#   0 — clean, dirty, or fail-open probe failure
#   1 — --fail-closed probe failure
#   2 — argument validation failed

set -euo pipefail

FAIL_CLOSED=false
while [ $# -gt 0 ]; do
    case "$1" in
        --fail-closed)
            FAIL_CLOSED=true
            shift
            ;;
        *)
            printf 'check-clean-tree.sh: unknown flag: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done

one_line_summary() {
    local summary
    summary=$(tr '\n\r\t' '   ')
    printf '%s' "${summary:0:256}"
}

porcelain_exit=0
porcelain_out=$(git status --porcelain 2>&1) || porcelain_exit=$?

if [ "$porcelain_exit" -ne 0 ]; then
    summary=$(printf '%s' "$porcelain_out" | one_line_summary)
    printf 'check-clean-tree.sh: git status --porcelain failed (exit %s): %s\n' "$porcelain_exit" "$porcelain_out" >&2
    if [ "$FAIL_CLOSED" = "true" ]; then
        printf 'CLEAN=unknown\n'
        printf 'PROBE_ERROR=git exited %s (%s)\n' "$porcelain_exit" "$summary"
        exit 1
    fi
    printf 'CLEAN=true\n'
    exit 0
fi

if [ -n "$porcelain_out" ]; then
    summary=$(printf '%s' "$porcelain_out" | one_line_summary)
    printf 'CLEAN=false\n'
    printf 'DIRTY_OUT=%s\n' "$summary"
    exit 0
fi

printf 'CLEAN=true\n'
