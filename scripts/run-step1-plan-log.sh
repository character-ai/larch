#!/usr/bin/env bash
# run-step1-plan-log.sh - Compose and write the /implement Step 1 plan batch.

set -euo pipefail

fail() {
    printf 'run-step1-plan-log.sh: %s\n' "$1" >&2
    exit 2
}

append_log_write_failure() {
    local site="$1" tool="$2" output_file="$3"
    local helper="$PLUGIN_ROOT/scripts/append-tool-failure.sh"
    if [[ -x "$helper" ]]; then
        "$helper" \
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

PLAN_FILE="$(session_get "$SESSION_ENV_PATH" PLAN_FILE "")"
if [[ -z "$PLAN_FILE" ]]; then
    fail "PLAN_FILE missing from session-env; fix scripts/persist-post-plan-keys.sh (or other session-env writers). Issue-anchored runs must not recover from design-export/plan.txt."
fi
[[ -f "$PLAN_FILE" ]] || fail "PLAN_FILE not found: $PLAN_FILE"

COMPOSE_SH="${RUN_STEP1_COMPOSE_SH:-$PLUGIN_ROOT/scripts/compose-plan-goals-test.sh}"
LARCH_LOG_SH="${RUN_STEP1_LARCH_LOG_SH:-$PLUGIN_ROOT/scripts/larch-log.sh}"
[[ -x "$COMPOSE_SH" ]] || fail "compose-plan-goals-test.sh not executable: $COMPOSE_SH"
[[ -x "$LARCH_LOG_SH" ]] || fail "larch-log.sh not executable: $LARCH_LOG_SH"

OUTPUT_FILE="$IMPLEMENT_TMPDIR/plan-goals-test.md"
OUTPUT_TMP="$(mktemp "$IMPLEMENT_TMPDIR/plan-goals-test.md.tmp.XXXXXX")"
cleanup() {
    rm -f "$OUTPUT_TMP"
}
trap cleanup EXIT

"$COMPOSE_SH" --plan-file "$PLAN_FILE" --goal-text "$GOAL_TEXT" > "$OUTPUT_TMP"
mv "$OUTPUT_TMP" "$OUTPUT_FILE"
trap - EXIT

"$LARCH_LOG_SH" write \
    --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
    --skill implement \
    --run-id "$RUN_ID" \
    --batch plan-goals-test \
    --input-file "$OUTPUT_FILE"

if [[ -f "$IMPLEMENT_TMPDIR/parent-issue.md" ]]; then
    parent_issue_fail_log="$IMPLEMENT_TMPDIR/parent-issue-write.failure.log"
    if ! "$LARCH_LOG_SH" write \
        --log-root "$IMPLEMENT_TMPDIR/larch-logs" \
        --skill implement \
        --run-id "$RUN_ID" \
        --batch parent-issue \
        --input-file "$IMPLEMENT_TMPDIR/parent-issue.md" >"$parent_issue_fail_log" 2>&1; then
        append_log_write_failure "1" "larch-log.sh write parent-issue" "$parent_issue_fail_log"
    fi
fi
