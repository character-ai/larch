#!/usr/bin/env bash
# step-18b-final-report.sh — Step 18b token refresh, final report render, and EMIT_BODY decision.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "step-18b-final-report.sh: usage: $0 --implement-tmpdir <path>"
}

die_argv() {
    larch_err "step-18b-final-report.sh: $*"
    exit 1
}

kv_value() {
    local key=$1 file=$2
    awk -F= -v key="$key" '$1==key{print substr($0, index($0, "=") + 1); exit}' "$file" 2>/dev/null
}

append_failure_best_effort() {
    local site=$1 tool=$2 rc=$3 log=$4
    [ -f "$log" ] || : >"$log" 2>/dev/null || true
    python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$rc" \
        --category "Tool Failures" \
        --output-file "$log" \
        --redact >/dev/null 2>&1 || true
}

main() {
    local tmpdir=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --implement-tmpdir) [ $# -ge 2 ] || die_argv "--implement-tmpdir requires a value"; tmpdir=$2; shift 2 ;;
            *) die_argv "unknown option: $1" ;;
        esac
    done
    [ -n "$tmpdir" ] || die_argv "--implement-tmpdir is required"
    [ -d "$tmpdir" ] || die_argv "--implement-tmpdir must exist"
    IMPLEMENT_TMPDIR=$tmpdir
    export IMPLEMENT_TMPDIR

    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$tmpdir/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$tmpdir/plugin-root.env"
        PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}"
    fi

    "$SCRIPT_DIR/cleanup.sh" --help >/dev/null 2>&1 || true
    python3 "$PLUGIN_ROOT/python/cli.py" timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 18 — cleanup" || true

    local session_env="$tmpdir/session-env.sh"
    if [ -f "$session_env" ]; then
        LARCH_TOKEN_SESSION_ID=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$session_env" --key LARCH_TOKEN_SESSION_ID --default "" 2>/dev/null || true)
        LARCH_CLAUDE_SOURCE_FILE=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$session_env" --key LARCH_CLAUDE_SOURCE_FILE --default "" 2>/dev/null || true)
        LARCH_TIMING_LEDGER=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$session_env" --key LARCH_TIMING_LEDGER --default "" 2>/dev/null || true)
        export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
    fi

    local emit_body=false step17_present=false snapshot_ok="" wfr_rc=0
    local token_fail_log="$tmpdir/step18-token-report.failure.log"
    local wfr_fail_log="$tmpdir/step18-write-final-report.failure.log"
    [ -f "$tmpdir/.step17-emitted" ] && step17_present=true
    if [ ! -f "$tmpdir/.step17-emitted" ]; then
        emit_body=true
    fi

    : >"$token_fail_log" 2>/dev/null || true
    local token_rc=0
    if python3 "$PLUGIN_ROOT/python/cli.py" token report --full --format json --output "$tmpdir/token-report-rendered.json" >>"$token_fail_log" 2>&1; then
        :
    else
        token_rc=$?
        append_failure_best_effort "Step 18 — cleanup" "python3 python/cli.py token report" "$token_rc" "$token_fail_log"
    fi

    if [ -f "$tmpdir/summary-final.md" ]; then
        if cp "$tmpdir/summary-final.md" "$tmpdir/.step18-prebody" 2>/dev/null; then
            snapshot_ok=true
        else
            rm -f "$tmpdir/.step18-prebody"
            snapshot_ok=false
        fi
    else
        rm -f "$tmpdir/.step18-prebody"
        snapshot_ok=absent
    fi

    : >"$wfr_fail_log" 2>/dev/null || true
    step18b_out="$tmpdir/step18b-final-report.stdout"
    if python3 "$PLUGIN_ROOT/python/cli.py" final-report step18b --implement-tmpdir "$tmpdir" >"$step18b_out" 2>>"$wfr_fail_log"; then
        wfr_rc=0
    else
        wfr_rc=$?
        append_failure_best_effort "Step 18 — cleanup" "python/cli.py final-report step18b" "$wfr_rc" "$wfr_fail_log"
    fi
    wfr_rc=$(kv_value WFR_RC "$step18b_out")
    wfr_rc=${wfr_rc:-1}
    emit_body=$(kv_value EMIT_BODY "$step18b_out")
    snapshot_ok=$(kv_value SNAPSHOT_OK "$step18b_out")
    snapshot_ok=${snapshot_ok:-absent}
    step17_present=false
  case "$(kv_value STEP17_EMITTED_PRESENT "$step18b_out")" in
        true) step17_present=true ;;
    esac

    local emit_body_kv=false
    if [ "$emit_body" = true ]; then
        emit_body_kv=true
    fi

    emit_kv EMIT_BODY "$emit_body_kv"
    emit_kv WFR_RC "$wfr_rc"
    emit_kv STEP17_EMITTED_PRESENT "$step17_present"
    emit_kv SNAPSHOT_OK "$snapshot_ok"
}

main "$@"
