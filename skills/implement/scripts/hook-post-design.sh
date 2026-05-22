#!/usr/bin/env bash
# hook-post-design.sh — PostToolUse hook after /design Skill tool use.
#
# Issue #2485: post-design-boundary dispatch was retired. This hook retains
# only the session-id export for tmpdir resolution; it does not inject
# hookSpecificOutput or invoke post-design-boundary.sh.
#
# set -e omitted: every probe must fail open; the hook must not block tool
# completion. Intentional per .claude/rules/shell-strict-mode.md.

set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

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

SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || SID=""
[[ -n "$SID" ]] && export LARCH_TOKEN_SESSION_ID="$SID"

# shellcheck source=lib-resolve-implement-tmpdir.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-resolve-implement-tmpdir.sh"
IMPLEMENT_TMPDIR=$(resolve_implement_tmpdir "$HOOK_CWD")
[[ -n "$IMPLEMENT_TMPDIR" ]] || exit 0

emit_breadcrumb "ℹ hook-post-design: boundary injection retired (#2485); LARCH_TOKEN_SESSION_ID export retained."

exit 0
