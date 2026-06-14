#!/usr/bin/env bash
# design-clarify.sh — /design Step 0b clarify fetch/publish phase driver.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

SESSION_ENV_PATH=""
CLAUDE_PID=""
PHASE=""
ISSUE=""

CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
SESSION_ID="${SESSION_ID:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
REPO="${REPO:-}"

usage() {
    printf '%s\n' 'Usage: design-clarify.sh --phase fetch|publish --issue N' >&2
}

fail() {
    printf '%s\n' "design-clarify.sh: $*" >&2
    exit 2
}

validate_positive_int() {
    local label="$1" value="$2"
    case "$value" in
        '' | *[!0-9]*) fail "$label must be a positive integer" ;;
    esac
    [[ "$value" != "0" ]] || fail "$label must be a positive integer"
}

validate_repo() {
    local value="$1"
    case "$value" in
        '' | --* | *$'\n'* | *$'\r'* | /* | *../* | *\\*) fail 'invalid --repo' ;;
    esac
    [[ "$value" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || fail 'invalid --repo'
}

write_result_env() {
    local path="$1"
    shift
    [[ ! -L "$path" ]] || fail "refusing symlink result env: $path"
    local tmp
    tmp="$(mktemp "${path}.XXXXXX")" || fail "could not allocate result env temp: $path"
    : >"$tmp"
    local kv
    for kv in "$@"; do
        case "$kv" in
            *$'\n'* | *$'\r'*)
                rm -f "$tmp"
                fail "refusing result env value with newline"
                ;;
        esac
        printf '%s\n' "$kv" >>"$tmp"
    done
    mv "$tmp" "$path"
}

emit_kvs() {
    local kv
    for kv in "$@"; do
        printf '%s\n' "$kv"
    done
}

source_env_optional() {
    if [[ -n "$SESSION_ENV_PATH" && -f "$SESSION_ENV_PATH" ]]; then
        # shellcheck source=/dev/null
        . "$SESSION_ENV_PATH"
    fi
}

load_route_state_repo_fallback() {
    [[ -z "${REPO:-}" ]] || return 0
    [[ -n "${DESIGN_TMPDIR:-}" && -f "$DESIGN_TMPDIR/.design-step0-route-state.env" ]] || return 0
    local safe_route_state
    safe_route_state="$(mktemp "${TMPDIR:-/tmp}/larch-clarify-route-state.XXXXXX")" || fail 'could not allocate route state temp'
    set +e
    "$CLAUDE_PLUGIN_ROOT/scripts/read-result-env.sh" \
        --input "$DESIGN_TMPDIR/.design-step0-route-state.env" \
        --allow REPO \
        --output "$safe_route_state"
    local route_state_rc=$?
    set -e
    if [[ "$route_state_rc" -ne 0 ]]; then
        rm -f "$safe_route_state"
        fail 'could not read route state sidecar'
    fi
    # shellcheck source=/dev/null
    . "$safe_route_state"
    rm -f "$safe_route_state"
}

read_safe_env() {
    local input="$1" output="$2"
    shift 2
    set +e
    "$CLAUDE_PLUGIN_ROOT/scripts/read-result-env.sh" \
        --input "$input" \
        "$@" \
        --output "$output"
    local rc=$?
    set -e
    return "$rc"
}

stage_failed_clarify() {
    local exit_code="$1" detail_log="$2"
    [[ -f "$detail_log" ]] || printf 'clarify failure\n' >"$detail_log"
    set +e
    "$CLAUDE_PLUGIN_ROOT/skills/design/scripts/design-stage-terminal-state.sh" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --outcome failed-clarify \
        --step clarify \
        --phase clarify-loop \
        --site clarify-loop \
        --trigger failed \
        --bail-reason clarify-fetch-failed \
        --exit-code "$exit_code" \
        --source-script design-clarify \
        --summary-outcome failed-clarify \
        --failure-detail-log "$detail_log" \
        >"$DESIGN_TMPDIR/design-clarify-stage.stdout.log" \
        2>"$DESIGN_TMPDIR/design-clarify-stage.stderr.log"
    local stage_rc=$?
    set -e
    if [[ "$stage_rc" -ne 0 ]]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 0b clarify fetch" \
            --tool "design-stage-terminal-state.sh" \
            --exit-code "$stage_rc" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/design-clarify-stage.stderr.log" \
            --redact >/dev/null 2>&1 || true
    fi
}

parse_publish_ok() {
    local text="${1:-}" line key value
    PUBLISH_OK=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        key="${line%%=*}"
        value="${line#*=}"
        case "$key" in
            PUBLISH_OK) PUBLISH_OK="$value" ;;
        esac
    done <<<"$text"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --session-env-path) [[ $# -ge 2 ]] || fail '--session-env-path requires a value'; SESSION_ENV_PATH="$2"; shift 2 ;;
        --claude-pid) [[ $# -ge 2 ]] || fail '--claude-pid requires a value'; CLAUDE_PID="$2"; shift 2 ;;
        --phase) [[ $# -ge 2 ]] || fail '--phase requires a value'; PHASE="$2"; shift 2 ;;
        --issue) [[ $# -ge 2 ]] || fail '--issue requires a value'; ISSUE="$2"; shift 2 ;;
        -h | --help) usage; exit 0 ;;
        *) usage; fail "unknown option: $1" ;;
    esac
done

[[ -n "$PHASE" ]] || { usage; fail '--phase is required'; }
case "$PHASE" in
    fetch | publish) ;;
    *) fail '--phase must be fetch or publish' ;;
esac
[[ -n "$ISSUE" ]] || { usage; fail '--issue is required'; }
validate_positive_int --issue "$ISSUE"
[[ -n "$CLAUDE_PID" ]] && validate_positive_int --claude-pid "$CLAUDE_PID"

source_env_optional
if [[ -z "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
    CLAUDE_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
fi
export CLAUDE_PLUGIN_ROOT
[[ -n "${DESIGN_TMPDIR:-}" ]] || fail 'DESIGN_TMPDIR required'
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
export DESIGN_TMPDIR
ISSUE_NUMBER="$ISSUE"
export ISSUE_NUMBER
load_route_state_repo_fallback
[[ -z "${REPO:-}" ]] || validate_repo "$REPO"

if [[ -f "$DESIGN_TMPDIR/.pause-requested" ]]; then
    exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE" ${REPO:+--repo "$REPO"}
fi

FETCH_RESULT_ENV="$DESIGN_TMPDIR/.design-clarify-fetch-result.env"
PUBLISH_RESULT_ENV="$DESIGN_TMPDIR/.design-clarify-publish-result.env"
REQUEST_STATE_ENV="$DESIGN_TMPDIR/.design-clarify-request.env"
REQUEST_BODY_FILE="$DESIGN_TMPDIR/clarify-request.md"
PLAN_FILE="$DESIGN_TMPDIR/clarify-plan.md"
RESPONSE_FILE="$DESIGN_TMPDIR/clarify-response.md"

if [[ "$PHASE" == fetch ]]; then
    state_stdout="$DESIGN_TMPDIR/clarify-state.stdout"
    state_stderr="$DESIGN_TMPDIR/clarify-state.stderr"
    set +e
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" clarify state --issue "$ISSUE" ${REPO:+--repo "$REPO"} >"$state_stdout" 2>"$state_stderr"
    state_rc=$?
    set -e
    safe_state="$(mktemp "${TMPDIR:-/tmp}/larch-clarify-state.XXXXXX")" || fail 'could not allocate clarify state env'
    if ! read_safe_env "$state_stdout" "$safe_state" --allow FAILED --allow ERROR --allow STATE --allow LAST_REQUEST_ID --allow LAST_RESPONSE_ID; then
        rm -f "$safe_state"
        write_result_env "$FETCH_RESULT_ENV" "CLARIFY_FETCH_STATUS=state-read-failed" "SUMMARY_OUTCOME=failed-clarify"
        stage_failed_clarify 1 "$state_stderr"
        emit_kvs "CLARIFY_FETCH_STATUS=state-read-failed" "SUMMARY_OUTCOME=failed-clarify"
        exit 1
    fi
    # shellcheck source=/dev/null
    . "$safe_state"
    rm -f "$safe_state"
    if [[ "$state_rc" -ne 0 || "${FAILED:-false}" == true ]]; then
        write_result_env "$FETCH_RESULT_ENV" "CLARIFY_FETCH_STATUS=state-failed" "SUMMARY_OUTCOME=failed-clarify"
        stage_failed_clarify "$state_rc" "$state_stderr"
        emit_kvs "CLARIFY_FETCH_STATUS=state-failed" "SUMMARY_OUTCOME=failed-clarify"
        exit 1
    fi
    if [[ "${STATE:-}" != awaiting-response || -z "${LAST_REQUEST_ID:-}" ]]; then
        printf 'unexpected clarify state: %s\n' "${STATE:-<empty>}" >"$DESIGN_TMPDIR/clarify-fetch.failure.log"
        write_result_env "$FETCH_RESULT_ENV" "CLARIFY_FETCH_STATUS=unexpected-state" "STATE=${STATE:-}" "SUMMARY_OUTCOME=failed-clarify"
        stage_failed_clarify 1 "$DESIGN_TMPDIR/clarify-fetch.failure.log"
        emit_kvs "CLARIFY_FETCH_STATUS=unexpected-state" "STATE=${STATE:-}" "SUMMARY_OUTCOME=failed-clarify"
        exit 1
    fi
    fetch_stdout="$DESIGN_TMPDIR/clarify-comment-fetch.stdout"
    fetch_stderr="$DESIGN_TMPDIR/clarify-comment-fetch.stderr"
    set +e
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" clarify comment-fetch \
        --issue "$ISSUE" \
        --id "$LAST_REQUEST_ID" \
        --out "$REQUEST_BODY_FILE" \
        ${REPO:+--repo "$REPO"} >"$fetch_stdout" 2>"$fetch_stderr"
    fetch_rc=$?
    set -e
    safe_fetch="$(mktemp "${TMPDIR:-/tmp}/larch-clarify-fetch.XXXXXX")" || fail 'could not allocate comment fetch env'
    if ! read_safe_env "$fetch_stdout" "$safe_fetch" --allow FAILED --allow ERROR --allow FETCHED --allow COMMENT_ID --allow BODY_FILE; then
        rm -f "$safe_fetch"
        write_result_env "$FETCH_RESULT_ENV" "CLARIFY_FETCH_STATUS=fetch-read-failed" "SUMMARY_OUTCOME=failed-clarify"
        stage_failed_clarify 1 "$fetch_stderr"
        emit_kvs "CLARIFY_FETCH_STATUS=fetch-read-failed" "SUMMARY_OUTCOME=failed-clarify"
        exit 1
    fi
    # shellcheck source=/dev/null
    . "$safe_fetch"
    rm -f "$safe_fetch"
    if [[ "$fetch_rc" -ne 0 || "${FAILED:-false}" == true || "${FETCHED:-false}" != true ]]; then
        write_result_env "$FETCH_RESULT_ENV" "CLARIFY_FETCH_STATUS=fetch-failed" "SUMMARY_OUTCOME=failed-clarify"
        stage_failed_clarify "$fetch_rc" "$fetch_stderr"
        emit_kvs "CLARIFY_FETCH_STATUS=fetch-failed" "SUMMARY_OUTCOME=failed-clarify"
        exit 1
    fi
    write_result_env "$REQUEST_STATE_ENV" \
        "REQUEST_ID=$LAST_REQUEST_ID" \
        "REQUEST_BODY_FILE=$REQUEST_BODY_FILE" \
        "PLAN_FILE=$PLAN_FILE" \
        "RESPONSE_FILE=$RESPONSE_FILE" \
        "ISSUE_NUMBER=$ISSUE" \
        ${REPO:+"REPO=$REPO"}
    write_result_env "$FETCH_RESULT_ENV" \
        "CLARIFY_FETCH_STATUS=ok" \
        "REQUEST_ID=$LAST_REQUEST_ID" \
        "REQUEST_BODY_FILE=$REQUEST_BODY_FILE" \
        "PLAN_FILE=$PLAN_FILE" \
        "RESPONSE_FILE=$RESPONSE_FILE" \
        "ISSUE_NUMBER=$ISSUE" \
        ${REPO:+"REPO=$REPO"}
    emit_kvs \
        "CLARIFY_FETCH_STATUS=ok" \
        "REQUEST_ID=$LAST_REQUEST_ID" \
        "REQUEST_BODY_FILE=$REQUEST_BODY_FILE" \
        "PLAN_FILE=$PLAN_FILE" \
        "RESPONSE_FILE=$RESPONSE_FILE" \
        "ISSUE_NUMBER=$ISSUE" \
        ${REPO:+"REPO=$REPO"}
    exit 0
fi

safe_request="$(mktemp "${TMPDIR:-/tmp}/larch-clarify-request.XXXXXX")" || fail 'could not allocate request state env'
if ! read_safe_env "$REQUEST_STATE_ENV" "$safe_request" --allow REQUEST_ID --allow REQUEST_BODY_FILE --allow PLAN_FILE --allow RESPONSE_FILE --allow ISSUE_NUMBER --allow REPO; then
    rm -f "$safe_request"
    write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=missing-request-state" "SUMMARY_OUTCOME=failed-clarify"
    emit_kvs "CLARIFY_PUBLISH_STATUS=missing-request-state" "SUMMARY_OUTCOME=failed-clarify"
    exit 1
fi
# shellcheck source=/dev/null
. "$safe_request"
rm -f "$safe_request"
ISSUE_NUMBER="$ISSUE"
validate_positive_int REQUEST_ID "${REQUEST_ID:-}"
[[ -z "${REPO:-}" ]] || validate_repo "$REPO"

for required_file in "$PLAN_FILE" "$RESPONSE_FILE"; do
    if [[ -L "$required_file" || ! -s "$required_file" || ! -r "$required_file" ]]; then
        write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=missing-artifact" "SUMMARY_OUTCOME=failed-clarify"
        emit_kvs "CLARIFY_PUBLISH_STATUS=missing-artifact" "SUMMARY_OUTCOME=failed-clarify"
        exit 1
    fi
done

PLAN_REDACTED="$DESIGN_TMPDIR/clarify-plan.redacted.md"
if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" redact secrets <"$PLAN_FILE" >"$PLAN_REDACTED"; then
    write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=redact-failed" "SUMMARY_OUTCOME=failed-plan-write"
    emit_kvs "CLARIFY_PUBLISH_STATUS=redact-failed" "SUMMARY_OUTCOME=failed-plan-write"
    exit 1
fi
if [[ ! -s "$PLAN_REDACTED" ]]; then
    write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=redact-empty" "SUMMARY_OUTCOME=failed-plan-write"
    emit_kvs "CLARIFY_PUBLISH_STATUS=redact-empty" "SUMMARY_OUTCOME=failed-plan-write"
    exit 1
fi

plan_write_stdout="$DESIGN_TMPDIR/clarify-plan-write.stdout"
plan_write_stderr="$DESIGN_TMPDIR/clarify-plan-write.stderr"
set +e
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" named-block write \
    --marker plan \
    --issue "$ISSUE" \
    --content-file "$PLAN_REDACTED" \
    ${REPO:+--repo "$REPO"} >"$plan_write_stdout" 2>"$plan_write_stderr"
plan_write_rc=$?
set -e
if [[ "$plan_write_rc" -ne 0 ]]; then
    printf 'plan-block write failed\n' >"$DESIGN_TMPDIR/clarify-plan-write.failure.log"
    write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=plan-write-failed" "PLAN_WRITE_OK=false" "SUMMARY_OUTCOME=failed-plan-write"
    emit_kvs "CLARIFY_PUBLISH_STATUS=plan-write-failed" "PLAN_WRITE_OK=false" "SUMMARY_OUTCOME=failed-plan-write"
    exit 1
fi

PUBLISH_OK=false
publish_rc=0
if [[ -n "${SESSION_ID:-}" ]]; then
    set +e
    publish_out=$("$CLAUDE_PLUGIN_ROOT/scripts/design-log-publish.sh" \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --run-id "$SESSION_ID" \
        --issue "$ISSUE" \
        ${REPO:+--repo "$REPO"} 2>"$DESIGN_TMPDIR/design-log-publish.failure.log")
    publish_rc=$?
    set -e
    printf '%s\n' "$publish_out" >"$DESIGN_TMPDIR/design-log-publish.stdout"
    parse_publish_ok "$publish_out"
    if [[ "$publish_rc" -ne 0 ]]; then
        PUBLISH_OK=false
    elif [[ "${PUBLISH_OK:-}" != true ]]; then
        PUBLISH_OK=false
    fi
    if [[ "$PUBLISH_OK" != true ]]; then
        failure_exit="$publish_rc"
        [[ "$failure_exit" -eq 0 ]] && failure_exit=1
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 0b clarify publish" \
            --tool "design-log-publish.sh" \
            --exit-code "$failure_exit" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/design-log-publish.failure.log" \
            --redact >/dev/null 2>&1 || true
    fi
else
    printf '\n**⚠ /design: SESSION_ID missing; skipping design log publish**\n'
fi

comment_stdout="$DESIGN_TMPDIR/clarify-comment-post.stdout"
comment_stderr="$DESIGN_TMPDIR/clarify-comment-post.stderr"
set +e
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" clarify comment-post \
    --issue "$ISSUE" \
    --kind response \
    --id "$REQUEST_ID" \
    --content-file "$RESPONSE_FILE" \
    ${REPO:+--repo "$REPO"} >"$comment_stdout" 2>"$comment_stderr"
comment_rc=$?
set -e
if [[ "$comment_rc" -ne 0 ]]; then
    write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=comment-post-failed" "PLAN_WRITE_OK=true" "PUBLISH_OK=$PUBLISH_OK" "SUMMARY_OUTCOME=failed-clarify"
    emit_kvs "CLARIFY_PUBLISH_STATUS=comment-post-failed" "PLAN_WRITE_OK=true" "PUBLISH_OK=$PUBLISH_OK" "SUMMARY_OUTCOME=failed-clarify"
    exit 1
fi

label_stdout="$DESIGN_TMPDIR/clarify-label-remove.stdout"
label_stderr="$DESIGN_TMPDIR/clarify-label-remove.stderr"
set +e
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" clarify label \
    --issue "$ISSUE" \
    --action remove \
    ${REPO:+--repo "$REPO"} >"$label_stdout" 2>"$label_stderr"
label_rc=$?
set -e
if [[ "$label_rc" -ne 0 ]]; then
    write_result_env "$PUBLISH_RESULT_ENV" "CLARIFY_PUBLISH_STATUS=label-remove-failed" "PLAN_WRITE_OK=true" "PUBLISH_OK=$PUBLISH_OK" "SUMMARY_OUTCOME=failed-clarify"
    emit_kvs "CLARIFY_PUBLISH_STATUS=label-remove-failed" "PLAN_WRITE_OK=true" "PUBLISH_OK=$PUBLISH_OK" "SUMMARY_OUTCOME=failed-clarify"
    exit 1
fi

RENAMED=""
if [[ -n "${SESSION_ID:-}" && "$PUBLISH_OK" == true ]]; then
    set +e
    rename_out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue rename --issue "$ISSUE" --state designing ${REPO:+--repo "$REPO"} 2>"$DESIGN_TMPDIR/clarify-rename.stderr")
    rename_rc=$?
    set -e
    printf '%s\n' "$rename_out" >"$DESIGN_TMPDIR/clarify-rename.stdout"
    if [[ "$rename_rc" -eq 0 ]]; then
        RENAMED=$(printf '%s\n' "$rename_out" | sed -n 's/^RENAMED=//p' | tail -1)
    else
        RENAMED=false
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
            --log "$DESIGN_TMPDIR/execution-issues.md" \
            --site "design Step 0b clarify rename" \
            --tool "python/cli.py tracking-issue rename" \
            --exit-code "$rename_rc" \
            --category Warnings \
            --output-file "$DESIGN_TMPDIR/clarify-rename.stderr" \
            --redact >/dev/null 2>&1 || true
    fi
fi

write_result_env "$PUBLISH_RESULT_ENV" \
    "CLARIFY_PUBLISH_STATUS=ok" \
    "PLAN_WRITE_OK=true" \
    "PUBLISH_OK=$PUBLISH_OK" \
    "RENAMED=$RENAMED" \
    "SUMMARY_OUTCOME=cancelled-clarify"
emit_kvs \
    "CLARIFY_PUBLISH_STATUS=ok" \
    "PLAN_WRITE_OK=true" \
    "PUBLISH_OK=$PUBLISH_OK" \
    "RENAMED=$RENAMED" \
    "SUMMARY_OUTCOME=cancelled-clarify"
