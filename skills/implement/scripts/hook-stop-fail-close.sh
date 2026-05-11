#!/usr/bin/env bash
# hook-stop-fail-close.sh — Stop hook for post-/design and post-/review halt protection.
#
# set -e omitted: every probe must fail open; the hook must always exit 0.
# Intentional per .claude/rules/shell-strict-mode.md.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)

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
# is reachable in production (parallels hook-post-design.sh). Empty /
# missing / null falls through to TTL. See lib-resolve-implement-tmpdir.sh
# session-id binding for the resolver-side .larch-keepalive SESSION_ID match
# this export feeds.
SID=""
if command -v jq >/dev/null 2>&1; then
    SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || SID=""
fi
[[ -n "$SID" ]] && export LARCH_TOKEN_SESSION_ID="$SID"

# shellcheck source=lib-resolve-implement-tmpdir.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-resolve-implement-tmpdir.sh"

IMPLEMENT_TMPDIR=$(resolve_implement_tmpdir "$HOOK_CWD")
[[ -n "$IMPLEMENT_TMPDIR" ]] || exit 0
[[ ! -f "$IMPLEMENT_TMPDIR/.run-cleaned-up" ]] || exit 0

TMPDIR_BASENAME=$(basename "$IMPLEMENT_TMPDIR" 2>/dev/null) \
    || TMPDIR_BASENAME="<implement-tmpdir>"

# Block on post-/design boundary halt: design ran but boundary gate not yet passed.
if [[ -f "$IMPLEMENT_TMPDIR/design-export/manifest.env" ]] && \
   [[ ! -f "$IMPLEMENT_TMPDIR/.boundary-gate-passed" ]]; then
    REASON=$'You halted mid-Step-1 (post-/design boundary).\n\nNEXT REQUIRED: run skills/implement/scripts/post-design-boundary.sh against the active /implement tmpdir ('"$TMPDIR_BASENAME"$'). If it emits POST_DESIGN_BOUNDARY_OK=true, continue per its terminal directive. If it emits MANIFEST_FAILED=true, bail to /implement Step 18 cleanup.\n\nOperator escape: hard-quit the session, OR remove the stale tmpdir manifest manually, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run.'
    if command -v jq >/dev/null 2>&1; then
        jq -cn --arg r "$REASON" '{decision:"block",reason:$r}' \
            || printf '%s\n' '{"decision":"block","reason":"You halted mid-Step-1 (post-/design boundary). Run post-design-boundary.sh against the active /implement tmpdir; continue per its terminal directive."}'
    else
        printf '%s\n' '{"decision":"block","reason":"You halted mid-Step-1 (post-/design boundary). Run post-design-boundary.sh against the active /implement tmpdir; continue per its terminal directive."}'
    fi
    exit 0
fi

# Block on post-/review boundary halt: review ran but Step 6 sentinel not yet written.
# review-round-summary.md is written by /review on completion; .review-boundary-passed
# is written by the orchestrator at the start of Step 6 (issue #1862).
if [[ -f "$IMPLEMENT_TMPDIR/review-round-summary.md" ]] && \
   [[ ! -f "$IMPLEMENT_TMPDIR/.review-boundary-passed" ]]; then
    REASON=$'You halted mid-Step-5 (post-/review boundary).\n\nNEXT REQUIRED: execute the Cross-Skill Health Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb in order per skills/implement/SKILL.md Step 5 post-/review directives, then touch .review-boundary-passed inside the active /implement tmpdir ('"$TMPDIR_BASENAME"$') to release this guard.\n\nOperator escape: hard-quit the session, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run.'
    if command -v jq >/dev/null 2>&1; then
        jq -cn --arg r "$REASON" '{decision:"block",reason:$r}' \
            || printf '%s\n' '{"decision":"block","reason":"You halted mid-Step-5 (post-/review boundary). Execute Cross-Skill Health Propagation + Step 6 breadcrumb, then touch .review-boundary-passed inside the active /implement tmpdir."}'
    else
        printf '%s\n' '{"decision":"block","reason":"You halted mid-Step-5 (post-/review boundary). Execute Cross-Skill Health Propagation + Step 6 breadcrumb, then touch .review-boundary-passed inside the active /implement tmpdir."}'
    fi
    exit 0
fi

exit 0
