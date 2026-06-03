#!/usr/bin/env bash
# git-force-push.sh — Force-push the current branch with lease protection + recovery.
#
# Wraps `git push --force-with-lease` with the full recovery logic from
# /implement's Rebase + Re-bump Sub-procedure step 5
# (skills/implement/references/conflict-resolution.md):
#   - Refresh the local tracking ref (`git fetch origin <branch>`) best-effort,
#     then try `git push --force-with-lease` once.
#   - On failure: refresh the local tracking ref again,
#     compare local HEAD vs origin/<branch>. If equal, the push actually landed
#     (rare race) — return success.
#   - If they differ, sleep 5s and retry the push ONCE.
#   - If the retry fails, return a structured "diverged_retry_failed" status so
#     the caller can bail.
#
# Usage:
#   git-force-push.sh [--expected-remote-oid OID]
#
# Output (stdout, KEY=VALUE):
#   BRANCH=<name>
#   PUSHED=true|false
#   STATUS=pushed|noop_same_ref|diverged_retry_failed|dirty_worktree
#
# Exit codes:
#   0 — PUSHED=true (either pushed fresh or race-landed)
#   1 — dirty-tree guard aborted before push (PUSHED=false, STATUS=dirty_worktree), or PUSHED=false with STATUS=diverged_retry_failed
#   2 — not on a named branch (detached HEAD / not a git repo), or guard/setup failed

set -euo pipefail

SLEEP_SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$SLEEP_SCRIPT_DIR"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

GIT_STATUS_STDERR=""

EXPECTED_REMOTE_OID=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --expected-remote-oid)
            EXPECTED_REMOTE_OID="${2:?--expected-remote-oid requires a value}"
            shift 2
            ;;
        *)
            larch_err "git-force-push.sh: unknown option: $1"
            exit 2
            ;;
    esac
done

if ! BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null); then
    larch_err "git-force-push.sh: not on a named branch"
    exit 2
fi
emit_kv BRANCH "$BRANCH"

# Pre-push clean-tree guard: uncommitted working-tree changes are silently
# excluded from a push, causing data loss (issue #2434).
GIT_STATUS_STDERR=$(mktemp)
if ! DIRTY_FILES=$(git status --porcelain 2>"$GIT_STATUS_STDERR"); then
    larch_err "git-force-push.sh: failed to inspect working tree before force-push: $(cat "$GIT_STATUS_STDERR")"
    rm -f "$GIT_STATUS_STDERR"
    exit 2
fi
if [[ -n "$DIRTY_FILES" ]]; then
    emit_kv PUSHED "false"
    emit_kv STATUS "dirty_worktree"
    larch_err "git-force-push.sh: uncommitted working-tree changes detected before force-push. Stage and commit them before pushing."
    larch_err "$DIRTY_FILES"
    rm -f "$GIT_STATUS_STDERR"
    exit 1
fi
rm -f "$GIT_STATUS_STDERR"

push_with_lease() {
    if [[ -n "$EXPECTED_REMOTE_OID" ]]; then
        git push --force-with-lease="refs/heads/$BRANCH:$EXPECTED_REMOTE_OID"
    else
        git push --force-with-lease
    fi
}

# Refresh the tracking ref before the lease check, then make the first attempt.
git fetch origin "$BRANCH" 2>/dev/null || true
if push_with_lease; then
    emit_kv PUSHED "true"
    emit_kv STATUS "pushed"
    exit 0
fi

# Push failed. Refresh the tracking ref.
git fetch origin "$BRANCH" 2>/dev/null || true

# Compare local HEAD to origin/$BRANCH.
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH" 2>/dev/null || echo "")

if [[ -n "$REMOTE" && "$LOCAL" == "$REMOTE" ]]; then
    # Remote accepted the push in the race; client didn't observe the success.
    emit_kv PUSHED "true"
    emit_kv STATUS "noop_same_ref"
    exit 0
fi

# Local and remote diverge. Sleep 5s and retry once.
"$SLEEP_SCRIPT_DIR/sleep-seconds.sh" 5 >/dev/null 2>&1 || sleep 5

if push_with_lease; then
    emit_kv PUSHED "true"
    emit_kv STATUS "pushed"
    exit 0
fi

emit_kv PUSHED "false"
emit_kv STATUS "diverged_retry_failed"
exit 1
