#!/usr/bin/env bash
# PreToolUse hook shim: token-gated read-only-repo guard for Edit/Write/
# NotebookEdit. The policy lives in Rust (`larch hook deny-edit-write <token>`,
# crates/larch-cli/src/hook_commands.rs); this shim is only the fail-CLOSED
# fallback for when the larch binary is unavailable. It never bootstraps an
# install (LARCH_BOOTSTRAP_NO_INSTALL=1) so it always returns inside the hook
# timeout. The skill token is $1 and is forwarded to the verb.
#
# Stdin: JSON with tool_input.file_path or tool_input.notebook_path. Always
# exits 0. To deny, emits the PreToolUse deny envelope on stdout; to allow,
# emits nothing. set -e intentionally omitted: emit a decision, never abort.
set -uo pipefail

STATIC_DENY='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The active skill is read-only-repo -- Edit/Write/NotebookEdit outside /tmp or the larch session cache is not permitted."}}'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)" || { printf '%s\n' "$STATIC_DENY"; exit 0; }
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd -P)" || PLUGIN_ROOT=""
if [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
fi
if [ -z "$PLUGIN_ROOT" ] || [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ]; then
    printf '%s\n' "$STATIC_DENY"
    exit 0
fi

LARCH_BOOTSTRAP_NO_INSTALL=1 "$PLUGIN_ROOT/scripts/larch.sh" hook deny-edit-write "${1:-}" 2>/dev/null
if [ "$?" -ne 0 ]; then
    printf '%s\n' "$STATIC_DENY"
fi
exit 0
