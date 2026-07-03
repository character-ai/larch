#!/usr/bin/env bash
# run-step-checks.sh — rehydrate /implement telemetry env and run Python relevant checks.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
SITE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --site) [ $# -ge 2 ] || exit 2; SITE=$2; shift 2 ;;
        --help) printf '%s
' 'Usage: run-step-checks.sh --site SITE'; exit 0 ;;
        *) printf '%s
' "run-step-checks.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -n "$SITE" ] || { printf '%s
' 'run-step-checks.sh: --site is required' >&2; exit 2; }
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

# Write bg-wait marker for Step 3 (the site invoked with run_in_background: true) so
# hook-bg-poll-guard.sh can deny Monitor/TaskOutput/progress probes during the wait.
# Other sites (step5-review-fixes, step6, etc.) are composites; they manage their own
# marker lifecycle independently. Fail-open: a write failure must not abort the checks.
if [ "$SITE" = "step3" ]; then
  rm -f "$IMPLEMENT_TMPDIR/no-progress-turns.count" "$IMPLEMENT_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
  rm -f "$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-3-terminal.count" "$IMPLEMENT_TMPDIR/.completed/step-3-terminal" 2>/dev/null || true
  _step3_cleanup() {
    mkdir -p "$IMPLEMENT_TMPDIR/.completed" 2>/dev/null || true
    printf '' >"$IMPLEMENT_TMPDIR/.completed/step-3-terminal" 2>/dev/null || true
    rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
  }
  trap _step3_cleanup EXIT
  _step3_start=$(date +%s 2>/dev/null) || _step3_start=0
  case "$_step3_start" in ''|*[!0-9]*) _step3_start=0 ;; esac
  _step3_claude_pid="${LARCH_BG_POLL_GUARD_SESSION_PID:-${PPID:-}}"
  printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=implement-step3-checks\nTIMEOUT_S=10800\n' \
    "$$" "$_step3_claude_pid" "$_step3_start" >"$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
fi

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" checks run-relevant --site "$SITE" --tmpdir "$IMPLEMENT_TMPDIR"
