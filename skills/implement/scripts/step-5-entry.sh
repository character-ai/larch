#!/usr/bin/env bash
# step-5-entry.sh — /implement Step 5 entry telemetry and review caps.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
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
"$CLAUDE_PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 5 — code review" || true
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" "$CLAUDE_PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 5 — code review" || true
dynamic_archetypes_cap=""
if [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
  dynamic_archetypes_cap=$(awk 'BEGIN{p="LARCH_DYNAMIC_ARCHETYPES_MAX="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
fi
if [ -z "$dynamic_archetypes_cap" ] && [ -n "${LARCH_DYNAMIC_ARCHETYPES_MAX:-}" ]; then
  dynamic_archetypes_cap="$LARCH_DYNAMIC_ARCHETYPES_MAX"
fi
[ -n "$dynamic_archetypes_cap" ] || dynamic_archetypes_cap=3
case "$dynamic_archetypes_cap" in [0-3]) ;; *) printf 'ERROR: Step 5 banner dynamic_archetypes_cap is non-integer or out of range: %s
' "$dynamic_archetypes_cap" >&2; exit 2 ;; esac
round_cap=5
printf 'DYNAMIC_ARCHETYPES_CAP=%s
' "$dynamic_archetypes_cap"
printf 'ROUND_CAP=%s
' "$round_cap"
