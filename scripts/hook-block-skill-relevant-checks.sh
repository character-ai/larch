#!/usr/bin/env bash
# Block /relevant-checks Skill calls inside active /implement or /review runs.

set -euo pipefail
LC_ALL=C

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REASON="/relevant-checks Skill invocation is not allowed inside an active /implement or /review run; call run-relevant-checks-captured.sh instead. See scripts/run-relevant-checks-captured.md."

deny() {
    jq -cn --arg reason "$REASON" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: $reason
        }
    }' || printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"/relevant-checks Skill invocation is not allowed inside an active /implement or /review run; call run-relevant-checks-captured.sh instead. See scripts/run-relevant-checks-captured.md."}}'
    exit 0
}

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

INPUT=$(cat) || exit 0
tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || exit 0
if [[ "$tool_name" != "Skill" ]]; then
    exit 0
fi

skill_name=$(printf '%s' "$INPUT" | jq -r '[.tool_input.skill, .tool_input.skill_name] | map(select(type == "string" and length > 0)) | .[0] // empty' 2>/dev/null) || exit 0
case "$skill_name" in
    relevant-checks|larch:relevant-checks) ;;
    *) exit 0 ;;
esac

resolved=$(printf '%s' "$INPUT" | "$SCRIPT_DIR/lib-resolve-active-larch-session.sh" 2>/dev/null || true)
if [[ -n "$resolved" ]]; then
    deny
fi

exit 0
