#!/usr/bin/env bash
# run-step1-plan-log.sh - Compose and write the /implement Step 1 plan batch.

set -euo pipefail

fail() {
    printf 'run-step1-plan-log.sh: %s\n' "$1" >&2
    exit 2
}

append_log_write_failure() {
    local site="$1" tool="$2" output_file="$3"
    local helper="$PLUGIN_ROOT/python/cli.py"
    if [[ -f "$helper" ]]; then
        python3 "$helper" run-log append-failure \
            --log "$IMPLEMENT_TMPDIR/execution-issues.md" \
            --site "$site" \
            --tool "$tool" \
            --exit-code 1 \
            --category Warnings \
            --output-file "$output_file" \
            --redact >/dev/null 2>&1 || true
    else
        printf 'run-step1-plan-log.sh: best-effort log write failed for %s (see %s)\n' "$tool" "$output_file" >&2
    fi
}

usage() {
    printf 'Usage: run-step1-plan-log.sh --implement-tmpdir PATH --goal-text TEXT\n' >&2
}

session_get() {
    local file="$1" key="$2" default_value="${3-}" value
    value=$(awk -v k="$key" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$file" 2>/dev/null || true)
    if [[ -z "$value" ]]; then
        printf '%s\n' "$default_value"
    else
        printf '%s\n' "$value"
    fi
}

resolve_run_id() {
    local session_env_path="$1" implement_tmpdir="$2" session_id_file="$3"
    local run_id="" candidate="" manifest_count=0

    run_id="$(session_get "$session_env_path" RUN_ID "")"
    if [[ -z "$run_id" ]]; then
        run_id="$(session_get "$implement_tmpdir/parent-issue.md" RUN_ID "")"
    fi
    if [[ -z "$run_id" && -d "$implement_tmpdir/larch-logs/implement" ]]; then
        for candidate in "$implement_tmpdir"/larch-logs/implement/*/manifest.json; do
            [[ -f "$candidate" ]] || continue
            manifest_count=$((manifest_count + 1))
            run_id="$(basename "$(dirname "$candidate")")"
            if (( manifest_count > 1 )); then
                run_id=""
                break
            fi
        done
    fi
    if [[ -z "$run_id" && -s "$session_id_file" ]]; then
        run_id="$(tr -d '\r\n' < "$session_id_file" 2>/dev/null || true)"
    fi
    printf '%s\n' "$run_id"
}

IMPLEMENT_TMPDIR_ARG=""
GOAL_TEXT=""
GOAL_TEXT_SET=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --implement-tmpdir)
            [[ $# -ge 2 ]] || fail "--implement-tmpdir requires a value"
            IMPLEMENT_TMPDIR_ARG="$2"
            shift 2
            ;;
        --goal-text)
            [[ $# -ge 2 ]] || fail "--goal-text requires a value"
            GOAL_TEXT="$2"
            GOAL_TEXT_SET=true
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$IMPLEMENT_TMPDIR_ARG" ]] || { usage; fail "--implement-tmpdir is required"; }
[[ "$GOAL_TEXT_SET" == "true" ]] || { usage; fail "--goal-text is required"; }
[[ -d "$IMPLEMENT_TMPDIR_ARG" ]] || fail "--implement-tmpdir not a directory: $IMPLEMENT_TMPDIR_ARG"

IMPLEMENT_TMPDIR="$(cd "$IMPLEMENT_TMPDIR_ARG" && pwd -P)"
SESSION_ENV_PATH="$IMPLEMENT_TMPDIR/session-env.sh"
SESSION_ID_FILE="$IMPLEMENT_TMPDIR/session-id"
[[ -r "$SESSION_ENV_PATH" ]] || fail "session-env not readable: $SESSION_ENV_PATH"

RUN_ID="$(resolve_run_id "$SESSION_ENV_PATH" "$IMPLEMENT_TMPDIR" "$SESSION_ID_FILE")"
[[ -n "$RUN_ID" ]] || fail "RUN_ID unresolved from session-env, parent-issue, manifest, or session-id"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(session_get "$SESSION_ENV_PATH" LARCH_CLAUDE_PLUGIN_ROOT "")}"
if [[ -z "$PLUGIN_ROOT" ]]; then
    PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export IMPLEMENT_TMPDIR

PLAN_FILE="$IMPLEMENT_TMPDIR/plan.txt"
[[ -f "$PLAN_FILE" ]] || fail "plan file not found at conventional path: $PLAN_FILE"

if [[ -n "${RUN_STEP1_COMPOSE_CMD:-}" ]]; then
    # shellcheck disable=SC2206 # test override intentionally supplies a command word list.
    COMPOSE_CMD=($RUN_STEP1_COMPOSE_CMD)
else
    COMPOSE_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" plan compose-goals-test)
fi
if [[ -n "${RUN_STEP1_LARCH_LOG_SH:-}" ]]; then
    LARCH_LOG_CMD=("$RUN_STEP1_LARCH_LOG_SH")
    [[ -x "${LARCH_LOG_CMD[0]}" ]] || fail "run-log override not executable: ${LARCH_LOG_CMD[0]}"
else
    LARCH_LOG_CMD=(python3 "$PLUGIN_ROOT/python/cli.py" run-log)
    command -v python3 >/dev/null 2>&1 || fail "python3 not found"
    [[ -f "$PLUGIN_ROOT/python/cli.py" ]] || fail "python CLI missing: $PLUGIN_ROOT/python/cli.py"
fi

OUTPUT_FILE="$IMPLEMENT_TMPDIR/plan-goals-test.md"
OUTPUT_TMP="$(mktemp "$IMPLEMENT_TMPDIR/plan-goals-test.md.tmp.XXXXXX")"
cleanup() {
    rm -f "$OUTPUT_TMP"
}
trap cleanup EXIT

"${COMPOSE_CMD[@]}" --plan-file "$PLAN_FILE" --goal-text "$GOAL_TEXT" > "$OUTPUT_TMP"
mv "$OUTPUT_TMP" "$OUTPUT_FILE"
trap - EXIT

"${LARCH_LOG_CMD[@]}" write \
    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
    --skill implement \
    --run-id "$RUN_ID" \
    --batch plan-goals-test \
    --input-file "$OUTPUT_FILE"

if [[ -f "$IMPLEMENT_TMPDIR/parent-issue.md" ]]; then
    parent_issue_fail_log="$IMPLEMENT_TMPDIR/parent-issue-write.failure.log"
    if ! "${LARCH_LOG_CMD[@]}" write \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --batch parent-issue \
        --input-file "$IMPLEMENT_TMPDIR/parent-issue.md" >"$parent_issue_fail_log" 2>&1; then
        append_log_write_failure "1" "python3 python/cli.py run-log write parent-issue" "$parent_issue_fail_log"
    fi
fi
