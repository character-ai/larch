#!/usr/bin/env bash
# step-18a-gate.sh — /implement Step 18a four-layer stall-tracking resolution KVs.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
STALL_TRACKING_MEMORY_ARG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --stall-tracking-memory) [ $# -ge 2 ] || { printf '%s\n' 'step-18a-gate.sh: --stall-tracking-memory requires a value' >&2; exit 2; }; STALL_TRACKING_MEMORY_ARG=$2; shift 2 ;;
        --help) printf '%s\n' 'Usage: step-18a-gate.sh [--stall-tracking-memory true|false]'; exit 0 ;;
        *) printf '%s\n' "step-18a-gate.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done

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
_stall_disk=false
_stall_finalize=false
_stall_session=false
if [ -f "$IMPLEMENT_TMPDIR/ship-pr-state.sh" ]; then
  _stall_disk=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" --key STALL_TRACKING --default "false")
fi
if [ -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then
  _stall_finalize=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/finalize-state.sh" --key STALL_TRACKING --default "false")
fi
if [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  _stall_session=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$IMPLEMENT_TMPDIR/session-env.sh" --key STALL_TRACKING --default "false")
fi
_stall_memory=false
case "$STALL_TRACKING_MEMORY_ARG" in
  true|false) _stall_memory="$STALL_TRACKING_MEMORY_ARG" ;;
  "") _stall_memory="${STALL_TRACKING:-false}" ;;
esac
printf 'STALL_TRACKING_MEMORY=%s
' "$_stall_memory"
printf 'STALL_TRACKING_DISK=%s
' "$_stall_disk"
printf 'STALL_TRACKING_FINALIZE=%s
' "$_stall_finalize"
printf 'STALL_TRACKING_SESSION=%s
' "$_stall_session"
