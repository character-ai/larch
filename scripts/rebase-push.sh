#!/usr/bin/env bash
# rebase-push.sh — Rebase onto a configured base and optionally force-push with lease.
#
# Fetches the configured base ref, rebases, and (unless --no-push) pushes. Reports
# conflicts and push failures via exit codes.
#
# Usage:
#   rebase-push.sh [--continue] [--no-push [--skip-if-pushed] [--keep-on-conflict]] [--base-remote NAME] [--base-ref BRANCH]
#
# Flags:
#   --continue       — Continue an in-progress rebase instead of starting a new
#                      one. Skips fetch and runs `git rebase --continue` instead
#                      of `git rebase $BASE_TARGET`. Caller must resolve
#                      conflicts and stage files before invoking with --continue.
#   --no-push        — Skip the push step after a successful rebase. Used by
#                      /implement for local-only freshness rebases
#                      where the branch has not yet been pushed. In this mode,
#                      conflicts are aborted immediately (exit 1) instead of
#                      left in progress unless --keep-on-conflict is set.
#   --skip-if-pushed — Only valid with --no-push. Before fetching, check whether
#                      the current branch already exists on origin. If it does,
#                      print `SKIPPED_ALREADY_PUSHED=true` to stdout and exit 0
#                      without fetching or rebasing. This lets /implement
#                      collapse its per-checkpoint "is branch pushed? if so skip,
#                      else rebase" dance into a single script invocation. If the
#                      ls-remote check fails (network/auth), the script falls
#                      through to the normal rebase path so the subsequent fetch
#                      surfaces the real error.
#   --keep-on-conflict
#                    — Only valid with --no-push. On rebase conflict, leave
#                      the rebase in progress and emit CONFLICT_FILES= so the
#                      caller can resolve and continue without pushing.
#   --base-remote NAME
#                    — Remote to fetch/rebase against (default: origin).
#   --base-ref BRANCH
#                    — Branch/ref name on base remote (default: main).
#
# Exit codes:
#   0 — rebase (and push, unless --no-push) succeeded, OR skipped because
#       --skip-if-pushed detected the branch already on origin, OR (in
#       --no-push mode only) skipped because HEAD already contains
#       $BASE_TARGET (nothing to rebase)
#   1 — rebase failed with conflicts
#       Default mode: rebase left in progress (CONFLICT_FILES= on stdout)
#       --no-push mode: rebase aborted unless --keep-on-conflict is set.
#       With --keep-on-conflict, rebase left in progress (CONFLICT_FILES= on stdout)
#   2 — push --force-with-lease failed (PUSH_ERROR= on stderr, caller should retry after fetch)
#       Not possible in --no-push mode.
#   3 — rebase failed for non-conflict reasons (REBASE_ERROR= on stderr), OR
#       invalid flag combination (e.g., --skip-if-pushed without --no-push,
#       --continue --no-push without --keep-on-conflict)
#       In normal mode: rebase is aborted.
#       In --continue mode: rebase is left in progress (caller can inspect/retry).
#       In --no-push mode: rebase is aborted.
#
# Stdout on exit 0 when --skip-if-pushed skipped the rebase:
#   SKIPPED_ALREADY_PUSHED=true
#
# Stdout on exit 0 when --no-push and HEAD already contains $BASE_TARGET:
#   SKIPPED_ALREADY_FRESH=true
#   Only emitted in --no-push mode. In default (push) mode the script
#   always proceeds to the push step even if the rebase would be a no-op,
#   because a feature branch may have local commits that still need to
#   reach origin.
#
# Stdout on exit 1 (default mode only):
#   CONFLICT_FILES=<comma-separated list of conflicted files>
#
# Note: On exit 1 in default mode, the rebase is left in progress so the
# caller can resolve conflicts and run `rebase-push.sh --continue`. On exit 1
# in --no-push mode, the rebase is aborted unless --keep-on-conflict is set.
# On exit 3 in normal mode, the rebase is aborted. On exit 3 in --continue
# mode, the rebase is left in progress to avoid destroying already-resolved work.

set -uo pipefail
# Note: not using set -e — we need to capture exit codes explicitly

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# --- Parse flags ---
CONTINUE_MODE=false
NO_PUSH=false
SKIP_IF_PUSHED=false
KEEP_ON_CONFLICT=false
BASE_REMOTE="origin"
BASE_REF="main"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --continue) CONTINUE_MODE=true; shift ;;
        --no-push) NO_PUSH=true; shift ;;
        --skip-if-pushed) SKIP_IF_PUSHED=true; shift ;;
        --keep-on-conflict) KEEP_ON_CONFLICT=true; shift ;;
        --base-remote) BASE_REMOTE="${2:?--base-remote requires a value}"; shift 2 ;;
        --base-ref) BASE_REF="${2:?--base-ref requires a value}"; shift 2 ;;
        *) larch_err "Unknown option: $1"; exit 1 ;;
    esac
done

if [[ ! "$BASE_REMOTE" =~ ^[A-Za-z0-9._/-]+$ ]]; then
    emit_kv REBASE_ERROR "--base-remote contains unsupported characters"
    exit 3
fi

if [[ ! "$BASE_REF" =~ ^[A-Za-z0-9._/-]+$ ]]; then
    emit_kv REBASE_ERROR "--base-ref contains unsupported characters"
    exit 3
fi

BASE_TARGET="${BASE_REMOTE}/${BASE_REF}"

if [[ "$SKIP_IF_PUSHED" == "true" && "$NO_PUSH" != "true" ]]; then
    emit_kv REBASE_ERROR "--skip-if-pushed is only valid with --no-push"
    exit 3
fi

if [[ "$SKIP_IF_PUSHED" == "true" && "$CONTINUE_MODE" == "true" ]]; then
    emit_kv REBASE_ERROR "--skip-if-pushed cannot be used with --continue"
    exit 3
fi

if [[ "$KEEP_ON_CONFLICT" == "true" && "$NO_PUSH" != "true" ]]; then
    emit_kv REBASE_ERROR "--keep-on-conflict is only valid with --no-push"
    exit 3
fi

# --continue --no-push is the local-only conflict-resolution loop used by
# the Rebase Checkpoint Macro's early_rebase path; in that loop a nested
# conflict on a later commit MUST leave the rebase in progress so the
# caller can resolve and re-continue. Without --keep-on-conflict the
# script would silently abort the in-progress rebase on a nested conflict
# and discard any partial resolution. Reject the combination at parse
# time rather than risk losing work — every legitimate caller of
# --continue --no-push (the early_rebase Phase 4 invocation) already
# passes --keep-on-conflict, so this is defense-in-depth, not a behavior
# change for any documented call site.
if [[ "$CONTINUE_MODE" == "true" && "$NO_PUSH" == "true" && "$KEEP_ON_CONFLICT" != "true" ]]; then
    emit_kv REBASE_ERROR "--continue --no-push requires --keep-on-conflict to safely handle nested conflicts"
    exit 3
fi

# --- Early exit: skip if branch already on origin (--skip-if-pushed only) ---
if [[ "$SKIP_IF_PUSHED" == "true" ]]; then
    CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
    # If detached HEAD (empty branch name), fall through to the normal rebase
    # path, where the detached-HEAD guard below will error cleanly.
    if [[ -n "$CURRENT_BRANCH" ]]; then
        # Use the full "refs/heads/<branch>" form to force an exact-match
        # lookup — ls-remote's pattern arg otherwise uses fnmatch/glob
        # semantics, which would misbehave for branches containing [, ?, *.
        # If ls-remote fails (network/auth), we fall through to the normal
        # rebase path; the subsequent fetch will surface the real error.
        if REMOTE_REFS=$(git ls-remote --heads origin "refs/heads/$CURRENT_BRANCH" 2>/dev/null) && [[ -n "$REMOTE_REFS" ]]; then
            emit_kv SKIPPED_ALREADY_PUSHED "true"
            exit 0
        fi
    fi
fi

if [[ "$CONTINUE_MODE" == "true" ]]; then
    # --- Guard: must have a rebase in progress ---
    GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
    if [[ -z "$GIT_DIR" || (! -d "$GIT_DIR/rebase-merge" && ! -d "$GIT_DIR/rebase-apply") ]]; then
        emit_kv REBASE_ERROR "--continue called but no rebase is in progress"
        exit 3
    fi

    # --- Continue an in-progress rebase (GIT_EDITOR=true prevents editor hang) ---
    REBASE_OUTPUT=$(GIT_EDITOR=true git rebase --continue 2>&1)
    REBASE_EXIT=$?
else
    # --- Guard: must be on a branch, not detached HEAD ---
    if ! git symbolic-ref --quiet HEAD > /dev/null 2>&1; then
        emit_kv REBASE_ERROR "Not on a branch (detached HEAD)"
        exit 3
    fi

    # --- Fetch latest base ---
    # In --no-push mode, fetch failure is fatal (the whole point is freshness).
    # In default mode, fetch failure is tolerated to allow rebasing against the cached $BASE_TARGET.
    if [[ "$NO_PUSH" == "true" ]]; then
        if ! git fetch "$BASE_REMOTE" "$BASE_REF" --quiet 2>/dev/null; then
            emit_kv REBASE_ERROR "git fetch $BASE_REMOTE $BASE_REF failed (network/auth issue)"
            exit 3
        fi
    else
        git fetch "$BASE_REMOTE" "$BASE_REF" --quiet 2>/dev/null || true
    fi

    # --- Early exit: skip rebase if HEAD already contains $BASE_TARGET ---
    # If $BASE_TARGET is an ancestor of HEAD, HEAD already has every commit
    # from the base ref, so `git rebase $BASE_TARGET` would be a no-op. Exit 0
    # with a SKIPPED_ALREADY_FRESH=true marker so callers can log it distinctly.
    #
    # This optimization is gated on --no-push mode. In default (push) mode we
    # must still reach the push step: a feature branch may have local commits
    # that have never been pushed, and HEAD containing $BASE_TARGET says
    # nothing about whether the remote tracking branch is up to date.
    if [[ "$NO_PUSH" == "true" ]] && git merge-base --is-ancestor "$BASE_TARGET" HEAD 2>/dev/null; then
        emit_kv SKIPPED_ALREADY_FRESH "true"
        exit 0
    fi

    # --- Attempt rebase ---
    REBASE_OUTPUT=$(git rebase "$BASE_TARGET" 2>&1)
    REBASE_EXIT=$?
fi

if [[ $REBASE_EXIT -ne 0 ]]; then
    # Check if there are conflicts
    CONFLICT_FILES=$(git diff --name-only --diff-filter=U 2>/dev/null | tr '\n' ',' | sed 's/,$//')
    if [[ -n "$CONFLICT_FILES" ]]; then
        if [[ "$NO_PUSH" == "true" && "$KEEP_ON_CONFLICT" != "true" ]]; then
            # In --no-push mode, abort immediately — caller does not resolve conflicts
            git rebase --abort 2>/dev/null || true
            exit 1
        fi
        emit_kv CONFLICT_FILES "$CONFLICT_FILES"
        # Leave the rebase in progress so caller can resolve and --continue
        exit 1
    else
        # Rebase failed for another reason (not conflicts)
        # Sanitize multi-line git output to single line for key=value protocol
        REBASE_OUTPUT="${REBASE_OUTPUT//$'\n'/ }"
        emit_kv REBASE_ERROR "$REBASE_OUTPUT"
        if [[ "$CONTINUE_MODE" == "true" ]]; then
            # In --continue mode, leave rebase in progress to avoid destroying
            # already-resolved work. Caller can inspect and retry.
            exit 3
        else
            git rebase --abort 2>/dev/null || true
            exit 3
        fi
    fi
fi

# --- Skip push in --no-push mode ---
if [[ "$NO_PUSH" == "true" ]]; then
    exit 0
fi

# --- Attempt force-push with retry and jittered backoff ---
# Preserve the original expected remote OID across retries so a failed lease
# cannot refresh to a newer remote tip and overwrite another runner's push.
_PUSH_MAX=3
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null)
if [[ -z "$CURRENT_BRANCH" ]]; then
    emit_kv PUSH_ERROR "Not on a branch (detached HEAD) before push"
    exit 2
fi
LEASE_REF="refs/heads/$CURRENT_BRANCH"
git fetch "$BASE_REMOTE" "$CURRENT_BRANCH" --quiet 2>/dev/null || true
EXPECTED_REMOTE_OID=$(git rev-parse "$BASE_REMOTE/$CURRENT_BRANCH" 2>/dev/null || printf '')
LEASE_ARG="--force-with-lease=$LEASE_REF:$EXPECTED_REMOTE_OID"
for _push_attempt in 1 2 3; do
    if ! git symbolic-ref --quiet HEAD >/dev/null 2>&1; then
        emit_kv PUSH_ERROR "Not on a branch (detached HEAD) before push attempt $_push_attempt"
        exit 2
    fi
    PUSH_OUTPUT=$(git push "$LEASE_ARG" 2>&1)
    PUSH_EXIT=$?
    if [[ $PUSH_EXIT -eq 0 ]]; then
        exit 0
    fi
    git fetch "$BASE_REMOTE" "$CURRENT_BRANCH" --quiet 2>/dev/null || true
    LOCAL_HEAD=$(git rev-parse HEAD 2>/dev/null || printf '')
    REMOTE_HEAD=$(git rev-parse "$BASE_REMOTE/$CURRENT_BRANCH" 2>/dev/null || printf '')
    if [[ -n "$LOCAL_HEAD" && -n "$REMOTE_HEAD" && "$LOCAL_HEAD" == "$REMOTE_HEAD" ]]; then
        exit 0
    fi
    if [[ $_push_attempt -lt $_PUSH_MAX ]]; then
        # Jittered backoff: base 1s/2s ±25 %
        _base=$(( 1 * 2 ** (_push_attempt - 1) ))
        _jitter=$(( RANDOM % (_base / 2 + 1) ))
        _sleep=$(( _base + _jitter - _base / 4 ))
        [[ $_sleep -lt 1 ]] && _sleep=1
        sleep "$_sleep"
    fi
done
PUSH_OUTPUT="${PUSH_OUTPUT//$'\n'/ }"
emit_kv PUSH_ERROR "$PUSH_OUTPUT"
exit 2
