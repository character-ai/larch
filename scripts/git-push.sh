#!/usr/bin/env bash
# git-push.sh — Push the current branch to origin (fast-forward, no force).
#
# Wraps a plain `git push` for non-force updates (e.g., when /implement's
# Step 10 / Step 12c adds a CI fix commit on top of the existing remote tip).
# For force-with-lease updates after a rebase, use `git-force-push.sh` instead.
#
# Usage:
#   git-push.sh
#
# Output (stdout): BRANCH=<name>
#
# Exit codes:
#   0 — push succeeded (or branch was already up-to-date)
#   1 — not on a named branch (detached HEAD / not a git repo)
#   >0 — passthrough from `git push`

set -euo pipefail

if ! BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null); then
    echo "git-push.sh: not on a named branch" >&2
    exit 1
fi
echo "BRANCH=$BRANCH"

# Retry loop with jittered backoff for transient non-fast-forward rejections
# (e.g. concurrent pushes). Detached-HEAD is checked before each attempt so
# a mid-loop `git rebase` that leaves HEAD detached is caught immediately.
# First retry sleeps a fixed 1s floor; later retries use the jittered formula
# below.
#
# Per-attempt stderr is captured so identical consecutive blocks are deduplicated
# on failure: each unique block is emitted once; if a block repeated M times
# "(repeated M times)" is appended so the caller sees one clean diagnostic.
_MAX_ATTEMPTS=3
_last_exit=0
_STDERR_DIR=$(mktemp -d)
trap 'rm -rf "$_STDERR_DIR"' EXIT
for _attempt in 1 2 3; do
    if ! git symbolic-ref --quiet HEAD >/dev/null 2>&1; then
        printf 'git-push.sh: not on a named branch before attempt %d\n' "$_attempt" >&2
        exit 1
    fi
    if git push 2>"$_STDERR_DIR/attempt-$_attempt"; then
        exit 0
    else
        _last_exit=$?
    fi
    if [ "$_attempt" -lt "$_MAX_ATTEMPTS" ]; then
        # Jittered backoff: first retry fixed 1s, then base 2s ±25 %
        _base=$(( 1 * 2 ** (_attempt - 1) ))
        _jitter=$(( RANDOM % (_base / 2 + 1) ))
        _sleep=$(( _base + _jitter - _base / 4 ))
        [ "$_sleep" -lt 1 ] && _sleep=1
        sleep "$_sleep"
    fi
done

# Deduplicate consecutive identical stderr blocks before emitting.
_prev_file=""
_repeat=0
for _n in 1 2 3; do
    _cur="$_STDERR_DIR/attempt-$_n"
    [ -f "$_cur" ] || continue
    if [ -n "$_prev_file" ] && cmp -s "$_prev_file" "$_cur" 2>/dev/null; then
        _repeat=$(( _repeat + 1 ))
    else
        if [ -n "$_prev_file" ]; then
            cat "$_prev_file" >&2
            if [ "$_repeat" -gt 0 ]; then
                printf '(repeated %d times)\n' "$(( _repeat + 1 ))" >&2
            fi
        fi
        _prev_file="$_cur"
        _repeat=0
    fi
done
if [ -n "$_prev_file" ]; then
    cat "$_prev_file" >&2
    if [ "$_repeat" -gt 0 ]; then
        printf '(repeated %d times)\n' "$(( _repeat + 1 ))" >&2
    fi
fi

exit "$_last_exit"
