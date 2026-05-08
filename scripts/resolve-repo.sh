#!/usr/bin/env bash
# resolve-repo.sh - Print the current GitHub repository as OWNER/REPO.

set -euo pipefail

RESOLVED=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || RESOLVED=""

if [[ -z "$RESOLVED" ]]; then
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
    if [[ -n "$REMOTE_URL" ]]; then
        RESOLVED=$(printf '%s\n' "$REMOTE_URL" \
            | sed -E \
                -e 's#^git@github\.com:##' \
                -e 's#^ssh://git@github\.com/##' \
                -e 's#^https://github\.com/##' \
                -e 's#\.git$##')
    fi
fi

if [[ -z "$RESOLVED" || ! "$RESOLVED" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR=could not resolve repo (gh repo view + git remote both failed)" >&2
    exit 1
fi

printf '%s\n' "$RESOLVED"
