#!/usr/bin/env bash
# step-16.sh — /implement Step 16 telemetry and rejected-findings report.

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

read_state_key() {
    local file=$1 key=$2 default_value=$3 line
    if [ -f "$file" ]; then
        line=$(grep "^${key}=" "$file" 2>/dev/null | tail -n 1 || true)
        if [ -n "$line" ]; then
            printf '%s\n' "${line#*=}"
            return 0
        fi
    fi
    printf '%s\n' "$default_value"
}

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

rehydrate_plugin_root
run_id=$(read_session_key LARCH_RUN_ID "${RUN_ID:-}")
if [ -z "$run_id" ]; then
    run_id=$(read_state_key "$IMPLEMENT_TMPDIR/ship-pr-state.sh" RUN_ID "")
fi
if [ -z "$run_id" ]; then
    run_id=$(read_state_key "$IMPLEMENT_TMPDIR/finalize-state.sh" RUN_ID "")
fi
"$CLAUDE_PLUGIN_ROOT/scripts/step-telemetry-mark.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 16 — rejected findings" || true
"$CLAUDE_PLUGIN_ROOT/skills/implement/scripts/write-rejected-findings.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR" --run-id "$run_id" --log-root "$IMPLEMENT_TMPDIR/larch-logs" || true
