#!/usr/bin/env bash
# check-remote-branch.sh — detect whether a branch exists on origin.
#
# Wraps the inline `git ls-remote --exit-code --heads origin <branch>` probe
# that /implement Step 8b uses to decide whether the feature branch needs a
# force-push (rebase rewrote local history that origin still points at) or
# whether create-pr.sh will perform the initial push.
#
# `git ls-remote --exit-code` returns 0 when the named ref is present, 2
# when it is positively confirmed absent, and other non-zero (typically
# 128) on transport / auth / network failures. Step 8b's load-bearing
# trichotomy depends on distinguishing all three — see issue #818 for why
# transport failures must NOT silently degrade to a stale-remote path.
#
# Usage:
#   check-remote-branch.sh --branch BRANCH [--remote ORIGIN]
#
# Output (stdout, KEY=VALUE; always exits 0):
#   STATE=present|absent|error
#   RC=<git-ls-remote-exit-code>
#   ERROR=<single-line>           (only when STATE=error)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

BRANCH=""
REMOTE="origin"

while [ $# -gt 0 ]; do
    case "$1" in
        --branch) BRANCH="${2:-}"; shift 2 ;;
        --remote) REMOTE="${2:-}"; shift 2 ;;
        *)
            emit_kv STATE error
            emit_kv RC 1
            emit_kv ERROR "unknown flag: $1"
            exit 0 ;;
    esac
done

if [ -z "$BRANCH" ]; then
    emit_kv STATE error
    emit_kv RC 1
    emit_kv ERROR "--branch is required"
    exit 0
fi

# Capture stderr so transport-error messages can be redacted into ERROR=.
STDERR_TMP=$(mktemp)
trap 'rm -f "$STDERR_TMP"' EXIT

git ls-remote --exit-code --heads "$REMOTE" "$BRANCH" >/dev/null 2>"$STDERR_TMP"
RC=$?

case "$RC" in
    0)  emit_kv STATE present; emit_kv RC 0 ;;
    2)  emit_kv STATE absent;  emit_kv RC 2 ;;
    *)
        STDERR_FLAT=$(tr '\n' ' ' < "$STDERR_TMP" | sed 's/  */ /g; s/^ //; s/ $//')
        emit_kv STATE error
        emit_kv RC "$RC"
        if [ -n "$STDERR_FLAT" ]; then
            emit_kv ERROR "$STDERR_FLAT"
        else
            emit_kv ERROR "git ls-remote failed (exit $RC)"
        fi
        ;;
esac
exit 0
