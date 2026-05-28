#!/usr/bin/env bash
# audit-close-priors.sh — Close prior open audit-report issues for this skill.
#
# Finds open audit-report issues whose titles match --skill, except --new-issue-number,
# posts "Superseded by #N", then closes each.
#
# Output: per-issue KV lines to stdout:
#   CLOSED_NUMBER=<N>
# Plus error lines on failure (TAB separates issue number from REASON on the same line):
#   CLOSE_FAILED=<N><TAB>REASON=<msg>
#
# Usage:
#   audit-close-priors.sh --skill <design|implement> --new-issue-number N --repo OWNER/NAME

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# shellcheck source=scripts/lib-net.sh
source "$PLUGIN_ROOT/scripts/lib-net.sh"
# shellcheck source=.claude/skills/audit-runs/scripts/audit-title-matcher.sh
. "$SCRIPT_DIR/audit-title-matcher.sh"

NEW_ISSUE=""
REPO="character-ai/larch"
SKILL=""

audit_close_validate_skill() {
    case "${1:-}" in
        design|implement) return 0 ;;
        "")
            printf 'audit-close-priors.sh: --skill is required (allowed: design, implement)\n' >&2
            return 1
            ;;
        *)
            printf 'audit-close-priors.sh: --skill must be design or implement (got: %s)\n' "$1" >&2
            return 1
            ;;
    esac
}

while [ $# -gt 0 ]; do
    case "$1" in
        --new-issue-number) NEW_ISSUE="$2"; shift 2 ;;
        --repo) REPO="$2"; shift 2 ;;
        --skill) SKILL="$2"; shift 2 ;;
        *)
            printf 'audit-close-priors.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if ! audit_close_validate_skill "$SKILL"; then
    exit 1
fi

if [ -z "$NEW_ISSUE" ]; then
    printf 'audit-close-priors.sh: --new-issue-number is required\n' >&2
    exit 1
fi

if ! OPEN_ISSUES_JSON=$(gh issue list --state open --limit 100000 --label audit-report --repo "$REPO" \
    --json number,title 2>/dev/null); then
    printf 'ISSUE_LIST_FAILED=true\nREASON=gh issue list failed\n'
    exit 1
fi

if ! printf '%s' "$OPEN_ISSUES_JSON" | jq -e 'if type == "array" then . else error("not-array") end' >/dev/null 2>&1; then
    printf 'ISSUE_LIST_FAILED=true\nREASON=gh issue list returned invalid JSON\n'
    exit 1
fi

OPEN_ISSUES=""
while IFS= read -r row; do
    [ -z "$row" ] && continue
    num=$(printf '%s' "$row" | jq -r '.number // empty' 2>/dev/null || true)
    title=$(printf '%s' "$row" | jq -r '.title // empty' 2>/dev/null || true)
    [ -z "$num" ] && continue
    if match_audit_report_title --skill "$SKILL" --title "$title"; then
        OPEN_ISSUES="${OPEN_ISSUES}${num}"$'\n'
    fi
done < <(printf '%s' "$OPEN_ISSUES_JSON" | jq -c '.[]')

if [ -z "$OPEN_ISSUES" ]; then
    exit 0
fi

SUPERSEDE_BODY=$(mktemp "${TMPDIR:-/tmp}/larch-audit-superseded.XXXXXX") || {
    printf 'BODY_FILE_FAILED=true\nREASON=mktemp failed\n'
    exit 1
}
trap 'rm -f "$SUPERSEDE_BODY"' EXIT
printf 'Superseded by #%s' "$NEW_ISSUE" >"$SUPERSEDE_BODY"

while IFS= read -r issue_num; do
    [ -z "$issue_num" ] && continue
    if [ "$issue_num" = "$NEW_ISSUE" ]; then
        continue
    fi

    comment_fail_file=$(mktemp "${TMPDIR:-/tmp}/audit-close-comment.XXXXXX")
    if with_transient_retry transient_envelope_predicate_none "$comment_fail_file" \
        gh issue comment "$issue_num" --repo "$REPO" --body-file "$SUPERSEDE_BODY"; then
        rm -f "$comment_fail_file"
        close_fail_file=$(mktemp "${TMPDIR:-/tmp}/audit-close-close.XXXXXX")
        if with_transient_retry transient_envelope_predicate_none "$close_fail_file" \
            gh issue close "$issue_num" --repo "$REPO"; then
            rm -f "$close_fail_file"
            printf 'CLOSED_NUMBER=%s\n' "$issue_num"
        else
            rm -f "$close_fail_file"
            printf 'CLOSE_FAILED=%s\tREASON=gh issue close failed\n' "$issue_num"
        fi
    else
        rm -f "$comment_fail_file"
        printf 'CLOSE_FAILED=%s\tREASON=gh issue comment failed\n' "$issue_num"
    fi
done <<EOF
$OPEN_ISSUES
EOF
