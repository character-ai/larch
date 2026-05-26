#!/usr/bin/env bash
# get-issue-context.sh — Fetch issue title/body into implement tmpdir files.
set -euo pipefail

SCRIPT_DIR="$(cd "${BASH_SOURCE[0]%/*}" && pwd -P)"
larch_err() {
    printf '%s\n' "$*" >&2
}

usage() {
    larch_err "Usage: get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH"
}

ISSUE=""
REPO=""
TMPDIR_ARG="${IMPLEMENT_TMPDIR:-}"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --issue) ISSUE="${2:?--issue requires a value}"; shift 2 ;;
        --repo) REPO="${2:?--repo requires a value}"; shift 2 ;;
        --tmpdir) TMPDIR_ARG="${2:?--tmpdir requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 2 ;;
    esac
done

if [[ -z "$ISSUE" || -z "$REPO" || -z "$TMPDIR_ARG" ]]; then
    usage
    exit 2
fi

# GitHub issue numbers are >=1, so this deliberately rejects 0 and
# leading-zero forms. The divergence from lax peers is intentional:
# tracking-issue-read.sh (--issue and sentinel ISSUE_NUMBER) and
# get-issue-state.sh accept bare all-digits; a future hardening pass
# should tighten them, not loosen this. clarify-comment-post.sh and
# clarify-state.sh reach the same >=1 semantics with all-digits + zero checks.
if [[ ! "$ISSUE" =~ ^[1-9][0-9]*$ ]]; then
    larch_err "ERROR: --issue must be a positive integer (>= 1; #0 is not a valid GitHub issue number)"
    exit 2
fi

if [[ ! "$REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    larch_err "ERROR: --repo must be OWNER/REPO using GitHub owner/repo characters"
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    larch_err "ERROR: jq is required to parse the issue JSON; install it (e.g. \`brew install jq\` / \`apt install jq\`) and retry."
    exit 2
fi

# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

mkdir -p "$TMPDIR_ARG"
title_tmp="$TMPDIR_ARG/upstream-issue-title.txt.tmp"
body_tmp="$TMPDIR_ARG/upstream-issue-body.txt.tmp"

json=$(gh issue view "$ISSUE" --repo "$REPO" --json title,body 2>/dev/null) || {
    larch_err "ERROR: gh issue view failed for #$ISSUE in $REPO"
    exit 1
}

printf '%s\n' "$json" | jq -r '.title // ""' > "$title_tmp"
printf '%s\n' "$json" | jq -r '.body // ""' > "$body_tmp"
mv -f "$title_tmp" "$TMPDIR_ARG/upstream-issue-title.txt"
mv -f "$body_tmp" "$TMPDIR_ARG/upstream-issue-body.txt"

emit_kv TITLE_FILE "$TMPDIR_ARG/upstream-issue-title.txt"
emit_kv BODY_FILE "$TMPDIR_ARG/upstream-issue-body.txt"
