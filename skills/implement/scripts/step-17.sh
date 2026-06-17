#!/usr/bin/env bash
# step-17.sh — /implement Step 17 telemetry and final report render.

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

NO_PRINT_STDOUT=false
while [ $# -gt 0 ]; do
    case "$1" in
        --no-print-stdout) NO_PRINT_STDOUT=true; shift ;;
        --help)
            printf '%s\n' 'Usage: step-17.sh [--no-print-stdout]'
            exit 0
            ;;
        *)
            printf 'step-17.sh: unknown option: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done
summary_path="$IMPLEMENT_TMPDIR/summary-final.md"

append_step17_failure() {
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "Step 17 — final report" \
        --tool "python/cli.py final-report write" \
        --exit-code "$1" \
        --category "Tool Failures" \
        --output-file "$_step17_wfr_log" \
        --redact >/dev/null 2>&1 || true
}

rehydrate_plugin_root
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 17 — final report" || true
_step17_wfr_log="$IMPLEMENT_TMPDIR/step17-write-final-report.failure.log"
: >"$_step17_wfr_log" 2>/dev/null || true
if [ "$NO_PRINT_STDOUT" = true ]; then
    summary_backup=""
    if [ -f "$summary_path" ]; then
        summary_backup="$IMPLEMENT_TMPDIR/.summary-final.pre-step17.bak"
        mv "$summary_path" "$summary_backup"
    fi
    set +e
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" final-report write --implement-tmpdir "$IMPLEMENT_TMPDIR" >"$_step17_wfr_log" 2>&1
    _step17_wfr_rc=$?
    set -e
    if [ "$_step17_wfr_rc" -eq 0 ]; then
        rm -f "$summary_backup"
        exit 0
    fi
    append_step17_failure "$_step17_wfr_rc"
    if [ -s "$summary_path" ]; then
        rm -f "$summary_backup"
        exit 0
    fi
    if [ -n "$summary_backup" ] && [ -f "$summary_backup" ]; then
        mv "$summary_backup" "$summary_path"
    fi
    exit "$_step17_wfr_rc"
fi

set +e
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" final-report write --implement-tmpdir "$IMPLEMENT_TMPDIR" --print-stdout >"$_step17_wfr_log" 2>&1
_step17_wfr_rc=$?
set -e
if [ "$_step17_wfr_rc" -eq 0 ]; then
  cat "$_step17_wfr_log"
  if [ -s "$summary_path" ]; then
    touch "$IMPLEMENT_TMPDIR/.step17-printed"
  fi
else
  append_step17_failure "$_step17_wfr_rc"
fi
