#!/usr/bin/env bash
# hook-stop-fail-close.sh — Stop hook for post-/review halt protection.
#
# set -e omitted: every probe must fail open; the hook must always exit 0.
# Intentional per G-Bash-4: this hook must fail open and exit 0.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
exec 3>&1
hook_emit() { printf '%s
' "$1" >&3; }

implement_session_dir_exists() {
    [[ -n "$HOOK_CWD" ]] || return 1
    local roots=(
        "${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions"
        "/tmp"
        "/private/tmp"
    )
    local root dir
    for root in "${roots[@]}"; do
        [[ -d "$root" ]] || continue
        for dir in "$root"/claude-implement-*; do
            [[ -d "$dir" ]] && return 0
        done
    done
    return 1
}

INPUT=$(cat 2>/dev/null) || exit 0

STOP_ACTIVE=false
if command -v jq >/dev/null 2>&1; then
    SA=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null) || SA=false
    [[ "$SA" = "true" ]] && STOP_ACTIVE=true
fi
[[ "$STOP_ACTIVE" = "true" ]] && exit 0

HOOK_CWD=""
if command -v jq >/dev/null 2>&1; then
    HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || HOOK_CWD=""
fi

# Surface the active Claude Code session_id from the Stop event payload
# into LARCH_TOKEN_SESSION_ID so the resolver's session-id binding branch
# is reachable in production. Empty, missing, or null session_id unsets any
# inherited LARCH_TOKEN_SESSION_ID before the resolver falls through to TTL.
# The Python resolver consumes the `.larch-keepalive` `SESSION_ID=` slim
# session-identity record this feeds.
SID=""
if command -v jq >/dev/null 2>&1; then
    SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || SID=""
fi
if [[ -n "$SID" ]]; then
    export LARCH_TOKEN_SESSION_ID="$SID"
else
    unset LARCH_TOKEN_SESSION_ID || true
fi

IMPLEMENT_TMPDIR=""
if implement_session_dir_exists && command -v python3 >/dev/null 2>&1; then
    IMPLEMENT_TMPDIR=$(python3 "$PLUGIN_ROOT/python/cli.py" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""
fi
[[ -n "$IMPLEMENT_TMPDIR" ]] || exit 0
[[ ! -f "$IMPLEMENT_TMPDIR/.run-cleaned-up" ]] || exit 0

TMPDIR_BASENAME=$(basename "$IMPLEMENT_TMPDIR" 2>/dev/null) \
    || TMPDIR_BASENAME="<implement-tmpdir>"

# Block on post-/review boundary halt: review ran but Step 6 sentinel not yet written.
# review-round-summary.md is written by /review on completion; .review-boundary-passed
# is written by the orchestrator at the start of Step 6 (issue #1862).
if [[ -f "$IMPLEMENT_TMPDIR/review-round-summary.md" ]] && \
   [[ ! -f "$IMPLEMENT_TMPDIR/.review-boundary-passed" ]]; then
    REASON=$'You halted mid-Step-5 (post-/review boundary).\n\nNEXT REQUIRED: execute the Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5 post-/review directives, then touch .review-boundary-passed inside the active /implement tmpdir ('"$TMPDIR_BASENAME"$') to release this guard.\n\nOperator escape: hard-quit the session, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run.'
    HOOK_OUT=""
    if command -v jq >/dev/null 2>&1; then
        HOOK_OUT=$(jq -cn --arg r "$REASON" '{decision:"block",reason:$r}' 2>/dev/null) || HOOK_OUT=""
    fi
    if [[ -z "$HOOK_OUT" ]] && command -v python3 >/dev/null 2>&1; then
        HOOK_OUT=$(REASON="$REASON" python3 -c 'import json,os; print(json.dumps({"decision":"block","reason":os.environ["REASON"]}))' 2>/dev/null) || HOOK_OUT=""
    fi
    # jq/python3-absent static fallback. Fixed reason (no runtime interpolation).
    if [[ -z "$HOOK_OUT" ]]; then
        HOOK_OUT='{"decision":"block","reason":"You halted mid-Step-5 (post-/review boundary). Execute Cross-Skill Presence Propagation + Step 6 breadcrumb, then touch .review-boundary-passed inside the active /implement tmpdir."}'
    fi
    hook_emit "$HOOK_OUT"
    exit 0
fi

exit 0
