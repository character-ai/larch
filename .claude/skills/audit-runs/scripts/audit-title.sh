#!/usr/bin/env bash
# audit-title.sh — Generate audit report title string.
#
# Title rules:
#   Contiguous range:      [<prefix> <ts> Report] PRs #X-#Y
#   Non-contiguous <= 4:   [<prefix> <ts> Report] PRs #X, #Y, #Z
#   Non-contiguous > 4:    [<prefix> <ts> Report] PRs #X, #Y, #Z, #A, #B, ...
#
# Output KV (stdout):
#   TITLE=[... Report] PRs ...
#
# Usage:
#   audit-title.sh --skill <design|implement> --pr-list N,M,... --timestamp STR

set -euo pipefail

PR_LIST=""
TIMESTAMP=""
SKILL=""

audit_title_validate_skill() {
    case "${1:-}" in
        design|implement) return 0 ;;
        "")
            printf 'audit-title.sh: --skill is required (allowed: design, implement)\n' >&2
            return 1
            ;;
        *)
            printf 'audit-title.sh: --skill must be design or implement (got: %s)\n' "$1" >&2
            return 1
            ;;
    esac
}

while [ $# -gt 0 ]; do
    case "$1" in
        --pr-list) PR_LIST="$2"; shift 2 ;;
        --timestamp) TIMESTAMP="$2"; shift 2 ;;
        --skill) SKILL="$2"; shift 2 ;;
        *)
            printf 'audit-title.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if ! audit_title_validate_skill "$SKILL"; then
    exit 1
fi

if [ -z "$PR_LIST" ] || [ -z "$TIMESTAMP" ]; then
    printf 'audit-title.sh: --pr-list and --timestamp are required\n' >&2
    exit 1
fi

case "$SKILL" in
    implement) TITLE_PREFIX="Implement Run Logs Audit" ;;
    design) TITLE_PREFIX="Design Run Logs Audit" ;;
esac

# Parse comma-separated PR list into sorted unique integers (trim per token; never merge digits across separators)
SORTED_PRS=$(
    printf '%s' "$PR_LIST" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -E '^[0-9]+$' | sort -n -u
)
PR_COUNT=$(printf '%s' "$SORTED_PRS" | awk 'NF { c++ } END { print c + 0 }')

if [ "$PR_COUNT" -eq 0 ]; then
    printf 'audit-title.sh: --pr-list contains no valid PR numbers\n' >&2
    exit 1
fi

if [ "$PR_COUNT" -eq 1 ]; then
    ONLY=$(printf '%s' "$SORTED_PRS" | head -1)
    printf 'TITLE=[%s %s Report] PRs #%d\n' "$TITLE_PREFIX" "$TIMESTAMP" "$((10#$ONLY))"
    exit 0
fi

FIRST=$(printf '%s' "$SORTED_PRS" | head -1)
LAST=$(printf '%s' "$SORTED_PRS" | tail -1)

# Check if contiguous: last - first + 1 == count (force decimal radix for leading-zero tokens)
EXPECTED_COUNT=$(( 10#$LAST - 10#$FIRST + 1 ))
if [ "$EXPECTED_COUNT" -eq "$PR_COUNT" ]; then
    printf 'TITLE=[%s %s Report] PRs #%d-#%d\n' "$TITLE_PREFIX" "$TIMESTAMP" "$((10#$FIRST))" "$((10#$LAST))"
    exit 0
fi

# Non-contiguous: build explicit list (canonical decimal form, no leading zeros)
PR_REFS=$(printf '%s\n' "$SORTED_PRS" | while IFS= read -r n || [ -n "$n" ]; do
    [ -z "$n" ] && continue
    printf '#%d ' "$((10#$n))"
done | sed 's/  */ /g; s/ $//; s/ /, /g')

printf 'TITLE=[%s %s Report] PRs %s\n' "$TITLE_PREFIX" "$TIMESTAMP" "$PR_REFS"
