#!/usr/bin/env bash
# preflight.sh — Pre-skill sanity checks.
#
# Default: verify on main, clean working tree, then fetch+rebase to latest main.
# With --skip-branch-check: skip the on-main check. With --skip-clean-check:
# skip the clean working tree check. Rebase runs only when both checks run.
#
# Usage:
#   preflight.sh [--skip-branch-check] [--skip-clean-check]
#
# Exit codes:
#   0 — all checks passed
#   1 — not on main branch (only without --skip-branch-check)
#   2 — dirty working tree (only without --skip-clean-check)
#   3 — argument validation, git fetch, or rebase failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_BRANCH_CHECK=false
SKIP_CLEAN_CHECK=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-branch-check) SKIP_BRANCH_CHECK=true; shift ;;
        --skip-clean-check) SKIP_CLEAN_CHECK=true; shift ;;
        *) echo "Unknown option: $1" >&2; exit 3 ;;
    esac
done

if [[ "$SKIP_BRANCH_CHECK" == "false" ]]; then
    # Check on main
    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
    if [[ "$CURRENT_BRANCH" != "main" ]]; then
        echo "PREFLIGHT=fail"
        echo "PREFLIGHT_ERROR=Not on main branch (on '$CURRENT_BRANCH'). Switch to main first, or pass --skip-branch-check."
        exit 1
    fi
fi

# Check clean status
if [[ "$SKIP_CLEAN_CHECK" == "false" ]]; then
    CLEAN_TREE_OUT=$("$SCRIPT_DIR/check-clean-tree.sh" 2>/dev/null || true)
    CLEAN_TREE=$(echo "$CLEAN_TREE_OUT" | awk -F= '/^CLEAN=/ { v=$2 } END { print v }')
    if [[ "$CLEAN_TREE" == "false" ]]; then
        echo "PREFLIGHT=fail"
        echo "PREFLIGHT_ERROR=Working tree is not clean. Commit or stash changes first."
        exit 2
    fi
fi

# Always fetch to ensure origin/main is current. Rebase requires being on main.
if ! git fetch origin main --quiet 2>/dev/null; then
    echo "PREFLIGHT=fail"
    echo "PREFLIGHT_ERROR=git fetch origin main failed."
    exit 3
fi

if [[ "$SKIP_BRANCH_CHECK" == "false" && "$SKIP_CLEAN_CHECK" == "false" ]]; then
    if ! git rebase origin/main --quiet 2>/dev/null; then
        git rebase --abort 2>/dev/null || true
        echo "PREFLIGHT=fail"
        echo "PREFLIGHT_ERROR=git rebase origin/main failed."
        exit 3
    fi
fi

# Clear the stalled-run sentinel only after every requested check has passed
# AND the working tree is genuinely clean. We must NOT delete it when
# --skip-clean-check is set with a dirty tree — recovery metadata for the
# prior stall is the only thing connecting the leftover edits to an issue.
if [[ "$SKIP_CLEAN_CHECK" == "false" || -z "$(git status --porcelain 2>/dev/null)" ]]; then
    sentinel_path=$(git rev-parse --git-path larch-stalled-run.txt 2>/dev/null || echo "")
    if [[ -n "$sentinel_path" ]]; then
        rm -f "$sentinel_path" 2>/dev/null || true
    fi
fi

echo "PREFLIGHT=ok"
