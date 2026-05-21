#!/usr/bin/env bash
# audit-close-priors.sh — Close prior open audit-report issues.
#
# Finds all open issues with label audit-report except --new-issue-number,
# posts "Superseded by #N", then closes each. Idempotent (skips already-closed).
#
# Output: per-issue KV lines to stdout:
#   CLOSED_NUMBER=<N>
# Plus error lines on failure:
#   CLOSE_FAILED=<N>  REASON=<msg>
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
        *) shift ;;
    esac
done

if [ -z "$NEW_ISSUE" ]; then
    printf 'audit-close-priors.sh: --new-issue-number is required\n' >&2
    exit 1
fi

# List open audit-report issues
OPEN_ISSUES=$(gh issue list --state open --label audit-report --repo "$REPO" \
    --json number --jq '.[].number' 2>/dev/null || true)

if [ -z "$OPEN_ISSUES" ]; then
    exit 0
fi

while IFS= read -r issue_num; do
    [ -z "$issue_num" ] && continue
    # Skip the just-filed report
    if [ "$issue_num" = "$NEW_ISSUE" ]; then
        continue
    fi

    # Post superseded comment
    if gh issue comment "$issue_num" --repo "$REPO" --body "Superseded by #${NEW_ISSUE}" 2>/dev/null; then
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
