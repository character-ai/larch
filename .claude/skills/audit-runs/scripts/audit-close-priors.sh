#!/usr/bin/env bash
# audit-close-priors.sh — Close prior open audit-report issues.
#
# Finds all open issues with label audit-report except --new-issue-number,
# posts "Superseded by #N", then closes each. Idempotent (skips already-closed).
#
# Output: per-issue KV lines to stdout:
#   CLOSED_NUMBER=<N>
# Plus error lines on failure (TAB separates issue number from REASON on the same line):
#   CLOSE_FAILED=<N><TAB>REASON=<msg>
#
# Usage:
#   audit-close-priors.sh --new-issue-number N --repo OWNER/NAME

set -euo pipefail

NEW_ISSUE=""
REPO="character-ai/larch"

while [ $# -gt 0 ]; do
    case "$1" in
        --new-issue-number) NEW_ISSUE="$2"; shift 2 ;;
        --repo) REPO="$2"; shift 2 ;;
        *)
            printf 'audit-close-priors.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if [ -z "$NEW_ISSUE" ]; then
    printf 'audit-close-priors.sh: --new-issue-number is required\n' >&2
    exit 1
fi

# List open audit-report issues
if ! OPEN_ISSUES=$(gh issue list --state open --label audit-report --repo "$REPO" \
    --json number --jq '.[].number' 2>/dev/null); then
    printf 'ISSUE_LIST_FAILED=true\nREASON=gh issue list failed\n'
    exit 1
fi

if [ -z "$OPEN_ISSUES" ]; then
    exit 0
fi

SUPERSEDE_BODY=$(mktemp "${TMPDIR:-/tmp}/larch-audit-superseded.XXXXXX")
trap 'rm -f "$SUPERSEDE_BODY"' EXIT
printf 'Superseded by #%s' "$NEW_ISSUE" >"$SUPERSEDE_BODY"

while IFS= read -r issue_num; do
    [ -z "$issue_num" ] && continue
    # Skip the just-filed report
    if [ "$issue_num" = "$NEW_ISSUE" ]; then
        continue
    fi

    # Post superseded comment
    if gh issue comment "$issue_num" --repo "$REPO" --body-file "$SUPERSEDE_BODY" 2>/dev/null; then
        # Close the issue
        if gh issue close "$issue_num" --repo "$REPO" 2>/dev/null; then
            printf 'CLOSED_NUMBER=%s\n' "$issue_num"
        else
            printf 'CLOSE_FAILED=%s\tREASON=gh issue close failed\n' "$issue_num"
        fi
    else
        printf 'CLOSE_FAILED=%s\tREASON=gh issue comment failed\n' "$issue_num"
    fi
done <<EOF
$OPEN_ISSUES
EOF
