#!/usr/bin/env bash
# step-18.sh — /implement Step 18 two-phase stall gate and finalizer.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
PHASE=gate
STALL_TRACKING_MEMORY_ARG=""
STEP17_EMITTED=false

usage() {
    cat <<'USAGE'
Usage: step-18.sh [--phase gate|finalize] [--stall-tracking-memory true|false] [--step17-emitted true|false]

Phases:
  gate      Emit four stall-tracking layers and STALL_RECOVERY_REQUIRED.
  --phase finalize  Run final-report step18b, optional summary markers, closing marks, restore-finalize-state, and teardown.
USAGE
}

die_argv() {
    printf 'step-18.sh: %s\n' "$*" >&2
    exit 2
}

while [ $# -gt 0 ]; do
    case "$1" in
        --phase)
            [ $# -ge 2 ] || die_argv "--phase requires a value"
            PHASE=$2
            shift 2
            ;;
        --stall-tracking-memory)
            [ $# -ge 2 ] || die_argv "--stall-tracking-memory requires a value"
            STALL_TRACKING_MEMORY_ARG=$2
            shift 2
            ;;
        --step17-emitted)
            [ $# -ge 2 ] || die_argv "--step17-emitted requires a value"
            STEP17_EMITTED=$2
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            die_argv "unknown argument: $1"
            ;;
    esac
done

case "$PHASE" in
    gate|finalize) ;;
    *) die_argv "--phase must be gate or finalize" ;;
esac
case "$STEP17_EMITTED" in
    true|false) ;;
    *) die_argv "--step17-emitted must be true or false" ;;
esac

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
    if [ ! -d "$CLAUDE_PLUGIN_ROOT" ]; then
        printf 'step-18.sh: CLAUDE_PLUGIN_ROOT not found: %s\n' "$CLAUDE_PLUGIN_ROOT" >&2
        exit 2
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

read_key_from_file() {
    local file=$1 key=$2 default_value=$3
    if [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

rehydrate_larch_triplet() {
    RUN_ID=$(read_session_key LARCH_RUN_ID "${RUN_ID:-}")
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export RUN_ID LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

_stall_layer_active() {
    [ -n "$1" ] && [ "$1" != "false" ]
}

kv_value() {
    local key=$1 file=$2
    awk -F= -v key="$key" '$1==key{print substr($0, index($0, "=") + 1); exit}' "$file" 2>/dev/null
}

append_failure_best_effort() {
    local site=$1 tool=$2 rc=$3 log=$4
    [ -f "$log" ] || : >"$log" 2>/dev/null || true
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$rc" \
        --category "Tool Failures" \
        --output-file "$log" \
        --redact >/dev/null 2>&1 || true
}

print_summary_markers() {
    summary_path="$IMPLEMENT_TMPDIR/summary-final.md"
    printf '%s\n' '---LARCH-SUMMARY-FINAL-BEGIN---'
    if ! cat "$summary_path"; then
        return 1
    fi
    last_hex=$(tail -c 1 "$summary_path" 2>/dev/null | od -An -t x1 | tr -d ' \n')
    if [ "$last_hex" != "0a" ]; then
        printf '\n'
    fi
    printf '%s\n' '---LARCH-SUMMARY-FINAL-END---'
    touch "$IMPLEMENT_TMPDIR/.step17-emitted"
}

run_gate() {
    local _stall_memory _stall_disk _stall_finalize _stall_session
    _stall_disk=false
    _stall_finalize=false
    _stall_session=false
    _stall_disk=$(read_key_from_file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" STALL_TRACKING "false")
    _stall_finalize=$(read_key_from_file "$IMPLEMENT_TMPDIR/finalize-state.sh" STALL_TRACKING "false")
    _stall_session=$(read_key_from_file "$IMPLEMENT_TMPDIR/session-env.sh" STALL_TRACKING "false")
    _stall_memory=false
    case "$STALL_TRACKING_MEMORY_ARG" in
        true|false) _stall_memory="$STALL_TRACKING_MEMORY_ARG" ;;
        "") _stall_memory="${STALL_TRACKING:-false}" ;;
        *) _stall_memory="$STALL_TRACKING_MEMORY_ARG" ;;
    esac
    printf 'STALL_TRACKING_MEMORY=%s\n' "$_stall_memory"
    printf 'STALL_TRACKING_DISK=%s\n' "$_stall_disk"
    printf 'STALL_TRACKING_FINALIZE=%s\n' "$_stall_finalize"
    printf 'STALL_TRACKING_SESSION=%s\n' "$_stall_session"
    if _stall_layer_active "$_stall_memory" || _stall_layer_active "$_stall_disk" || _stall_layer_active "$_stall_finalize" || _stall_layer_active "$_stall_session"; then
        printf 'STALL_RECOVERY_REQUIRED=true\n'
        exit 0
    fi
    printf 'STALL_RECOVERY_REQUIRED=false\n'
    printf '%s\n' '⏩ 18a: stall recovery — no stall detected'
}

run_finalize() {
    local step18b_out step18b_err step18b_rc emit_body wfr_rc step17_present snapshot_ok marker_rc capture_out capture_rc
    if [ "$STEP17_EMITTED" = true ]; then
        touch "$IMPLEMENT_TMPDIR/.step17-emitted"
    fi

    step18b_out="$IMPLEMENT_TMPDIR/step18b-final-report.stdout"
    step18b_err="$IMPLEMENT_TMPDIR/step18b-final-report.stderr"
    : >"$step18b_err" 2>/dev/null || true
    set +e
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" final-report step18b --implement-tmpdir "$IMPLEMENT_TMPDIR" >"$step18b_out" 2>"$step18b_err"
    step18b_rc=$?
    set -e

    emit_body=$(kv_value EMIT_BODY "$step18b_out")
    emit_body=${emit_body:-false}
    wfr_rc=$(kv_value WFR_RC "$step18b_out")
    if [ -z "$wfr_rc" ]; then
        wfr_rc=$step18b_rc
    fi
    step17_present=$(kv_value STEP17_EMITTED_PRESENT "$step18b_out")
    step17_present=${step17_present:-false}
    snapshot_ok=$(kv_value SNAPSHOT_OK "$step18b_out")
    snapshot_ok=${snapshot_ok:-absent}
    if [ "$step18b_rc" -ne 0 ]; then
        append_failure_best_effort "Step 18b — final-report" "python/cli.py final-report step18b" "$step18b_rc" "$step18b_err"
    fi

    printf 'EMIT_BODY=%s\n' "$emit_body"
    printf 'WFR_RC=%s\n' "$wfr_rc"
    printf 'STEP17_EMITTED_PRESENT=%s\n' "$step17_present"
    printf 'SNAPSHOT_OK=%s\n' "$snapshot_ok"

    if [ "$emit_body" = true ] && [ "$wfr_rc" = 0 ] && [ -s "$IMPLEMENT_TMPDIR/summary-final.md" ]; then
        set +e
        print_summary_markers
        marker_rc=$?
        set -e
        if [ "$marker_rc" -ne 0 ]; then
            :
        fi
    fi

    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" token report --since-last-mark --terse > /dev/null || true
    DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing report --since-last-mark --terse > /dev/null || true
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" token mark "Step 18 — done" || true
    DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing mark "Step 18 — done" || true
    if [ -n "${RUN_ID:-}" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" execution-issues flush-safety-net \
            --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
            --run-id "$RUN_ID" \
            --issue-log "$IMPLEMENT_TMPDIR/execution-issues.md" >/dev/null 2>&1 || true
        if [ -n "${LARCH_CLAUDE_SOURCE_FILE:-}" ] && [ ! -f "$IMPLEMENT_TMPDIR/.completed/step-7a-terminal" ]; then
            set +e
            capture_out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log capture-transcript \
                --source-file "$LARCH_CLAUDE_SOURCE_FILE" \
                --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
                --skill implement \
                --run-id "$RUN_ID" \
                --defer-commit true \
                --execution-issues-log "$IMPLEMENT_TMPDIR/execution-issues.md" \
                --warning-step-label "18" 2>/dev/null)
            capture_rc=$?
            set -e
            printf '%s\n' "$capture_out" | awk 'index($0,"SESSION_TRANSCRIPT_STATUS=")==1{print}'
            : "$capture_rc"
        fi
    fi
    _restore_finalize=false
    if [ -f "$IMPLEMENT_TMPDIR/ship-pr-state.sh" ]; then
      if [ ! -f "$IMPLEMENT_TMPDIR/finalize-state.sh" ]; then
        _restore_finalize=true
      else
        _ship_stall=$(read_key_from_file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" STALL_TRACKING "false")
        _ship_bail=$(read_key_from_file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" BAIL_NEEDS_USER_INPUT "false")
        _ship_step=$(read_key_from_file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" STALL_STEP "")
        _final_step=$(read_key_from_file "$IMPLEMENT_TMPDIR/finalize-state.sh" STALL_STEP "")
        _ship_stall_truthy=false
        _ship_bail_truthy=false
        case "$_ship_stall" in 1|true|TRUE|True|yes|YES|Yes|on|ON|On) _ship_stall_truthy=true ;; esac
        case "$_ship_bail" in 1|true|TRUE|True|yes|YES|Yes|on|ON|On) _ship_bail_truthy=true ;; esac
        if [ "$_ship_stall_truthy" = true ] || [ "$_ship_bail_truthy" = true ] || { [ -n "$_ship_step" ] && [ "$_ship_step" != "$_final_step" ]; }; then
          _restore_finalize=true
        fi
      fi
    fi
    if [ "$_restore_finalize" = true ]; then
      if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session restore-finalize-state --implement-tmpdir "$IMPLEMENT_TMPDIR"; then
        printf '%s\n' "**⚠ Step 18: restore-finalize-state.sh failed; proceeding to teardown.**" >&2
      fi
    fi
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session clear-implement-pointer --claude-pid "${LARCH_CLAUDE_PID:-$PPID}" 2>/dev/null || true
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement-finalize teardown --state-file "$IMPLEMENT_TMPDIR/finalize-state.sh" --implement-tmpdir "$IMPLEMENT_TMPDIR"
}

rehydrate_plugin_root
rehydrate_larch_triplet
case "$PHASE" in
    gate) run_gate ;;
    finalize) run_finalize ;;
esac
