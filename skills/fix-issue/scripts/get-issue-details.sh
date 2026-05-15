#!/usr/bin/env bash
# get-issue-details.sh — Fetch an issue's full details (body + all comments).
#
# Writes a structured text file containing the issue title, body, labels,
# and all comments with author attribution.
#
# Usage:
#   get-issue-details.sh --issue NUMBER --output PATH
#
# Output file format:
#   # Issue #N: <title>
#   **Labels**: <comma-separated, or "none" when no labels>
#   **Created**: <date>
#
#   ## Description
#   <body>
#
#   ## Comments
#   ### Comment by <login> at <date>
#   <body>
#
# Exit codes:
#   0 — success
#   1 — error (missing args, API failure)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"
larch_quiet_init

RESOLVE_REPO="${SCRIPT_DIR}/../../../scripts/resolve-repo.sh"

ISSUE_NUMBER=""
OUTPUT_PATH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --issue) ISSUE_NUMBER="${2:?--issue requires a value}"; shift 2 ;;
        --output) OUTPUT_PATH="${2:?--output requires a value}"; shift 2 ;;
        *) larch_err "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ -z "$ISSUE_NUMBER" ]] || [[ -z "$OUTPUT_PATH" ]]; then
    larch_err "Usage: get-issue-details.sh --issue NUMBER --output PATH"
    exit 1
fi

# Resolve repo identity
REPO=$("$RESOLVE_REPO" 2>/dev/null) || {
    larch_err "ERROR=Failed to resolve repository name"
    exit 1
}

# Fetch issue metadata
ISSUE_JSON=$(gh issue view "$ISSUE_NUMBER" --repo "$REPO" --json title,body,labels,createdAt 2>/dev/null) || {
    larch_err "ERROR=Failed to fetch issue #$ISSUE_NUMBER"
    exit 1
}

TITLE=$(echo "$ISSUE_JSON" | jq -r '.title // "Untitled"')
BODY=$(echo "$ISSUE_JSON" | jq -r '.body // "No description provided."')
LABELS=$(echo "$ISSUE_JSON" | jq -r '[ (.labels // [])[] | .name ] | if length == 0 then "none" else join(", ") end')
CREATED=$(echo "$ISSUE_JSON" | jq -r '.createdAt // "unknown"')

# Fetch all comments (paginated)
COMMENTS=$(gh api --paginate --slurp "repos/${REPO}/issues/${ISSUE_NUMBER}/comments" 2>/dev/null | jq 'add // []') || {
    larch_err "ERROR=Failed to fetch comments for issue #$ISSUE_NUMBER"
    exit 1
}

# Write structured output
{
    printf '%s\n' "# Issue #${ISSUE_NUMBER}: ${TITLE}"
    printf '%s\n' "**Labels**: ${LABELS}"
    printf '%s\n' "**Created**: ${CREATED}"
    printf '%s\n' ""
    printf '%s\n' "## Description"
    printf '%s\n' ""
    printf '%s\n' "$BODY"
    printf '%s\n' ""
    printf '%s\n' "## Comments"
    printf '%s\n' ""

    COMMENT_COUNT=$(echo "$COMMENTS" | jq 'length')
    if [ "$COMMENT_COUNT" -eq 0 ]; then
        printf '%s\n' "No comments."
    else
        printf '%s\n' "$COMMENTS" | jq -r '.[] | select((.body // "" | split("\n")[0] | startswith("<!-- larch:")) | not) | "### Comment by \(.user.login) at \(.created_at)\n\n\(.body)\n"'
    fi
} > "$OUTPUT_PATH"

emit_kv OUTPUT_FILE "$OUTPUT_PATH"
