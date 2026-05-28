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
# shellcheck source=scripts/lib-net.sh
source "$SCRIPT_DIR/lib-net.sh"

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

fail_file=$(mktemp "${TMPDIR:-/tmp}/check-remote-branch.XXXXXX")
if with_transient_retry transient_envelope_predicate_none "$fail_file" \
    git ls-remote --exit-code --heads "$REMOTE" "$BRANCH"; then
    RC=0
else
    RC=$_WTR_RC
fi
FAIL_CAPTURE=$(cat "$fail_file" 2>/dev/null || true)
rm -f "$fail_file"

case "$RC" in
    0)  emit_kv STATE present; emit_kv RC 0 ;;
    2)  emit_kv STATE absent;  emit_kv RC 2 ;;
    *)
        STDERR_FLAT=$(printf '%s\n' "$FAIL_CAPTURE" | tr '\n' ' ' | sed 's/  */ /g; s/^ //; s/ $//')
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
