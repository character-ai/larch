#!/usr/bin/env bash
# hook-post-design.sh — PostToolUse hook for post-/design boundary breadcrumbs.
#
# set -e omitted: every probe must fail open; the hook must not block tool
# completion. Intentional per .claude/rules/shell-strict-mode.md.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

SKILL=$(printf '%s' "$INPUT" | jq -r '
    if (.tool_name // "") == "Skill" then
        (.tool_input.skill // .tool_input.skill_name // "")
    else "" end' 2>/dev/null) || exit 0
case "$SKILL" in
    design|larch:design) ;;
    *) exit 0 ;;
esac

HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || HOOK_CWD=""

# Surface the active Claude Code session_id (passed by Claude Code in every
# hook event payload) into LARCH_TOKEN_SESSION_ID so the resolver's
# session-id binding branch is reachable in production. Without this,
# `/implement` Step 0's in-bash export does not propagate to hook
# subprocesses, leaving the resolver on the TTL-only fallback path. Empty
# / missing / null session_id falls through to TTL — the resolver treats
# unset LARCH_TOKEN_SESSION_ID as "no session signal available".
SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || SID=""
[[ -n "$SID" ]] && export LARCH_TOKEN_SESSION_ID="$SID"

# shellcheck source=lib-resolve-implement-tmpdir.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-resolve-implement-tmpdir.sh"

IMPLEMENT_TMPDIR=$(resolve_implement_tmpdir "$HOOK_CWD")
[[ -n "$IMPLEMENT_TMPDIR" ]] || exit 0

DESIGN_ONLY=false
DO_FILE="$IMPLEMENT_TMPDIR/.design-only"
if [[ -f "$DO_FILE" ]]; then
    DO_VAL=$(head -n1 "$DO_FILE" 2>/dev/null | tr -d '[:space:]')
    [[ "$DO_VAL" = "true" ]] && DESIGN_ONLY=true
fi

TMPOUT=$(mktemp 2>/dev/null) || exit 0
trap 'rm -f "$TMPOUT"' EXIT

if ! "$PLUGIN_ROOT/skills/implement/scripts/post-design-boundary.sh" \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --session-env "$IMPLEMENT_TMPDIR/session-env.sh" \
    --design-only "$DESIGN_ONLY" \
    > "$TMPOUT" 2>/dev/null; then
    exit 0
fi

jq -cn --rawfile ctx "$TMPOUT" \
    '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}' \
    || exit 0

exit 0
