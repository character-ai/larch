#!/usr/bin/env bash
# audit-preflight.sh — Pre-flight checks for /audit-runs.
#
# Runs: git fetch/pull, repo-identity verification, concurrency guard.
# Output KV (stdout): PREFLIGHT_OK=true|false  REASON=<msg>
#
# Usage:
#   audit-preflight.sh --repo OWNER/NAME [--allow-concurrent]
#
# Exit codes: 0 always (caller reads PREFLIGHT_OK from stdout).

set -euo pipefail

REPO=""
ALLOW_CONCURRENT=false

while [ $# -gt 0 ]; do
    case "$1" in
        --repo) REPO="$2"; shift 2 ;;
        --allow-concurrent) ALLOW_CONCURRENT=true; shift ;;
        *)
            printf 'audit-preflight.sh: unknown argument: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if [ -z "$REPO" ]; then
    printf 'PREFLIGHT_OK=false\nREASON=--repo is required\n'
    exit 0
fi

# Step 1: git fetch + fast-forward main when applicable
if ! git fetch origin main 2>/dev/null; then
    printf 'PREFLIGHT_OK=false\nREASON=git fetch origin main failed\n'
    exit 0
fi
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || printf '%s' "")
if [ "$CURRENT_BRANCH" = "main" ]; then
    if ! git pull --ff-only origin main 2>/dev/null; then
        printf 'PREFLIGHT_OK=false\nREASON=git pull --ff-only origin main failed (working tree may be dirty or branch is not ff-only)\n'
        exit 0
    fi
else
    if git show-ref --verify --quiet refs/heads/main 2>/dev/null && git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
        lm=$(git rev-parse main 2>/dev/null || true)
        om=$(git rev-parse origin/main 2>/dev/null || true)
        if [ -n "$lm" ] && [ -n "$om" ] && [ "$lm" != "$om" ] && git merge-base --is-ancestor "$lm" "$om" 2>/dev/null; then
            printf 'PREFLIGHT_OK=false\nREASON=local branch main is behind origin/main; fast-forward main (git checkout main && git pull --ff-only origin main) before auditing\n'
            exit 0
        fi
    fi
fi

# Dirty tree check
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    printf 'PREFLIGHT_OK=false\nREASON=working tree is dirty\n'
    exit 0
fi

# Step 2: repo-identity verification
REMOTE_URL=$(git config --get remote.origin.url 2>/dev/null || true)
GH_URL=$(gh repo view -R "$REPO" --json url --jq '.url' 2>/dev/null || true)

# Normalize both to owner/repo form
normalize_repo() {
    printf '%s' "$1" \
        | sed -n 's|.*github\.com[:/]\([^/]*/[^/.]*\)\.git|\1|p; s|.*github\.com[:/]\([^/]*/[^/]*\)$|\1|p' \
        | head -1
}
REMOTE_REPO=$(normalize_repo "$REMOTE_URL")
GH_REPO=$(printf '%s' "$GH_URL" | sed 's|https://github.com/||')

if [ -z "$REMOTE_REPO" ] || [ -z "$GH_REPO" ]; then
    printf 'PREFLIGHT_OK=false\nREASON=could not determine repo identity (remote=%s gh=%s)\n' "$REMOTE_URL" "$GH_URL"
    exit 0
fi
if [ "$REMOTE_REPO" != "$GH_REPO" ]; then
    printf 'PREFLIGHT_OK=false\nREASON=repo mismatch: normalized_remote_origin=%s gh_repo_identity=%s (expected clone to match gh repo view -R %s)\n' "$REMOTE_REPO" "$GH_REPO" "$REPO"
    exit 0
fi

# Step 3: concurrency guard (skip when --allow-concurrent)
if [ "$ALLOW_CONCURRENT" = "false" ]; then
    # macOS-portable: try -v-5M first, fall back to GNU -d
    if date -u -v-5M +"%Y-%m-%dT%H:%M:%SZ" >/dev/null 2>&1; then
        CUTOFF=$(date -u -v-5M +"%Y-%m-%dT%H:%M:%SZ")
    else
        CUTOFF=$(date -u -d "5 minutes ago" +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || true)
    fi

    if [ -z "$CUTOFF" ]; then
        printf 'PREFLIGHT_OK=false\nREASON=could not compute concurrency cutoff timestamp\n'
        exit 0
    fi

    RECENT=false
    if gh issue list --state all --label audit-report --repo "$REPO" \
        --json number,createdAt --limit 50 2>/dev/null \
        | jq -e --arg c "$CUTOFF" 'any(.[]; .createdAt > $c)' >/dev/null 2>&1; then
        RECENT=true
    fi

    if [ "$RECENT" = "true" ]; then
        printf 'PREFLIGHT_OK=false\nREASON=audit-report filed within the 5-minute concurrency window; use --allow-concurrent to override\n'
        exit 0
    fi
fi

printf 'PREFLIGHT_OK=true\nREASON=\n'
