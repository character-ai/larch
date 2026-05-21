#!/usr/bin/env bash
# audit-resolve-prs.sh — Resolve verbal description to a concrete PR list.
#
# Handles all supported forms:
#   empty / omitted  → since last audit (implicit)
#   since last audit → read most-recent audit-report, parse frontmatter, list PRs after
#   last N PRs       → N most-recently-merged PRs
#   since <ISO>      → PRs merged after that instant
#   #N / PR #N       → exactly one PR
#
# Output KV (stdout):
#   IMPLICIT_SINCE_LAST_AUDIT=true|false
#   PRIOR_REPORT_NUMBER=<N or empty>
#   PR_LIST=N,M,...      (comma-separated, empty on error)
#   PR_COUNT=<N>
#   RESOLVED_ECHO=<human-readable line>
#   ERROR=<empty when ok; human-readable error when PR_LIST is empty>
#
# Exit codes: 0 always; caller reads PR_LIST / ERROR.

set -euo pipefail

REPO="character-ai/larch"
VERBAL=""

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO="$2"; shift 2 ;;
        --verbal-description) VERBAL="$2"; shift 2 ;;
        *) shift ;;
    esac
done

# Trim whitespace
VERBAL=$(printf '%s' "$VERBAL" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

emit_error() {
    printf 'IMPLICIT_SINCE_LAST_AUDIT=false\nPRIOR_REPORT_NUMBER=\nPR_LIST=\nPR_COUNT=0\nRESOLVED_ECHO=\nERROR=%s\n' "$1"
    exit 0
}

emit_ok() {
    local implicit="$1" prior="$2" pr_list="$3" pr_count="$4" echo_line="$5"
    printf 'IMPLICIT_SINCE_LAST_AUDIT=%s\nPRIOR_REPORT_NUMBER=%s\nPR_LIST=%s\nPR_COUNT=%s\nRESOLVED_ECHO=%s\nERROR=\n' \
        "$implicit" "$prior" "$pr_list" "$pr_count" "$echo_line"
    exit 0
}

# ---- "since last audit" helper ----
resolve_since_last_audit() {
    local implicit="$1"

    # Read most-recent audit-report issue
    PRIOR_BODY=$(gh issue list --state all --label audit-report --repo "$REPO" \
        --json number,title,body,createdAt \
        --jq 'sort_by(.createdAt) | reverse | .[0]' 2>/dev/null || true)

    if [ -z "$PRIOR_BODY" ] || [ "$PRIOR_BODY" = "null" ]; then
        emit_error "no prior audit-report issue found"
    fi

    PRIOR_NUM=$(printf '%s' "$PRIOR_BODY" | jq -r '.number // empty' 2>/dev/null || true)
    PRIOR_ISSUE_BODY=$(printf '%s' "$PRIOR_BODY" | jq -r '.body // empty' 2>/dev/null || true)

    # Parse audited_pr_range.last from YAML frontmatter (between --- markers)
    LAST_PR=$(printf '%s' "$PRIOR_ISSUE_BODY" \
        | awk '/^---$/{f=!f;next} f && /audited_pr_range:/{in_range=1} in_range && /[[:space:]]last:/{gsub(/.*last:[[:space:]]*/,""); print; exit}')

    if [ -z "$LAST_PR" ]; then
        emit_error "prior audit-report #${PRIOR_NUM} has malformed or missing frontmatter (audited_pr_range.last)"
    fi

    # Get mergedAt for LAST_PR
    MERGED_AT=$(gh pr view "$LAST_PR" --repo "$REPO" --json mergedAt --jq '.mergedAt // empty' 2>/dev/null || true)
    if [ -z "$MERGED_AT" ]; then
        emit_error "could not get mergedAt for prior PR #${LAST_PR}"
    fi

    # List PRs merged after MERGED_AT
    PR_JSON=$(gh pr list --repo "$REPO" --state merged --base main \
        --json number,mergedAt \
        --jq "[.[] | select(.mergedAt > \"$MERGED_AT\")] | sort_by(.mergedAt) | [.[].number]" \
        2>/dev/null || true)

    if [ -z "$PR_JSON" ] || [ "$PR_JSON" = "[]" ]; then
        emit_error "no new PRs merged after prior audit (last PR: #${LAST_PR})"
    fi

    PR_LIST=$(printf '%s' "$PR_JSON" | jq -r 'join(",")' 2>/dev/null || true)
    PR_COUNT=$(printf '%s' "$PR_JSON" | jq 'length' 2>/dev/null || echo 0)

    if [ "$implicit" = "true" ]; then
        ECHO_LINE="Resolved since last audit (implicit default: empty/omitted positional) to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    else
        ECHO_LINE="Resolved since last audit to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    fi

    emit_ok "$implicit" "$PRIOR_NUM" "$PR_LIST" "$PR_COUNT" "$ECHO_LINE"
}

# ---- Dispatch on form ----
if [ -z "$VERBAL" ]; then
    resolve_since_last_audit "true"
fi

if [ "$VERBAL" = "since last audit" ]; then
    resolve_since_last_audit "false"
fi

# "last N PRs"
if printf '%s' "$VERBAL" | grep -qE '^last[[:space:]]+[0-9]+[[:space:]]+PRs?$'; then
    N=$(printf '%s' "$VERBAL" | grep -oE '[0-9]+')
    PR_JSON=$(gh pr list --repo "$REPO" --state merged --base main \
        --json number --limit "$N" \
        --jq '[.[].number]' 2>/dev/null || true)
    PR_LIST=$(printf '%s' "$PR_JSON" | jq -r 'join(",")' 2>/dev/null || true)
    PR_COUNT=$(printf '%s' "$PR_JSON" | jq 'length' 2>/dev/null || echo 0)
    ECHO_LINE="Resolved last $N PRs to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    emit_ok "false" "" "$PR_LIST" "$PR_COUNT" "$ECHO_LINE"
fi

# "since <ISO>"
if printf '%s' "$VERBAL" | grep -qE '^since[[:space:]]+[0-9]{4}-[0-9]{2}-[0-9]{2}'; then
    TS=$(printf '%s' "$VERBAL" | sed 's/^since[[:space:]]*//')
    PR_JSON=$(gh pr list --repo "$REPO" --state merged --base main \
        --json number,mergedAt \
        --jq "[.[] | select(.mergedAt > \"$TS\")] | sort_by(.mergedAt) | [.[].number]" \
        2>/dev/null || true)
    PR_LIST=$(printf '%s' "$PR_JSON" | jq -r 'join(",")' 2>/dev/null || true)
    PR_COUNT=$(printf '%s' "$PR_JSON" | jq 'length' 2>/dev/null || echo 0)
    ECHO_LINE="Resolved since $TS to: [$(printf '%s' "$PR_JSON" | jq -r '[.[] | "#\(.)"] | join(", ")')]. Proceeding."
    emit_ok "false" "" "$PR_LIST" "$PR_COUNT" "$ECHO_LINE"
fi

# "#N" or "PR #N"
if printf '%s' "$VERBAL" | grep -qE '^(PR[[:space:]]+)?#[0-9]+$'; then
    N=$(printf '%s' "$VERBAL" | grep -oE '[0-9]+$')
    emit_ok "false" "" "$N" "1" "Resolved $VERBAL to: [#${N}]. Proceeding."
fi

emit_error "unrecognized verbal description: $VERBAL"
