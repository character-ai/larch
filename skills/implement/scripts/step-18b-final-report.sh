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

append_failure_best_effort() {
    local site=$1 tool=$2 rc=$3 log=$4
    [ -f "$log" ] || : >"$log" 2>/dev/null || true
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
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

    local session_env="$tmpdir/session-env.sh"
    if [ -f "$session_env" ]; then
        LARCH_TOKEN_SESSION_ID=$("$PLUGIN_ROOT/scripts/read-session-env-key.sh" --file "$session_env" --key LARCH_TOKEN_SESSION_ID --default "")
        LARCH_CLAUDE_SOURCE_FILE=$("$PLUGIN_ROOT/scripts/read-session-env-key.sh" --file "$session_env" --key LARCH_CLAUDE_SOURCE_FILE --default "")
        LARCH_TIMING_LEDGER=$("$PLUGIN_ROOT/scripts/read-session-env-key.sh" --file "$session_env" --key LARCH_TIMING_LEDGER --default "")
        export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
    fi

    local emit_body=false step17_present=false wfr_rc=0 token_rc=0
    [ -f "$tmpdir/.step17-emitted" ] && step17_present=true
    if [ ! -f "$tmpdir/.step17-emitted" ]; then
        emit_body=true
    fi

    if ! "$PLUGIN_ROOT/scripts/token-report.sh" --full --format json --output "$tmpdir/token-report-rendered.json"; then
        token_rc=$?
        append_failure_best_effort "Step 18 — cleanup" "token-report.sh" "$token_rc" "$tmpdir/step18-token-report.failure.log"
    fi

    if [ -f "$tmpdir/summary-final.md" ]; then
        cp "$tmpdir/summary-final.md" "$tmpdir/.step18-prebody" 2>/dev/null || rm -f "$tmpdir/.step18-prebody"
    else
        rm -f "$tmpdir/.step18-prebody"
    fi

    if "$SCRIPT_DIR/write-final-report.sh" --implement-tmpdir "$tmpdir"; then
        wfr_rc=0
    else
        wfr_rc=$?
        append_failure_best_effort "Step 18 — cleanup" "write-final-report.sh" "$wfr_rc" "$tmpdir/step18-write-final-report.failure.log"
    fi

    if [ "$wfr_rc" -eq 0 ] && [ -s "$tmpdir/summary-final.md" ]; then
        if [ "$emit_body" = false ] && ! cmp -s "$tmpdir/.step18-prebody" "$tmpdir/summary-final.md" 2>/dev/null; then
            emit_body=true
        fi
    fi

    local emit_body_kv=false
    if [ "$emit_body" = true ] && [ "$wfr_rc" -eq 0 ] && [ -s "$tmpdir/summary-final.md" ]; then
        emit_body_kv=true
    fi

    emit_kv EMIT_BODY "$emit_body_kv"
    emit_kv WFR_RC "$wfr_rc"
    emit_kv STEP17_EMITTED_PRESENT "$step17_present"
}

main "$@"
