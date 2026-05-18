#!/usr/bin/env bash
# hook-post-bump-version.sh — PostToolUse hook for post-/bump-version boundary.
#
# Injects a continuation directive into the assistant's next-turn context when
# /bump-version's Skill tool returns AND the orchestrator has not yet completed
# the post-verification chain (sentinel: $IMPLEMENT_TMPDIR/postbump-state.sh).
# Catches the turn-boundary halt described in issue #2338, where the orchestrator
# ends the turn on `APPLIED=true COMMIT_SHA=<sha>` instead of immediately invoking
# `check-bump-version.sh --mode post --before-count $COMMITS_BEFORE` as the
# Rebase + Re-bump Sub-procedure step 4 requires. Parallel mechanical pattern to
# hook-post-design.sh; the Stop-hook block in hook-stop-fail-close.sh remains the
# session-stop safety net.
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
    bump-version|larch:bump-version) ;;
    *) exit 0 ;;
esac

HOOK_CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || HOOK_CWD=""

# Surface the active Claude Code session_id (parallels hook-post-design.sh) so
# the tmpdir resolver's session-id binding branch is reachable in production.
SID=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || SID=""
[[ -n "$SID" ]] && export LARCH_TOKEN_SESSION_ID="$SID"

# shellcheck source=lib-resolve-implement-tmpdir.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-resolve-implement-tmpdir.sh"

IMPLEMENT_TMPDIR=$(resolve_implement_tmpdir "$HOOK_CWD")
[[ -n "$IMPLEMENT_TMPDIR" ]] || exit 0

# Fire only when check-bump-version.sh --mode pre armed us (sub-procedure step 4)
# AND the orchestrator's post-bump continuation hasn't yet completed
# (postbump-state.sh is the "post-verification chain done" sentinel, parallel to
# the Stop-hook block in hook-stop-fail-close.sh).
[[ -f "$IMPLEMENT_TMPDIR/.bump-version-armed" ]] || exit 0
[[ ! -f "$IMPLEMENT_TMPDIR/postbump-state.sh" ]] || exit 0

read -r -d '' DIRECTIVE <<'EOF' || true
➡️ /bump-version returned (APPLIED=true COMMIT_SHA=<sha>). The Rebase + Re-bump Sub-procedure (or Step 8 continuation) is NOT complete. NEXT REQUIRED: invoke check-bump-version.sh --mode post --before-count <value> as the FIRST permitted Bash tool call, substituting <value> with the COMMITS_BEFORE numeric value you parsed from the earlier check-bump-version.sh --mode pre stdout (do NOT pass the literal string $COMMITS_BEFORE). Do NOT end the turn, do NOT echo APPLIED/COMMIT_SHA, do NOT write a recap. APPLIED=true COMMIT_SHA=<sha> in the tool result is NOT a run-completion signal. See skills/implement/references/rebase-rebump-subprocedure.md "Continue after child returns" and skills/implement/SKILL.md NEVER #15.
EOF
DIRECTIVE="${DIRECTIVE%$'\n'}"

HOOK_OUTPUT=$(jq -cn --arg ctx "$DIRECTIVE" \
    '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}' \
    2>/dev/null) || exit 0
emit "$HOOK_OUTPUT"

exit 0
