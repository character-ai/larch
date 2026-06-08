#!/usr/bin/env bash
# status.sh — larch version and vendor health status check.
#
# Outputs (KEY=value on stdout via emit_kv):
#   LARCH_PLUGIN_VERSION=<value>   Current larch plugin version.
#   CODEX_BINARY_FOUND=true|false  Whether the codex binary is on PATH.
#   CURSOR_BINARY_FOUND=true|false Whether the cursor binary is on PATH.
#   CODEX_PRESENT=true|false       Codex binary found AND runtime probe passed.
#   CURSOR_PRESENT=true|false      Cursor binary found AND runtime probe passed.
#   CODEX_STATE=ok|binary-missing|probe-failed
#   CURSOR_STATE=ok|binary-missing|probe-failed
#   DEGRADED=true|false            Whether any vendor is unavailable.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

# Read plugin version (best-effort; always emits a value)
LARCH_PLUGIN_VERSION="unknown"
_ver_out=$("$PLUGIN_ROOT/scripts/read-plugin-version.sh" 2>/dev/null || true)
if [ -n "$_ver_out" ]; then
    _v=$(printf '%s\n' "$_ver_out" | awk -F= '/^LARCH_PLUGIN_VERSION=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && LARCH_PLUGIN_VERSION="$_v"
fi

# Run reviewer health probes (same machinery as /implement Step 0)
CODEX_BINARY_FOUND=false
CURSOR_BINARY_FOUND=false
CODEX_PRESENT=false
CURSOR_PRESENT=false
_check_out=$("$PLUGIN_ROOT/scripts/check-reviewers.sh" 2>/dev/null || true)
if [ -n "$_check_out" ]; then
    _v=$(printf '%s\n' "$_check_out" | awk -F= '/^CODEX_BINARY_FOUND=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && CODEX_BINARY_FOUND="$_v"
    _v=$(printf '%s\n' "$_check_out" | awk -F= '/^CURSOR_BINARY_FOUND=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && CURSOR_BINARY_FOUND="$_v"
    _v=$(printf '%s\n' "$_check_out" | awk -F= '/^CODEX_PRESENT=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && CODEX_PRESENT="$_v"
    _v=$(printf '%s\n' "$_check_out" | awk -F= '/^CURSOR_PRESENT=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && CURSOR_PRESENT="$_v"
fi

# Interpret results using degraded-tools-gate.sh (same gate as /implement Step 0)
CODEX_STATE=unknown
CURSOR_STATE=unknown
DEGRADED=false
_gate_out=$("$PLUGIN_ROOT/scripts/degraded-tools-gate.sh" \
    --codex-binary-found "$CODEX_BINARY_FOUND" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-binary-found "$CURSOR_BINARY_FOUND" \
    --cursor-present "$CURSOR_PRESENT" \
    --skill status 2>/dev/null || true)
if [ -n "$_gate_out" ]; then
    _v=$(printf '%s\n' "$_gate_out" | awk -F= '/^CODEX_STATE=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && CODEX_STATE="$_v"
    _v=$(printf '%s\n' "$_gate_out" | awk -F= '/^CURSOR_STATE=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && CURSOR_STATE="$_v"
    _v=$(printf '%s\n' "$_gate_out" | awk -F= '/^DEGRADED=/{print substr($0, index($0,"=")+1); exit}')
    [ -n "$_v" ] && DEGRADED="$_v"
fi

emit_kv LARCH_PLUGIN_VERSION "$LARCH_PLUGIN_VERSION"
emit_kv CODEX_BINARY_FOUND   "$CODEX_BINARY_FOUND"
emit_kv CURSOR_BINARY_FOUND  "$CURSOR_BINARY_FOUND"
emit_kv CODEX_PRESENT        "$CODEX_PRESENT"
emit_kv CURSOR_PRESENT       "$CURSOR_PRESENT"
emit_kv CODEX_STATE          "$CODEX_STATE"
emit_kv CURSOR_STATE         "$CURSOR_STATE"
emit_kv DEGRADED             "$DEGRADED"
