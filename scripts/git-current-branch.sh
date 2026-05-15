#!/usr/bin/env bash
# git-current-branch.sh — Print the current branch name in KEY=VALUE form.
#
# Wraps `git symbolic-ref --short HEAD` so callers invoke a pre-approved
# script instead of a raw `git` command (avoids per-invocation permission
# prompts in Claude Code sessions).
#
# Usage:
#   git-current-branch.sh
#
# Output (stdout):
#   BRANCH=<name>          On a named branch.
#
# Exit codes:
#   0 — on a named branch (BRANCH emitted)
#   1 — detached HEAD or not in a git repo (nothing emitted, error on stderr)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/lib-quiet.sh" ]]; then
    # shellcheck source=scripts/lib-quiet.sh
    source "$SCRIPT_DIR/lib-quiet.sh"
    larch_quiet_init
else
    emit_kv() { printf '%s=%s\n' "$1" "${2-}"; }
    larch_err() { printf '%s\n' "$*" >&2; }
fi

if BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null); then
    emit_kv BRANCH "$BRANCH"
    exit 0
fi

larch_err "git-current-branch.sh: not on a named branch (detached HEAD or not a git repo)"
exit 1
