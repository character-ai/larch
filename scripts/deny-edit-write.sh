#!/usr/bin/env bash
# Fail-closed PreToolUse shim for the Rust token-scoped write guard.
# set -e is omitted so every delegation failure can emit the deny fallback.

set -uo pipefail

readonly FALLBACK_DENY='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"The active skill is read-only-repo -- Edit/Write/NotebookEdit outside /tmp or the larch session cache is not permitted."}}'

hook_emit() { printf '%s\n' "$1"; }

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)" || {
    hook_emit "$FALLBACK_DENY"
    exit 0
}
PLUGIN_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/.." 2>/dev/null && pwd -P)" || PLUGIN_ROOT=""
if [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ] && [ -n "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    PLUGIN_ROOT="$CLAUDE_PLUGIN_ROOT"
fi
if [ -z "$PLUGIN_ROOT" ] || [ ! -x "$PLUGIN_ROOT/scripts/larch.sh" ]; then
    hook_emit "$FALLBACK_DENY"
    exit 0
fi

OUTPUT="$(CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" LARCH_BOOTSTRAP_NO_INSTALL=1 \
    "$PLUGIN_ROOT/scripts/larch.sh" hook deny-edit-write "${1:-}" 2>/dev/null)"
RC=$?
if [ "$RC" -ne 0 ]; then
    hook_emit "$FALLBACK_DENY"
elif [ -n "$OUTPUT" ]; then
    hook_emit "$OUTPUT"
fi
exit 0
