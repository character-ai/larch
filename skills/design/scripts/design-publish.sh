#!/usr/bin/env bash
# design-publish.sh — /design Step 5c publish-tail phase driver (plan write, diagrams, rename, log publish).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
larch_quiet_init

fail() {
    larch_err "design-publish.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: design-publish.sh --design-tmpdir PATH --issue N --session-id STR --claude-pid N [--repo OWNER/REPO] [--skip-validate]'
}

validate_session_id_flag() {
    local value="$1"
    case "$value" in
        *$'\n'* | *$'\r'*) fail 'invalid --session-id' ;;
    esac
    if [[ -n "$value" && "$value" =~ ^[[:space:]]+$ ]]; then
        fail 'invalid --session-id'
    fi
}

validate_repo() {
    local value="$1"
    case "$value" in
        '' | --* | *$'\n'* | *$'\r'* | /* | *../* | *\\*) fail 'invalid --repo' ;;
    esac
    [[ "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || fail 'invalid --repo'
}

parse_kv_from_output() {
    local text="${1:-}"
    local _line _key _value
    while IFS= read -r _line || [[ -n "$_line" ]]; do
        _key="${_line%%=*}"
        _value="${_line#*=}"
        case "$_key" in
            PUBLISH_OK) PUBLISH_OK="$_value" ;;
            PR_NUMBER) PR_NUMBER="$_value" ;;
            PR_URL) PR_URL="$_value" ;;
            RECOVERY_BRANCH) RECOVERY_BRANCH="$_value" ;;
            UPSERT_STATUS) UPSERT_STATUS="$_value" ;;
            ARCHITECTURE_SOURCE) ARCHITECTURE_SOURCE="$_value" ;;
            VALIDATE_STATUS) VALIDATE_STATUS="$_value" ;;
            VALIDATE_DEFECT_COUNT) VALIDATE_DEFECT_COUNT="$_value" ;;
            VALIDATE_SKIPPED_COUNT) VALIDATE_SKIPPED_COUNT="$_value" ;;
            VALIDATE_UNSAFE_TOKEN_COUNT) VALIDATE_UNSAFE_TOKEN_COUNT="$_value" ;;
            VALIDATE_LOG_FILE) VALIDATE_LOG_FILE="$_value" ;;
        esac
    done <<<"$text"
}

validate_pr_number() {
    local value="$1"
    [[ "$value" =~ ^[1-9][0-9]*$ ]]
}

validate_pr_url() {
    local value="$1"
    [[ "$value" =~ ^https://github[.]com/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+/pull/[1-9][0-9]*([/?#].*)?$ ]]
}

validate_recovery_branch() {
    local value="$1"
    [[ "$value" =~ ^[A-Za-z0-9._/-]+$ ]] || return 1
    git check-ref-format --branch "$value" >/dev/null 2>&1
}

sanitize_publish_metadata() {
    [[ -z "${PR_NUMBER:-}" ]] || validate_pr_number "$PR_NUMBER" || PR_NUMBER=""
    [[ -z "${PR_URL:-}" ]] || validate_pr_url "$PR_URL" || PR_URL=""
    [[ -z "${RECOVERY_BRANCH:-}" ]] || validate_recovery_branch "$RECOVERY_BRANCH" || RECOVERY_BRANCH=""
}

DESIGN_TMPDIR_ARG=""
ISSUE=""
SESSION_ID=""
HAVE_SESSION_ID=false
CLAUDE_PID=""
REPO=""
SKIP_VALIDATE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
            shift 2
            ;;
        --issue)
            [[ $# -ge 2 ]] || fail '--issue requires a value'
            ISSUE="$2"
            shift 2
            ;;
        --session-id)
            [[ $# -ge 2 ]] || fail '--session-id requires a value'
            SESSION_ID="$2"
            HAVE_SESSION_ID=true
            shift 2
            ;;
        --claude-pid)
            [[ $# -ge 2 ]] || fail '--claude-pid requires a value'
            CLAUDE_PID="$2"
            shift 2
            ;;
        --repo)
            [[ $# -ge 2 ]] || fail '--repo requires a value'
            REPO="$2"
            shift 2
            ;;
        --skip-validate)
            SKIP_VALIDATE=true
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$DESIGN_TMPDIR_ARG" ]] || { usage; fail '--design-tmpdir is required'; }
[[ -n "$ISSUE" ]] || { usage; fail '--issue is required'; }
[[ "$HAVE_SESSION_ID" == true ]] || { usage; fail '--session-id is required'; }
[[ -n "$CLAUDE_PID" ]] || { usage; fail '--claude-pid is required'; }

case "$ISSUE" in
    '' | *[!0-9]*) fail '--issue must be a positive integer' ;;
esac
[[ "$ISSUE" != "0" ]] || fail '--issue must be a positive integer'
case "$CLAUDE_PID" in
    '' | *[!0-9]*) fail '--claude-pid must be a positive integer' ;;
esac
validate_session_id_flag "$SESSION_ID"
[[ -n "$REPO" ]] && validate_repo "$REPO"

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR
SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

export ISSUE_NUMBER="$ISSUE"
export SESSION_ID="$SESSION_ID"

RESULT_ENV="$DESIGN_TMPDIR/.design-publish-result.env"
FINAL_SUMMARY_PATH="$DESIGN_TMPDIR/final-summary.md"
WARN_LINES=()
PLAN_WRITE_OK=false
PUBLISH_OK=""
PR_NUMBER=""
PR_URL=""
RECOVERY_BRANCH=""
RENAMED=""
NEW_TITLE=""
DESIGNED_ADMISSION_READY=false
UPSERT_STATUS=""
ARCHITECTURE_SOURCE=""
UPSERT_RAN=false
VALIDATE_STATUS=not-run
VALIDATE_DEFECT_COUNT=0
VALIDATE_SKIPPED_COUNT=0
VALIDATE_UNSAFE_TOKEN_COUNT=0
VALIDATE_LOG_FILE=""

add_warn() {
    WARN_LINES+=("$1")
}

publish_recovery_detail() {
    local _details=()
    [[ -n "${PR_NUMBER:-}" ]] && _details+=("PR #$PR_NUMBER")
    [[ -n "${PR_URL:-}" ]] && _details+=("$PR_URL")
    [[ -n "${RECOVERY_BRANCH:-}" ]] && _details+=("recovery branch $RECOVERY_BRANCH")
    if [[ "${#_details[@]}" -eq 0 ]]; then
        printf '%s\n' 'no PR or recovery branch metadata was returned'
    else
        local _joined="${_details[0]}" _detail
        for _detail in "${_details[@]:1}"; do
            _joined="${_joined}, ${_detail}"
        done
        printf '%s\n' "$_joined"
    fi
}

renamed_admission_ready() {
    [[ "${RENAMED:-}" == true ]] && return 0
    [[ "${RENAMED:-}" == false && "${NEW_TITLE:-}" == "[DESIGNED] "* ]] && return 0
    return 1
}

refresh_designed_admission_ready() {
    DESIGNED_ADMISSION_READY=false
    if [[ "${UPSERT_RAN:-}" == true && "${UPSERT_STATUS:-}" != ok ]]; then
        return 0
    fi
    if renamed_admission_ready; then
        DESIGNED_ADMISSION_READY=true
    fi
}


render_fresh_timing_report_for_publish() {
    local _tmp_dir _tmp_json _tmp_stderr _render_rc=0 _existing
    _tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/larch-design-timing-report.XXXXXX") || {
        add_warn '**⚠ 5c: failed to create temporary directory for timing report render.**'
        : >"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        printf '%s\n' "mktemp failed while preparing timing-report-final.json" >"$DESIGN_TMPDIR/timing-report-final.failure.log" 2>/dev/null || true
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c timing-report" \
            --tool "mktemp" \
            --exit-code 1 \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/timing-report-final.failure.log" \
            --redact >/dev/null 2>&1 || true
        return 0
    }
    _tmp_json="$_tmp_dir/timing-report-final.json"
    _tmp_stderr="$_tmp_dir/timing-report-final.stderr.log"
    for _existing in "$DESIGN_TMPDIR"/timing-report-final.*; do
        [[ -e "$_existing" ]] || continue
        rm -f "$_existing" 2>/dev/null || true
    done
    if ! command -v jq >/dev/null 2>&1; then
        add_warn '**⚠ 5c: jq is required to validate timing-report-final.json before publish.**'
        : >"$_tmp_stderr" 2>/dev/null || true
        printf '%s\n' "jq is required to validate timing-report-final.json before publish" >"$_tmp_stderr" 2>/dev/null || true
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c timing-report" \
            --tool "jq" \
            --exit-code 127 \
            --category Warnings \
            --output-file "$_tmp_stderr" \
            --redact >/dev/null 2>&1 || true
        rm -rf "$_tmp_dir"
        rm -f "$DESIGN_TMPDIR"/timing-report-final.* 2>/dev/null || true
        return 0
    fi
    set +e
    env -u IMPLEMENT_TMPDIR \
        LARCH_TIMING_SKILL=design DESIGN_TMPDIR="$DESIGN_TMPDIR" LARCH_TIMING_LEDGER="$DESIGN_TMPDIR/timing-ledger.tsv" \
        "$PLUGIN_ROOT/scripts/timing-report.sh" --full --format json --output "$_tmp_json" > /dev/null 2>"$_tmp_stderr"
    _render_rc=$?
    set -e
    if [[ "$_render_rc" -eq 0 && -s "$_tmp_json" ]] && jq -e '
        type == "object" and
        (.per_step | type == "array") and
        (.per_step[]? | select(.skill == "design" and .step == "design Step 3 — plan review" and (.rounds | type == "array"))) and
        (.total_seconds | type == "number") and
        (.total_hms | type == "string")
    ' "$_tmp_json" >/dev/null 2>>"$_tmp_stderr"; then
        mv -f "$_tmp_json" "$DESIGN_TMPDIR/timing-report-final.json"
        rm -rf "$_tmp_dir"
        return 0
    fi
    rm -f "$DESIGN_TMPDIR"/timing-report-final.* 2>/dev/null || true
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site "design Step 5c timing-report" \
        --tool "timing-report.sh" \
        --exit-code "${_render_rc:-1}" \
        --category Warnings \
        --output-file "$_tmp_stderr" \
        --redact >/dev/null 2>&1 || true
    add_warn '**⚠ 5c: failed to render fresh timing-report-final.json before publishing design logs.**'
    rm -rf "$_tmp_dir"
}

write_result_env_and_emit() {
    local -a _kvs=()
    refresh_designed_admission_ready
    _kvs+=("PLAN_WRITE_OK=$PLAN_WRITE_OK")
    _kvs+=("VALIDATE_STATUS=$VALIDATE_STATUS")
    _kvs+=("VALIDATE_DEFECT_COUNT=$VALIDATE_DEFECT_COUNT")
    _kvs+=("VALIDATE_SKIPPED_COUNT=$VALIDATE_SKIPPED_COUNT")
    _kvs+=("VALIDATE_UNSAFE_TOKEN_COUNT=$VALIDATE_UNSAFE_TOKEN_COUNT")
    _kvs+=("VALIDATE_LOG_FILE=$VALIDATE_LOG_FILE")
    [[ -n "${PUBLISH_OK:-}" ]] && _kvs+=("PUBLISH_OK=$PUBLISH_OK")
    [[ -n "${PR_NUMBER:-}" ]] && _kvs+=("PR_NUMBER=$PR_NUMBER")
    [[ -n "${PR_URL:-}" ]] && _kvs+=("PR_URL=$PR_URL")
    [[ -n "${RECOVERY_BRANCH:-}" ]] && _kvs+=("RECOVERY_BRANCH=$RECOVERY_BRANCH")
    [[ -n "${RECOVERY_BRANCH:-}" ]] && _kvs+=("LOG_RECOVERY_BRANCH=$RECOVERY_BRANCH")
    [[ -n "${RENAMED:-}" ]] && _kvs+=("RENAMED=$RENAMED")
    [[ -n "${NEW_TITLE:-}" ]] && _kvs+=("NEW_TITLE=$NEW_TITLE")
    _kvs+=("DESIGNED_ADMISSION_READY=$DESIGNED_ADMISSION_READY")
    [[ -n "${UPSERT_STATUS:-}" ]] && _kvs+=("UPSERT_STATUS=$UPSERT_STATUS")
    [[ -n "${ARCHITECTURE_SOURCE:-}" ]] && _kvs+=("ARCHITECTURE_SOURCE=$ARCHITECTURE_SOURCE")
    _kvs+=("FINAL_SUMMARY_PATH=$FINAL_SUMMARY_PATH")
    local _warn
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        _kvs+=("WARN=$_warn")
    done
    emit_kv PLAN_WRITE_OK "$PLAN_WRITE_OK"
    emit_kv VALIDATE_STATUS "$VALIDATE_STATUS"
    emit_kv VALIDATE_DEFECT_COUNT "$VALIDATE_DEFECT_COUNT"
    emit_kv VALIDATE_SKIPPED_COUNT "$VALIDATE_SKIPPED_COUNT"
    emit_kv VALIDATE_UNSAFE_TOKEN_COUNT "$VALIDATE_UNSAFE_TOKEN_COUNT"
    emit_kv VALIDATE_LOG_FILE "$VALIDATE_LOG_FILE"
    [[ -n "${PUBLISH_OK:-}" ]] && emit_kv PUBLISH_OK "$PUBLISH_OK"
    [[ -n "${PR_NUMBER:-}" ]] && emit_kv PR_NUMBER "$PR_NUMBER"
    [[ -n "${PR_URL:-}" ]] && emit_kv PR_URL "$PR_URL"
    [[ -n "${RECOVERY_BRANCH:-}" ]] && emit_kv RECOVERY_BRANCH "$RECOVERY_BRANCH"
    [[ -n "${RECOVERY_BRANCH:-}" ]] && emit_kv LOG_RECOVERY_BRANCH "$RECOVERY_BRANCH"
    [[ -n "${RENAMED:-}" ]] && emit_kv RENAMED "$RENAMED"
    [[ -n "${NEW_TITLE:-}" ]] && emit_kv NEW_TITLE "$NEW_TITLE"
    emit_kv DESIGNED_ADMISSION_READY "$DESIGNED_ADMISSION_READY"
    [[ -n "${UPSERT_STATUS:-}" ]] && emit_kv UPSERT_STATUS "$UPSERT_STATUS"
    [[ -n "${ARCHITECTURE_SOURCE:-}" ]] && emit_kv ARCHITECTURE_SOURCE "$ARCHITECTURE_SOURCE"
    emit_kv FINAL_SUMMARY_PATH "$FINAL_SUMMARY_PATH"
    for _warn in "${WARN_LINES[@]+"${WARN_LINES[@]}"}"; do
        emit_kv WARN "$_warn"
    done
    phase_driver_write_result_env "$RESULT_ENV" "${_kvs[@]}"
}

[[ -f "$DESIGN_TMPDIR/.completed/step-5b" ]] \
    || fail 'Step 5b sentinel missing — refusing to publish before OOS filing'
[[ -s "$DESIGN_TMPDIR/composed-plan.md" ]] \
    || fail 'composed-plan.md missing or empty — orchestrator must compose the plan first'

if [[ -f "$DESIGN_TMPDIR/.pause-requested" ]]; then
    exec "$PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE" ${REPO:+--repo "$REPO"}
fi

if [[ "$SKIP_VALIDATE" == true ]]; then
    VALIDATE_STATUS=skipped
else
    set +e
    _validate_out=$("$PLUGIN_ROOT/skills/design/scripts/invoke-plan-validator.sh" "$DESIGN_TMPDIR/composed-plan.md" 2>&1)
    _validate_rc=$?
    set -e
    parse_kv_from_output "$_validate_out"
    if [[ "$VALIDATE_STATUS" == defects-found ]]; then
        PLAN_WRITE_OK=false
        write_result_env_and_emit || true
        exit 4
    fi
    if [[ "$_validate_rc" -ne 0 || -z "$VALIDATE_STATUS" || "$VALIDATE_STATUS" == not-run ]]; then
        fail 'plan validator failed before publish'
    fi
    if [[ "$VALIDATE_STATUS" != ok ]]; then
        fail 'plan validator returned unexpected VALIDATE_STATUS before publish'
    fi
fi

if ! "$PLUGIN_ROOT/scripts/redact-secrets.sh" <"$DESIGN_TMPDIR/composed-plan.md" >"$DESIGN_TMPDIR/composed-plan.redacted.md"; then
    fail 'redact-secrets.sh failed'
fi
[[ -s "$DESIGN_TMPDIR/composed-plan.redacted.md" ]] \
    || fail 'composed-plan.redacted.md missing or empty after redaction'

if [[ -z "$REPO" ]]; then
    if _resolved=$("$PLUGIN_ROOT/scripts/resolve-repo.sh" 2>/dev/null); then
        REPO="$_resolved"
    elif command -v gh >/dev/null 2>&1; then
        REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)
    fi
fi
[[ -n "$REPO" ]] && validate_repo "$REPO"

MODE="N/A"
if command -v jq >/dev/null 2>&1 && [[ -f "$DESIGN_TMPDIR/run-params.json" ]]; then
    MODE=$(jq -r '.design_classification // "N/A"' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo N/A)
fi

_plan_block_args=(--issue "$ISSUE" --content-file "$DESIGN_TMPDIR/composed-plan.redacted.md")
[[ -n "$REPO" ]] && _plan_block_args+=(--repo "$REPO")
if ! "$PLUGIN_ROOT/scripts/plan-block-write.sh" "${_plan_block_args[@]}"; then
    PLAN_WRITE_OK=false
    "${PLUGIN_ROOT}/skills/design/scripts/render-final-summary.sh" \
        --outcome failed-plan-write \
        --mode "$MODE" \
        ${REPO:+--repo "$REPO"} \
        --post-publish-only || true
    write_result_env_and_emit || exit 1
    exit 1
fi

PLAN_WRITE_OK=true

_arch_file="$DESIGN_TMPDIR/architecture-diagram.md"
_arch_skipped="$DESIGN_TMPDIR/architecture-diagram.skipped"
_run_upsert=false
_upsert_args=(--issue "$ISSUE")
[[ -n "$REPO" ]] && _upsert_args+=(--repo "$REPO")
if [[ -f "$_arch_file" ]] && [[ -s "$_arch_file" ]]; then
    _run_upsert=true
    _upsert_args+=(--architecture-file "$_arch_file")
elif [[ -f "$_arch_file" ]] && [[ ! -s "$_arch_file" ]] && [[ -f "$_arch_skipped" ]]; then
    _run_upsert=true
    _upsert_args+=(--clear-architecture)
elif [[ ! -f "$_arch_file" ]] && [[ -f "$_arch_skipped" ]]; then
    _run_upsert=true
    _upsert_args+=(--clear-architecture)
fi

if [[ "$_run_upsert" == true ]]; then
    UPSERT_RAN=true
    set +e
    _upsert_out=$("$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh" "${_upsert_args[@]}" 2>"$DESIGN_TMPDIR/diagrams-architecture-upsert.stderr")
    _upsert_rc=$?
    set -e
    printf '%s\n' "$_upsert_out" >"$DESIGN_TMPDIR/diagrams-architecture-upsert.stdout"
    parse_kv_from_output "$_upsert_out"
    if [[ "${UPSERT_STATUS:-}" == failed ]] || [[ "$_upsert_rc" -ne 0 ]]; then
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c.5" \
            --tool "upsert-diagrams-comment.sh architecture" \
            --exit-code "${_upsert_rc:-1}" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/diagrams-architecture-upsert.stderr" \
            --redact >/dev/null 2>&1 || true
    fi
fi

if [[ -n "$SESSION_ID" ]]; then
    _rename_seen=false
    if _rename_out=$("$PLUGIN_ROOT/scripts/tracking-issue-write.sh" rename --issue "$ISSUE" --state designed ${REPO:+--repo "$REPO"}); then
        RENAMED=""
        NEW_TITLE=""
        while IFS= read -r _rename_line || [[ -n "$_rename_line" ]]; do
            case "$_rename_line" in
                RENAMED=true) RENAMED=true; _rename_seen=true ;;
                RENAMED=false) RENAMED=false; _rename_seen=true ;;
                NEW_TITLE=*) NEW_TITLE="${_rename_line#NEW_TITLE=}" ;;
            esac
        done <<<"${_rename_out:-}"
        if [[ "$_rename_seen" != true ]]; then
            add_warn "**⚠ 5c: tracking-issue-write.sh rename succeeded but omitted RENAMED= line; treating rename outcome as unknown.**"
        fi
    else
        RENAMED=false
        NEW_TITLE=""
        _diagram_detail="diagram upsert skipped"
        if [[ "$UPSERT_RAN" == true ]]; then
            if [[ "${UPSERT_STATUS:-}" == failed ]]; then
                _diagram_detail="diagram upsert failed"
            elif [[ -n "${UPSERT_STATUS:-}" ]]; then
                _diagram_detail="diagram upsert status=${UPSERT_STATUS}"
            else
                _diagram_detail="diagram upsert ran without UPSERT_STATUS"
            fi
        fi
        add_warn "**⚠ 5c: [DESIGNED] rename failed (tracking-issue-write.sh); plan block was written; ${_diagram_detail}; the issue title was not updated. Rename manually with gh issue edit or tracking-issue-write.sh, or drop the lifecycle prefix before re-running /design.**"
    fi
fi

if [[ -n "$SESSION_ID" ]]; then
    render_fresh_timing_report_for_publish
    rm -f "$FINAL_SUMMARY_PATH" 2>/dev/null || true
    set +e
    _publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --run-id "$SESSION_ID" \
        --issue "$ISSUE" \
        ${REPO:+--repo "$REPO"} 2>"$DESIGN_TMPDIR/design-log-publish.failure.log")
    _publish_rc=$?
    set -e
    PUBLISH_OK=""
    PR_NUMBER=""
    PR_URL=""
    RECOVERY_BRANCH=""
    parse_kv_from_output "$_publish_out"
    _scrub_n="$(printf '%s\n' "$_publish_out" | sed -n 's/^SECRET_SCRUB_VIOLATIONS=//p' | tail -1)"
    case "${_scrub_n:-}" in ''|*[!0-9]*) _scrub_n=0 ;; esac
    if [[ "$_scrub_n" -gt 0 ]]; then
        add_warn "**⚠ SECURITY: scrub-log-secrets.sh redacted ${_scrub_n} secret-shaped value(s) from this /design run's logs before flush. A credential was almost certainly exposed in the session — ROTATE it now and check chat/PRs for the same value.**"
    fi
    if [[ "$_publish_rc" -ne 0 ]]; then
        sanitize_publish_metadata
        PUBLISH_OK=false
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c" \
            --tool "design-log-publish.sh" \
            --exit-code "$_publish_rc" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/design-log-publish.failure.log" \
            --redact >/dev/null 2>&1 || true
        add_warn "**⚠ 5c: design log publish failed; recovery metadata: $(publish_recovery_detail).**"
    elif [[ "${PUBLISH_OK:-}" == false ]]; then
        sanitize_publish_metadata
        _publish_failure_rc=${_publish_rc:-1}
        if [[ "$_publish_failure_rc" -eq 0 ]]; then
            _publish_failure_rc=1
        fi
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c" \
            --tool "design-log-publish.sh" \
            --exit-code "$_publish_failure_rc" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/design-log-publish.failure.log" \
            --redact >/dev/null 2>&1 || true
        add_warn "**⚠ 5c: design log publish failed; recovery metadata: $(publish_recovery_detail).**"
    elif [[ -z "${PUBLISH_OK:-}" ]]; then
        PUBLISH_OK=false
        sanitize_publish_metadata
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c" \
            --tool "design-log-publish.sh" \
            --exit-code "${_publish_rc:-0}" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/design-log-publish.failure.log" \
            --redact >/dev/null 2>&1 || true
        add_warn '**⚠ 5c: design-log-publish.sh returned without PUBLISH_OK=; treating publish as failed**'
        add_warn "**⚠ 5c: design log publish failed; recovery metadata: $(publish_recovery_detail).**"
    else
        sanitize_publish_metadata
    fi
else
    add_warn '**⚠ /design: SESSION_ID missing; skipping design log publish**'
fi

SUMMARY_OUTCOME=approved
if [[ -z "$SESSION_ID" ]]; then
    SUMMARY_OUTCOME=publish-skipped
elif [[ "${PUBLISH_OK:-}" != true ]]; then
    SUMMARY_OUTCOME=failed-publish
fi
export DESIGN_LOG_PR_NUMBER="${PR_NUMBER:-}"
export DESIGN_LOG_PR_URL="${PR_URL:-}"
export DESIGN_LOG_RECOVERY_BRANCH="${RECOVERY_BRANCH:-}"
export RENAMED="${RENAMED:-}"
export NEW_TITLE="${NEW_TITLE:-}"
export UPSERT_RAN="${UPSERT_RAN:-false}"
export UPSERT_STATUS="${UPSERT_STATUS:-}"
refresh_designed_admission_ready
export DESIGNED_ADMISSION_READY
"${PLUGIN_ROOT}/skills/design/scripts/render-final-summary.sh" \
    --outcome "$SUMMARY_OUTCOME" \
    --mode "$MODE" \
    ${REPO:+--repo "$REPO"} \
    --post-publish-only || true

if [[ -n "$SESSION_ID" ]] && [[ "${PUBLISH_OK:-}" == true ]]; then
    # shellcheck source=scripts/lib-design-reentry-guard.sh
    source "$PLUGIN_ROOT/scripts/lib-design-reentry-guard.sh"
    set +e
    design_reentry_marker_write "$ISSUE" "$CLAUDE_PID" 2>"$DESIGN_TMPDIR/design-reentry-marker-write.failure.log"
    _marker_rc=$?
    if [[ "$_marker_rc" -ne 0 ]]; then
        "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 5c marker write" \
            --tool "design_reentry_marker_write" \
            --exit-code "$_marker_rc" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/design-reentry-marker-write.failure.log" \
            --redact >/dev/null 2>&1 || true
    fi
    set -e
fi

if ! write_result_env_and_emit; then
    exit 3
fi
exit 0
