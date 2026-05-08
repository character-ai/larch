#!/usr/bin/env bash
# get-issue-context.sh — Fetch issue title/body into implement tmpdir files.
set -euo pipefail

usage() {
    echo "Usage: get-issue-context.sh --issue N --repo OWNER/REPO --tmpdir PATH" >&2
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
        *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$ISSUE" || -z "$REPO" || -z "$TMPDIR_ARG" ]]; then
    usage
    exit 2
fi

if [[ ! "$ISSUE" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: --issue must be a positive integer (>= 1; #0 is not a valid GitHub issue number)" >&2
    exit 2
fi

if [[ ! "$REPO" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR: --repo must be OWNER/REPO using GitHub owner/repo characters" >&2
    exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq is required to parse the issue JSON; install it (e.g. \`brew install jq\` / \`apt install jq\`) and retry." >&2
    exit 2
fi

mkdir -p "$TMPDIR_ARG"
title_tmp="$TMPDIR_ARG/upstream-issue-title.txt.tmp"
body_tmp="$TMPDIR_ARG/upstream-issue-body.txt.tmp"

json=$(gh issue view "$ISSUE" --repo "$REPO" --json title,body 2>/dev/null) || {
    echo "ERROR: gh issue view failed for #$ISSUE in $REPO" >&2
    exit 1
}

printf '%s\n' "$json" | jq -r '.title // ""' > "$title_tmp"
printf '%s\n' "$json" | jq -r '.body // ""' > "$body_tmp"
mv -f "$title_tmp" "$TMPDIR_ARG/upstream-issue-title.txt"
mv -f "$body_tmp" "$TMPDIR_ARG/upstream-issue-body.txt"

printf 'TITLE_FILE=%s\n' "$TMPDIR_ARG/upstream-issue-title.txt"
printf 'BODY_FILE=%s\n' "$TMPDIR_ARG/upstream-issue-body.txt"
