#!/usr/bin/env bash
# PreToolUse hook shim: deny Bash run_in_background launches while a larch bgjob
# is active in this clone. The policy lives in Rust
# (`larch hook deny-run-in-background`, crates/larch-cli/src/hook_commands.rs);
# this shim is only the fail-CLOSED fallback for when the larch binary is
# unavailable. It never bootstraps an install (LARCH_BOOTSTRAP_NO_INSTALL=1) so
# it always returns inside the hook timeout.
#
# Stdin: the Bash PreToolUse JSON. Always exits 0. To deny, emits the PreToolUse
# deny envelope on stdout; to allow, emits nothing. set -e intentionally
# omitted: a hook must always emit a decision, never abort.
set -uo pipefail

STATIC_DENY='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"run_in_background denied: larch binary unavailable"}}'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)" || { printf '%s\n' "$STATIC_DENY"; exit 0; }
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd -P)" || PLUGIN_ROOT=""
if [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
fi
if [ -z "$PLUGIN_ROOT" ] || [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ]; then
    printf '%s\n' "$STATIC_DENY"
    exit 0
fi

if ! LARCH_BOOTSTRAP_NO_INSTALL=1 "$PLUGIN_ROOT/scripts/larch.sh" hook deny-run-in-background 2>/dev/null; then
    printf '%s\n' "$STATIC_DENY"
fi
exit 0
