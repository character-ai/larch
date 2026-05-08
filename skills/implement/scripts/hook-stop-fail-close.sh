#!/usr/bin/env bash
# hook-stop-fail-close.sh — Stop hook for post-/design halt protection.
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

# shellcheck source=lib-resolve-implement-tmpdir.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-resolve-implement-tmpdir.sh"

IMPLEMENT_TMPDIR=$(resolve_implement_tmpdir "$HOOK_CWD")
[[ -n "$IMPLEMENT_TMPDIR" ]] || exit 0

[[ -f "$IMPLEMENT_TMPDIR/design-export/manifest.env" ]] || exit 0
[[ ! -f "$IMPLEMENT_TMPDIR/.boundary-gate-passed" ]] || exit 0
[[ ! -f "$IMPLEMENT_TMPDIR/.run-cleaned-up" ]] || exit 0

TMPDIR_BASENAME=$(basename "$IMPLEMENT_TMPDIR" 2>/dev/null) \
    || TMPDIR_BASENAME="<implement-tmpdir>"
REASON=$'You halted mid-Step-1 (post-/design boundary).\n\nNEXT REQUIRED: run skills/implement/scripts/post-design-boundary.sh against the active /implement tmpdir ('"$TMPDIR_BASENAME"$'). If it emits POST_DESIGN_BOUNDARY_OK=true, continue per its terminal directive. If it emits MANIFEST_FAILED=true, bail to /implement Step 18 cleanup.\n\nOperator escape: hard-quit the session, OR remove the stale tmpdir manifest manually, OR touch .run-cleaned-up inside the active /implement tmpdir to intentionally abandon the run.'

if command -v jq >/dev/null 2>&1; then
    jq -cn --arg r "$REASON" '{decision:"block",reason:$r}' \
        || printf '%s\n' '{"decision":"block","reason":"You halted mid-Step-1 (post-/design boundary). Run post-design-boundary.sh against the active /implement tmpdir; continue per its terminal directive."}'
else
    printf '%s\n' '{"decision":"block","reason":"You halted mid-Step-1 (post-/design boundary). Run post-design-boundary.sh against the active /implement tmpdir; continue per its terminal directive."}'
fi

exit 0
