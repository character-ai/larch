#!/usr/bin/env bash
# resolve-repo.sh - Print the current GitHub repository as OWNER/REPO.

set -euo pipefail

RESOLVED=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || RESOLVED=""

if [[ -z "$RESOLVED" ]]; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    RESOLVED=$("$SCRIPT_DIR/github-remote-repo.sh" origin 2>/dev/null) || RESOLVED=""
fi

if [[ -z "$RESOLVED" || ! "$RESOLVED" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    echo "ERROR=could not resolve repo (gh repo view + git remote both failed)" >&2
    exit 1
fi

printf '%s\n' "$RESOLVED"
