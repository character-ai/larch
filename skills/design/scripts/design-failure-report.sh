#!/usr/bin/env bash
# design-failure-report.sh — /design teardown gate for terminal and escalation reports.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
REPORT_SH="$PLUGIN_ROOT/skills/implement/scripts/stall-recovery-report.sh"

# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-design-tmpdir.sh
source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

usage() {
    larch_err 'Usage: design-failure-report.sh --design-tmpdir DIR --outcome TOKEN [--repo OWNER/REPO] [--issue N] [--run-id TOKEN]'
}

fail() { larch_err "design-failure-report.sh: $*"; exit 2; }
emit_skip() { emit_kv DESIGN_FAILURE_REPORT_DECISION skip; emit_kv DESIGN_FAILURE_REPORT_REASON "$1"; }

DESIGN_TMPDIR_ARG=""
OUTCOME=""
REPO=""
ISSUE=""
RUN_ID=""

while [ $# -gt 0 ]; do
    case "$1" in
        --design-tmpdir) [ $# -ge 2 ] || fail '--design-tmpdir requires a value'; DESIGN_TMPDIR_ARG=$2; shift 2 ;;
        --outcome) [ $# -ge 2 ] || fail '--outcome requires a value'; OUTCOME=$2; shift 2 ;;
        --repo) [ $# -ge 2 ] || fail '--repo requires a value'; REPO=$2; shift 2 ;;
        --issue) [ $# -ge 2 ] || fail '--issue requires a value'; ISSUE=$2; shift 2 ;;
        --run-id) [ $# -ge 2 ] || fail '--run-id requires a value'; RUN_ID=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) usage; fail "unknown option: $1" ;;
    esac
done

[ -n "$DESIGN_TMPDIR_ARG" ] || fail '--design-tmpdir is required'
[ -n "$OUTCOME" ] || fail '--outcome is required'
larch_design_tmpdir_validate "$DESIGN_TMPDIR_ARG" || exit $?
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"

TERMINAL_STATE="$DESIGN_TMPDIR/design-failure-terminal-state.env"
CLASS_FILE="$DESIGN_TMPDIR/design-failure-classification.env"
ATTEMPTS_FILE="$DESIGN_TMPDIR/design-failure-attempts.env"
LEDGER="$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv"
FALLBACK="$DESIGN_TMPDIR/design-failure-escalation-fallback.tsv"
MARKER="$DESIGN_TMPDIR/design-failure-escalation-record-failure.env"
ROOT_FILE="$DESIGN_TMPDIR/design-failure-root-cause.md"
BOUNDED_ROOT_FILE="$DESIGN_TMPDIR/design-failure-bounded-root-cause.md"
SENSITIVE_FILE="$DESIGN_TMPDIR/design-failure-sensitive-corpus.env"
CHAT_PRINT="$DESIGN_TMPDIR/design-failure-chat-print.md"
OPERATOR_CHAT="$DESIGN_TMPDIR/design-failure-operator-action-chat.md"
TERMINAL_SENTINEL="$DESIGN_TMPDIR/design-failure-terminal-report.env"
ESCALATION_SENTINEL="$DESIGN_TMPDIR/design-failure-escalation-success.env"
OPERATOR_SENTINEL="$DESIGN_TMPDIR/design-failure-operator-action.env"

append_run_log_audit() {
    local reason=$1 log_file="$DESIGN_TMPDIR/execution-issues.md" detail="$DESIGN_TMPDIR/design-failure-audit.log"
    printf 'design failure report audit: %s\n' "$reason" >"$detail"
    python3 "$PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$log_file" \
        --site "design failure report" \
        --tool "design-failure-report.sh" \
        --exit-code 0 \
        --category Warnings \
        --output-file "$detail" \
        --redact >/dev/null 2>&1 || true
}

write_operator_action_audit() {
    local reason=$1
    cat >"$OPERATOR_SENTINEL" <<EOF2
DESIGN_FAILURE_OPERATOR_ACTION=true
REASON=$reason
OUTCOME=$OUTCOME
EOF2
    {
        printf '**ℹ /design auto-report skipped:** operator action or cancellation outcome `%s`.\n\n' "$OUTCOME"
        printf 'No public larch bug was filed. The skip was recorded in the run log.\n'
    } >"$OPERATOR_CHAT"
    append_run_log_audit "operator-action:$reason"
}

write_fallback_chat() {
    local reason=$1
    {
        printf '### [Bug] /design report fallback required\n\n'
        printf 'The /design failure reporter could not safely file an issue.\n\n'
        printf '| Field | Value |\n|---|---|\n'
        printf '| Outcome | `%s` |\n' "$OUTCOME"
        printf '| Reason | `%s` |\n\n' "$reason"
        printf 'Use the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.\n'
    } >"$CHAT_PRINT"
    emit_kv DESIGN_FAILURE_REPORT_DECISION fallback-print-required
    emit_kv DESIGN_FAILURE_REPORT_REASON "$reason"
    emit_kv DESIGN_FAILURE_REPORT_ARTIFACT "$CHAT_PRINT"
}

safe_root_summary_from_state() {
    local site trigger outcome
    site=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$TERMINAL_STATE" --key SITE --default unknown)
    trigger=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$TERMINAL_STATE" --key TRIGGER --default unknown)
    outcome=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$TERMINAL_STATE" --key FAILURE_OUTCOME --default "$OUTCOME")
    printf '%s at %s via %s\n' "$outcome" "$site" "$trigger"
}

prepare_root_cause() {
    local kind=$1 summary verdict hint
    verdict=larch-defect
    if [ "$kind" = terminal ]; then
        hint=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$TERMINAL_STATE" --key ROOT_CAUSE_HINT --default '')
        case "$hint" in larch-defect|environment|operator-action) verdict=$hint ;; esac
        summary=$(safe_root_summary_from_state)
    else
        summary="design escalation reached main-agent recovery"
    fi
    cat >"$ROOT_FILE" <<EOF2
verdict=$verdict
confidence=medium
summary=$summary

The reporter used bounded /design state tokens and local ledger evidence only.
EOF2
    cp "$ROOT_FILE" "$BOUNDED_ROOT_FILE"
    : >"$SENSITIVE_FILE"
}

helper_common=(--profile generic --artifact-prefix design-failure --implement-tmpdir "$DESIGN_TMPDIR")
state_overrides=(--primary-state-file "$TERMINAL_STATE" --session-env-file "$DESIGN_TMPDIR/source-env.sh")
[ -f "$DESIGN_TMPDIR/finalize-state.sh" ] && state_overrides+=(--finalize-state-file "$DESIGN_TMPDIR/finalize-state.sh")

if [ -e "$TERMINAL_SENTINEL" ]; then
    emit_skip terminal-sentinel-present
    exit 0
fi
if [ -e "$ESCALATION_SENTINEL" ]; then
    emit_skip escalation-sentinel-present
    exit 0
fi
if [ -e "$OPERATOR_SENTINEL" ]; then
    [ -s "$OPERATOR_CHAT" ] || write_operator_action_audit operator-sentinel-present
    emit_skip operator-action
    exit 0
fi

case "$OUTCOME" in
    cancelled-*)
        write_operator_action_audit cancelled-outcome
        emit_kv DESIGN_FAILURE_REPORT_DECISION operator-action-skip
        emit_kv DESIGN_FAILURE_REPORT_ARTIFACT "$OPERATOR_CHAT"
        exit 0
        ;;
esac

case "$OUTCOME" in
    failed-plan-write|failed-publish|failed-postplan|failed-clarify|failed-judge-panel|failed-publish-tail)
        if [ ! -e "$TERMINAL_STATE" ]; then
            write_fallback_chat missing-terminal-state
            exit 0
        fi
        if ! "$REPORT_SH" "${helper_common[@]}" validate-terminal-state --primary-state-file "$TERMINAL_STATE" >/dev/null 2>"$DESIGN_TMPDIR/design-failure-validate-terminal-state.stderr.log"; then
            append_run_log_audit invalid-terminal-state
            write_fallback_chat invalid-terminal-state
            exit 0
        fi
        prepare_root_cause terminal
        "$REPORT_SH" "${helper_common[@]}" init-attempts --attempts-file "$ATTEMPTS_FILE" >/dev/null
        "$REPORT_SH" "${helper_common[@]}" "${state_overrides[@]}" classify >"$DESIGN_TMPDIR/design-failure-classify.env"
        if ! "$REPORT_SH" "${helper_common[@]}" "${state_overrides[@]}" compose-report \
            --report-kind terminal-failure \
            --surface chat-print \
            --classification-file "$CLASS_FILE" \
            --attempts-file "$ATTEMPTS_FILE" \
            --root-cause-file "$ROOT_FILE" \
            --bounded-root-cause-file "$BOUNDED_ROOT_FILE" \
            --sensitive-corpus-file "$SENSITIVE_FILE" \
            --output-file "$CHAT_PRINT" >"$DESIGN_TMPDIR/design-failure-compose.env" 2>"$DESIGN_TMPDIR/design-failure-compose.stderr.log"; then
            append_run_log_audit terminal-compose-failed
            write_fallback_chat terminal-compose-failed
            exit 0
        fi
        cp "$DESIGN_TMPDIR/design-failure-compose.env" "$TERMINAL_SENTINEL"
        emit_kv DESIGN_FAILURE_REPORT_DECISION terminal-failure
        emit_kv DESIGN_FAILURE_REPORT_ENV "$TERMINAL_SENTINEL"
        exit 0
        ;;
esac

case "$OUTCOME" in
    approved|approved-partition) ;;
    *) emit_skip outcome-not-success-allowlist; exit 0 ;;
esac

if [ ! -s "$LEDGER" ] && [ ! -s "$FALLBACK" ] && [ ! -s "$MARKER" ]; then
    emit_skip no-escalation-evidence
    exit 0
fi
prepare_root_cause escalation
"$REPORT_SH" "${helper_common[@]}" init-attempts --attempts-file "$ATTEMPTS_FILE" >/dev/null
if ! "$REPORT_SH" "${helper_common[@]}" compose-report \
    --report-kind escalation-success \
    --surface chat-print \
    --attempts-file "$ATTEMPTS_FILE" \
    --escalation-ledger-file "$LEDGER" \
    --escalation-fallback-file "$FALLBACK" \
    --record-failure-marker "$MARKER" \
    --root-cause-file "$ROOT_FILE" \
    --bounded-root-cause-file "$BOUNDED_ROOT_FILE" \
    --sensitive-corpus-file "$SENSITIVE_FILE" \
    --output-file "$CHAT_PRINT" >"$DESIGN_TMPDIR/design-failure-compose.env" 2>"$DESIGN_TMPDIR/design-failure-compose.stderr.log"; then
    append_run_log_audit escalation-compose-failed
    write_fallback_chat escalation-compose-failed
    exit 0
fi
cp "$DESIGN_TMPDIR/design-failure-compose.env" "$ESCALATION_SENTINEL"
emit_kv DESIGN_FAILURE_REPORT_DECISION escalation-success
emit_kv DESIGN_FAILURE_REPORT_ENV "$ESCALATION_SENTINEL"
