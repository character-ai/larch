#!/usr/bin/env bash
# step-2-entry.sh — /implement Step 2 token/timing entry marks.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
CODER=""
while [ $# -gt 0 ]; do
    case "$1" in
        --coder) [ $# -ge 2 ] || exit 2; CODER=$2; shift 2 ;;
        --help) printf '%s
' 'Usage: step-2-entry.sh --coder claude|codex|cursor'; exit 0 ;;
        *) printf '%s
' "step-2-entry.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

rehydrate_plugin_root
rehydrate_larch_triplet
CODEX_PRESENT=$(read_session_key CODEX_PRESENT false)
CURSOR_PRESENT=$(read_session_key CURSOR_PRESENT false)
case "$CODER" in
  claude) "$CLAUDE_PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 2 — implementation" || true ;;
  codex) [ "$CODEX_PRESENT" = true ] || "$CLAUDE_PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 2 — implementation" || true ;;
  cursor) [ "$CURSOR_PRESENT" = true ] || "$CLAUDE_PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 2 — implementation" || true ;;
esac
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement "$CLAUDE_PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 2 — implementation" || true
