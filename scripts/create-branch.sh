#!/usr/bin/env bash
# create-branch.sh — Branch creation for /design skill.
#
# Two modes:
#   --check          Output current branch state (no side effects)
#   --branch NAME    Create a new branch from latest origin/main
#
# Usage:
#   create-branch.sh --check
#   create-branch.sh --branch <branch-name>
#
# Outputs (key=value to stdout):
#   --check mode:
#     CURRENT_BRANCH=<name>     (empty if detached HEAD)
#     IS_MAIN=true|false
#     IS_USER_BRANCH=true|false
#     USER_PREFIX=<value>       (derived from git config user.name)
#
#   --branch mode:
#     BRANCH_NAME=<name>
#     ACTION=created
#
# Exit codes:
#   0 — success
#   1 — branch already exists (--branch mode only)
#   2 — git operation failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh"

usage() { larch_err "Usage: create-branch.sh --check | create-branch.sh --branch NAME"; }

# Derive user prefix from git config user.name:
# lowercase, spaces→hyphens, strip non-alphanumeric-hyphens, truncate to 20 chars, fallback "dev"
derive_user_prefix() {
    local raw
    raw=$(git config user.name 2>/dev/null || echo "")
    if [[ -z "$raw" ]]; then
        echo "dev"
        return
    fi
    local sanitized
    sanitized=$(printf '%s\n' "$raw" | tr '[:upper:]' '[:lower:]' | tr ' ' '-' | sed 's/[^a-z0-9-]//g' | head -c 20 | sed 's/-*$//')
    if [[ -z "$sanitized" ]]; then
        echo "dev"
        return
    fi
    echo "$sanitized"
}

MODE=""
BRANCH_NAME=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check) MODE="check"; shift ;;
        --branch) MODE="create"; BRANCH_NAME="${2:?--branch requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "Unknown option: $1"; usage; exit 2 ;;
    esac
done

if [[ -z "$MODE" ]]; then
    larch_err "ERROR: --check or --branch is required"
    usage; exit 2
fi

USER_PREFIX=$(derive_user_prefix)

if [[ "$MODE" == "check" ]]; then
    # --- Check mode: report current branch state ---
    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")

    IS_MAIN="false"
    IS_USER_BRANCH="false"

    if [[ -z "$CURRENT_BRANCH" ]] || [[ "$CURRENT_BRANCH" == "main" ]]; then
        IS_MAIN="true"
    elif [[ "$CURRENT_BRANCH" == "${USER_PREFIX}"/* ]]; then
        IS_USER_BRANCH="true"
    fi

    emit_kv CURRENT_BRANCH "$CURRENT_BRANCH"
    emit_kv IS_MAIN "$IS_MAIN"
    emit_kv IS_USER_BRANCH "$IS_USER_BRANCH"
    emit_kv USER_PREFIX "$USER_PREFIX"
    exit 0
fi

# --- Create mode: create branch from latest main ---

# Validate branch name format
if [[ ! "$BRANCH_NAME" == "${USER_PREFIX}"/* ]]; then
    larch_err "ERROR: Branch name must start with '${USER_PREFIX}/': $BRANCH_NAME"
    exit 2
fi

# Check if branch already exists
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null; then
    larch_err "ERROR: Branch already exists: $BRANCH_NAME"
    exit 1
fi

# Fetch latest main and create branch directly from origin/main
# (avoids unnecessary checkout main + pull round-trip)
fetch_fail_file=$(mktemp "${TMPDIR:-/tmp}/create-branch-fetch.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$fetch_fail_file" \
    git fetch origin main --quiet; then
    fetch_rc=0
else
    fetch_rc=$_WTR_RC
fi
rm -f "$fetch_fail_file"
if [[ "$fetch_rc" -ne 0 ]]; then
    larch_err "ERROR: Failed to fetch origin/main"
    exit 2
fi

if ! git checkout -b "$BRANCH_NAME" origin/main >/dev/null 2>&1; then
    larch_err "ERROR: Failed to create branch: $BRANCH_NAME"
    exit 2
fi

emit_kv BRANCH_NAME "$BRANCH_NAME"
emit_kv ACTION created
