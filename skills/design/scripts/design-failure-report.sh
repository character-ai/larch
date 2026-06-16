#!/usr/bin/env bash
# design-failure-report.sh — /design teardown gate for terminal and escalation reports.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
REPORT_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" stall-recovery)

# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"

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
: "$REPO" "$ISSUE" "$RUN_ID"
python3 "$PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR_ARG" || exit $?
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
larch_quiet_init

TERMINAL_STATE="$DESIGN_TMPDIR/design-failure-terminal-state.env"
CLASS_FILE="$DESIGN_TMPDIR/design-failure-classification.env"
ATTEMPTS_FILE="$DESIGN_TMPDIR/design-failure-attempts.env"
LEDGER="$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv"
FALLBACK="$DESIGN_TMPDIR/design-failure-escalation-fallback.tsv"
MARKER="$DESIGN_TMPDIR/design-failure-escalation-record-failure.env"
ROOT_FILE="$DESIGN_TMPDIR/design-failure-root-cause.md"
BOUNDED_ROOT_FILE="$DESIGN_TMPDIR/design-failure-bounded-root-cause.md"
SENSITIVE_FILE="$DESIGN_TMPDIR/design-failure-sensitive-corpus.env"
ISSUE_INPUT="$DESIGN_TMPDIR/design-failure-issue-input.md"
CHAT_PRINT="$DESIGN_TMPDIR/design-failure-chat-print.md"
OPERATOR_CHAT="$DESIGN_TMPDIR/design-failure-operator-action-chat.md"
TERMINAL_SENTINEL="$DESIGN_TMPDIR/design-failure-terminal-report.env"
ESCALATION_SENTINEL="$DESIGN_TMPDIR/design-failure-escalation-success.env"
OPERATOR_SENTINEL="$DESIGN_TMPDIR/design-failure-operator-action.env"
COMPOSE_ENV="$DESIGN_TMPDIR/design-failure-compose.env"

compose_env_key() {
    local key=$1 default=${2:-} value=""
    if [ "$key" = STALL_RECOVERY_REPORT_STATUS ] && [ -f "$COMPOSE_ENV" ]; then
        value=$(grep -E '^STALL_RECOVERY_REPORT_STATUS=' "$COMPOSE_ENV" 2>/dev/null | tail -1 | cut -d= -f2- || true)
        printf '%s\n' "${value:-$default}"
        return 0
    fi
    python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$COMPOSE_ENV" --key "$key" --default "$default"
}

resolve_working_tree_root() {
    local root=""
    if [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
        printf '%s\n' "$CLAUDE_PROJECT_DIR"
        return 0
    fi
    if [ -n "${REPO_ROOT:-}" ]; then
        printf '%s\n' "$REPO_ROOT"
        return 0
    fi
    if [ -f "$DESIGN_TMPDIR/source-env.sh" ]; then
        root=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$DESIGN_TMPDIR/source-env.sh" --key REPO_ROOT --default '')
        [ -n "$root" ] && { printf '%s\n' "$root"; return 0; }
    fi
    git rev-parse --show-toplevel 2>/dev/null || true
}

tier_a_forked() {
    local forked="" f
    for f in "$DESIGN_TMPDIR/ship-pr-state.sh" "$DESIGN_TMPDIR/finalize-state.sh" "$DESIGN_TMPDIR/source-env.sh"; do
        [ -f "$f" ] || continue
        forked=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$f" --key FORKED_TARGET --default '')
        [ -n "$forked" ] && break
    done
    case "$forked" in true|1|yes|TRUE|True) return 0 ;; esac
    return 1
}

tier_a_eligible() {
    local working_tree_root=""
    tier_a_forked && return 1
    working_tree_root=$(resolve_working_tree_root)
    [ -n "$working_tree_root" ] || return 1
    "${REPORT_CMD[@]}" is-larch-dev-clone "${helper_common[@]}" \
        --working-tree-root "$working_tree_root" \
        --implement-tmpdir "$DESIGN_TMPDIR" 2>/dev/null | grep -Fxq 'LARCH_DEV_CLONE=true'
}

report_surface() {
    if tier_a_eligible; then
        printf '%s\n' issue-input
    else
        printf '%s\n' chat-print
    fi
}

report_output_file() {
    case "$1" in
        issue-input) printf '%s\n' "$ISSUE_INPUT" ;;
        *) printf '%s\n' "$CHAT_PRINT" ;;
    esac
}

populate_design_sensitive_corpus() {
    local class_file=${1:-$CLASS_FILE} attempts_file=${2:-$ATTEMPTS_FILE}
    if [ ! -f "$class_file" ]; then
        class_file="$DESIGN_TMPDIR/design-failure-classification.seed.env"
        : >"$class_file"
    fi
    [ -f "$attempts_file" ] || attempts_file="$ATTEMPTS_FILE"
    "${REPORT_CMD[@]}" populate-sensitive-corpus "${helper_common[@]}" \
        --sensitive-corpus-file "$SENSITIVE_FILE" \
        --classification-file "$class_file" \
        --attempts-file "$attempts_file" \
        --escalation-ledger-file "$LEDGER" \
        --escalation-fallback-file "$FALLBACK" \
        --record-failure-marker "$MARKER" \
        >"$DESIGN_TMPDIR/design-failure-populate-sensitive.stdout.log" \
        2>"$DESIGN_TMPDIR/design-failure-populate-sensitive.stderr.log"
}

persist_effective_sensitive_corpus() {
    populate_design_sensitive_corpus "$CLASS_FILE" "$ATTEMPTS_FILE"
}

file_tier_a_after_compose() {
    local body_file=$1
    local dedup_env="$DESIGN_TMPDIR/design-failure-tier-a-dedup.env"
    local status title repo helper_out
    if ! "${REPORT_CMD[@]}" dedup-tier-a-report "${helper_common[@]}" --body-file "$body_file" >"$dedup_env" 2>"$DESIGN_TMPDIR/design-failure-tier-a-dedup.stderr.log"; then
        return 0
    fi
    status=$(python3 "$PLUGIN_ROOT/python/cli.py" session read-key --file "$dedup_env" --key STALL_RECOVERY_REPORT_STATUS --default '')
    case "$status" in
        no-match|lookup-failed-open)
            repo="$REPO"
            if [ -z "$repo" ]; then
                repo=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)
            fi
            [ -n "$repo" ] || return 0
            title=$(sed -n '1s/^### //p' "$body_file" | sed 's/^\[Bug\] //')
            [ -n "$title" ] || title="/design terminal failure"
            helper_out="$DESIGN_TMPDIR/design-failure-tier-a-file.env"
            if "$PLUGIN_ROOT/scripts/file-failure-report-cross-repo.sh" \
                --repo "$repo" \
                --body-file "$body_file" \
                --title "$title" \
                --publication-tier tier-a \
                >"$helper_out" 2>"$DESIGN_TMPDIR/design-failure-tier-a-file.stderr.log"; then
                local file_norm="$DESIGN_TMPDIR/design-failure-tier-a-file.normalized.env"
                "${REPORT_CMD[@]}" normalize-file-failure-report-env "${helper_common[@]}" --file-failure-report-env "$helper_out" >"$file_norm" 2>/dev/null || true
                cat "$file_norm" >>"$COMPOSE_ENV"
            fi
            ;;
        dedup-comment|dry-run|fallback-print-required|filed|printed)
            [ -s "$dedup_env" ] && cat "$dedup_env" >>"$COMPOSE_ENV"
            ;;
    esac
}

handle_compose_outcome() {
    local kind=$1 decision=$2 sentinel=$3 artifact_key=$4
    local status reason artifact
    status=$(compose_env_key STALL_RECOVERY_REPORT_STATUS "")
    if [ -z "$status" ] && panel_failure_evidence_present && [ -s "${LAST_REPORT_OUTPUT:-}" ]; then
        if [ "${LAST_REPORT_SURFACE:-}" = issue-input ]; then
            file_tier_a_after_compose "$LAST_REPORT_OUTPUT"
            status=$(compose_env_key STALL_RECOVERY_REPORT_STATUS "")
        fi
        if [ -z "$status" ]; then
            write_fallback_chat "compose-status-missing"
            exit 0
        fi
    fi
    case "$status" in
        skipped_operator_action)
            write_operator_action_audit "compose-$kind"
            emit_kv DESIGN_FAILURE_REPORT_DECISION operator-action-skip
            emit_kv DESIGN_FAILURE_REPORT_ARTIFACT "$OPERATOR_CHAT"
            exit 0
            ;;
        fallback-print-required)
            reason=$(compose_env_key STALL_RECOVERY_REPORT_FALLBACK_REASON "compose-$kind")
            write_fallback_chat "$reason"
            exit 0
            ;;
        filed|dry-run|dedup-comment|no-match|lookup-failed-open|printed)
            cp "$COMPOSE_ENV" "$sentinel"
            emit_kv DESIGN_FAILURE_REPORT_DECISION "$decision"
            emit_kv DESIGN_FAILURE_REPORT_ENV "$sentinel"
            artifact=$(compose_env_key "$artifact_key" "")
            [ -n "$artifact" ] && emit_kv DESIGN_FAILURE_REPORT_ARTIFACT "$artifact"
            exit 0
            ;;
        "")
            write_fallback_chat "compose-status-missing"
            exit 0
            ;;
        *)
            write_fallback_chat "compose-status-$status"
            exit 0
            ;;
    esac
}

escalation_evidence_present() {
    [ -s "$LEDGER" ] || [ -s "$FALLBACK" ] || [ -s "$MARKER" ] && return 0
    [ -f "$DESIGN_TMPDIR/execution-issues.md" ] && [ ! -L "$DESIGN_TMPDIR/execution-issues.md" ] && \
        grep -Eq '^#{2,3}[[:space:]]+Tool Failure: record-escalation([[:space:]]|$)' "$DESIGN_TMPDIR/execution-issues.md"
}

panel_failure_evidence_present() {
    if [ -f "$TERMINAL_STATE" ] && [ ! -L "$TERMINAL_STATE" ]; then
        grep -Eq '^(TRIGGER|BAIL_REASON)=(panel-failed|panel-init-failed)$' "$TERMINAL_STATE" && return 0
    fi
    [ -f "$LEDGER" ] && grep -Eq 'trigger=(panel-failed|panel-init-failed)([[:space:]]|$)' "$LEDGER" && return 0
    [ -f "$FALLBACK" ] && grep -Eq 'trigger=(panel-failed|panel-init-failed)([[:space:]]|$)' "$FALLBACK" && return 0
    [ -f "$MARKER" ] && grep -Eq 'trigger=(panel-failed|panel-init-failed)([[:space:]]|$)' "$MARKER" && return 0
    [ -f "$DESIGN_TMPDIR/execution-issues.md" ] && [ ! -L "$DESIGN_TMPDIR/execution-issues.md" ] && \
        grep -Eq 'panel-failed|panel-init-failed' "$DESIGN_TMPDIR/execution-issues.md"
}

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
        # shellcheck disable=SC2016
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
        # shellcheck disable=SC2016
        printf '| Outcome | `%s` |\n' "$OUTCOME"
        # shellcheck disable=SC2016
        printf '| Reason | `%s` |\n\n' "$reason"
        # shellcheck disable=SC2016
        printf 'Use the local artifacts in `DESIGN_TMPDIR` to investigate. This fallback contains no log tail.\n'
    } >"$CHAT_PRINT"
    emit_kv DESIGN_FAILURE_REPORT_DECISION fallback-print-required
    emit_kv DESIGN_FAILURE_REPORT_REASON "$reason"
    emit_kv DESIGN_FAILURE_REPORT_ARTIFACT "$CHAT_PRINT"
}

safe_root_summary_from_state() {
    local site=unknown trigger=unknown outcome="$OUTCOME" line
    # One batched read instead of three session read-key spawns (#4439 Trick B).
    while IFS= read -r line; do
        case "$line" in
            SITE=*) site=${line#SITE=} ;;
            TRIGGER=*) trigger=${line#TRIGGER=} ;;
            FAILURE_OUTCOME=*) outcome=${line#FAILURE_OUTCOME=} ;;
        esac
    done < <(python3 "$PLUGIN_ROOT/python/cli.py" session read-keys --file "$TERMINAL_STATE" --key SITE=unknown --key TRIGGER=unknown --key "FAILURE_OUTCOME=$OUTCOME")
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
    populate_design_sensitive_corpus
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
        if ! "${REPORT_CMD[@]}" validate-terminal-state "${helper_common[@]}" --primary-state-file "$TERMINAL_STATE" >/dev/null 2>"$DESIGN_TMPDIR/design-failure-validate-terminal-state.stderr.log"; then
            append_run_log_audit invalid-terminal-state
            write_fallback_chat invalid-terminal-state
            exit 0
        fi
        state_outcome=""
        state_summary=""
        # One batched read instead of two session read-key spawns (#4439 Trick B).
        while IFS= read -r kv_line; do
            case "$kv_line" in
                FAILURE_OUTCOME=*) state_outcome=${kv_line#FAILURE_OUTCOME=} ;;
                SUMMARY_OUTCOME=*) state_summary=${kv_line#SUMMARY_OUTCOME=} ;;
            esac
        done < <(python3 "$PLUGIN_ROOT/python/cli.py" session read-keys --file "$TERMINAL_STATE" --key "FAILURE_OUTCOME=" --key "SUMMARY_OUTCOME=")
        if [ -n "$state_outcome" ] && [ "$state_outcome" != "$OUTCOME" ]; then
            append_run_log_audit terminal-state-outcome-mismatch
            write_fallback_chat terminal-state-outcome-mismatch
            exit 0
        fi
        if [ -n "$state_summary" ] && [ "$state_summary" != "$OUTCOME" ]; then
            append_run_log_audit terminal-state-summary-mismatch
            write_fallback_chat terminal-state-summary-mismatch
            exit 0
        fi
        prepare_root_cause terminal
        "${REPORT_CMD[@]}" init-attempts "${helper_common[@]}" --attempts-file "$ATTEMPTS_FILE" >/dev/null
        "${REPORT_CMD[@]}" classify "${helper_common[@]}" "${state_overrides[@]}" >"$DESIGN_TMPDIR/design-failure-classify.env"
        _report_surface=$(report_surface)
        _report_output=$(report_output_file "$_report_surface")
        LAST_REPORT_SURFACE="$_report_surface"
        LAST_REPORT_OUTPUT="$_report_output"
        if ! populate_design_sensitive_corpus "$CLASS_FILE" "$ATTEMPTS_FILE"; then
            append_run_log_audit populate-sensitive-corpus-failed
            write_fallback_chat populate-sensitive-corpus-failed
            exit 0
        fi
        if ! "${REPORT_CMD[@]}" compose-report "${helper_common[@]}" "${state_overrides[@]}" \
            --report-kind terminal-failure \
            --surface "$_report_surface" \
            --classification-file "$CLASS_FILE" \
            --attempts-file "$ATTEMPTS_FILE" \
            --root-cause-file "$ROOT_FILE" \
            --bounded-root-cause-file "$BOUNDED_ROOT_FILE" \
            --sensitive-corpus-file "$SENSITIVE_FILE" \
            --output-file "$_report_output" >"$COMPOSE_ENV" 2>"$DESIGN_TMPDIR/design-failure-compose.stderr.log"; then
            append_run_log_audit terminal-compose-failed
            write_fallback_chat terminal-compose-failed
            exit 0
        fi
        persist_effective_sensitive_corpus
        if [ "$_report_surface" = issue-input ]; then
            file_tier_a_after_compose "$_report_output"
        fi
        handle_compose_outcome terminal-failure terminal-failure "$TERMINAL_SENTINEL" STALL_RECOVERY_REPORT_ARTIFACT
        ;;
esac

case "$OUTCOME" in
    approved|approved-partition) ;;
    *) emit_skip outcome-not-success-allowlist; exit 0 ;;
esac

if [ -e "$OPERATOR_SENTINEL" ]; then
    [ -s "$OPERATOR_CHAT" ] || write_operator_action_audit operator-sentinel-present
    emit_skip operator-action
    exit 0
fi

if ! escalation_evidence_present; then
    emit_skip no-escalation-evidence
    exit 0
fi
prepare_root_cause escalation
"${REPORT_CMD[@]}" init-attempts "${helper_common[@]}" --attempts-file "$ATTEMPTS_FILE" >/dev/null
_report_surface=$(report_surface)
_report_output=$(report_output_file "$_report_surface")
LAST_REPORT_SURFACE="$_report_surface"
LAST_REPORT_OUTPUT="$_report_output"
if ! populate_design_sensitive_corpus "" "$ATTEMPTS_FILE"; then
    append_run_log_audit populate-sensitive-corpus-failed
    write_fallback_chat populate-sensitive-corpus-failed
    exit 0
fi
if ! "${REPORT_CMD[@]}" compose-report "${helper_common[@]}" \
    --report-kind escalation-success \
    --surface "$_report_surface" \
    --attempts-file "$ATTEMPTS_FILE" \
    --escalation-ledger-file "$LEDGER" \
    --escalation-fallback-file "$FALLBACK" \
    --record-failure-marker "$MARKER" \
    --root-cause-file "$ROOT_FILE" \
    --bounded-root-cause-file "$BOUNDED_ROOT_FILE" \
    --sensitive-corpus-file "$SENSITIVE_FILE" \
    --output-file "$_report_output" >"$COMPOSE_ENV" 2>"$DESIGN_TMPDIR/design-failure-compose.stderr.log"; then
    append_run_log_audit escalation-compose-failed
    write_fallback_chat escalation-compose-failed
    exit 0
fi
persist_effective_sensitive_corpus
if [ "$_report_surface" = issue-input ]; then
    file_tier_a_after_compose "$_report_output"
fi
handle_compose_outcome escalation-success escalation-success "$ESCALATION_SENTINEL" STALL_RECOVERY_REPORT_ARTIFACT
