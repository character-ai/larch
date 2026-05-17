#!/usr/bin/env bash
# flush-execution-issues.sh — append execution-issues.md to the run log.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# shellcheck source=scripts/lib-execution-issues.sh
source "$PLUGIN_ROOT/scripts/lib-execution-issues.sh"

usage() {
    larch_err "Usage: flush-execution-issues.sh --log-root PATH --run-id RUN_ID --issue-log PATH [--batch execution-issues]"
}

fail_usage() {
    usage
    emit_kv FLUSH_STATUS failed
    emit_kv RECORDS 0
    emit_kv ERROR "$1"
    exit 2
}

LOG_ROOT=""
RUN_ID=""
ISSUE_LOG=""
BATCH="execution-issues"

while [ $# -gt 0 ]; do
    case "$1" in
        --log-root)
            [ $# -ge 2 ] || fail_usage "--log-root requires a value"
            LOG_ROOT=$2
            shift 2
            ;;
        --run-id)
            [ $# -ge 2 ] || fail_usage "--run-id requires a value"
            RUN_ID=$2
            shift 2
            ;;
        --issue-log)
            [ $# -ge 2 ] || fail_usage "--issue-log requires a value"
            ISSUE_LOG=$2
            shift 2
            ;;
        --batch)
            [ $# -ge 2 ] || fail_usage "--batch requires a value"
            BATCH=$2
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            fail_usage "unknown option: $1"
            ;;
    esac
done

[ -n "$LOG_ROOT" ] || fail_usage "--log-root is required"
[ -n "$RUN_ID" ] || fail_usage "--run-id is required"
case "$LOG_ROOT" in
    /*) ;;
    *) fail_usage "--log-root must be absolute" ;;
esac
case "$RUN_ID" in
    ""|*[!A-Za-z0-9-]*) fail_usage "--run-id must contain only letters, numbers, and hyphens" ;;
esac
[ "$BATCH" = "execution-issues" ] || fail_usage "--batch must be execution-issues"

if [ -z "$ISSUE_LOG" ] || [ ! -s "$ISSUE_LOG" ]; then
    emit_kv FLUSH_STATUS skip
    emit_kv RECORDS 0
    exit 0
fi

sha=$(sha256_file "$ISSUE_LOG" 2>/dev/null || true)
if [ -z "$sha" ]; then
    emit_kv FLUSH_STATUS skip
    emit_kv RECORDS 0
    exit 0
fi

sentinel_dir="${IMPLEMENT_TMPDIR:-$(dirname "$ISSUE_LOG")}"
sentinel="$sentinel_dir/.execution-issues-flushed.sha"
if [ -f "$sentinel" ] && [ "$(cat "$sentinel" 2>/dev/null || true)" = "$sha" ]; then
    emit_kv FLUSH_STATUS already-flushed
    emit_kv RECORDS 0
    exit 0
fi

batch_path="$LOG_ROOT/implement/$RUN_ID/execution-issues.ndjson"
if [ -f "$batch_path" ] && grep -Fq '"source_sha256":"'"$sha"'"' "$batch_path" 2>/dev/null; then
    printf '%s\n' "$sha" > "$sentinel" 2>/dev/null || true
    emit_kv FLUSH_STATUS already-flushed
    emit_kv RECORDS 0
    exit 0
fi

tmp_base="$sentinel_dir"
[ -d "$tmp_base" ] || tmp_base="${TMPDIR:-/tmp}"
record_file=""
append_log_tmp=""
# shellcheck disable=SC2317  # trap-only function; called indirectly on EXIT
cleanup() {
    rm -f "$record_file" "$append_log_tmp"
}
trap cleanup EXIT
record_file=$(mktemp "$tmp_base/flush-execution-issues-record.XXXXXX") || {
    emit_kv FLUSH_STATUS failed
    emit_kv RECORDS 0
    emit_kv ERROR "cannot create record temp"
    exit 1
}
append_log_tmp=$(mktemp "$tmp_base/flush-execution-issues-append.XXXXXX") || {
    emit_kv FLUSH_STATUS failed
    emit_kv RECORDS 0
    emit_kv ERROR "cannot create append log temp"
    exit 1
}

if ! write_execution_issues_records "$ISSUE_LOG" "$record_file" "$sha" "$batch_path" "7a" "execution-issues.md pre-bump"; then
    emit_kv FLUSH_STATUS failed
    emit_kv RECORDS 0
    emit_kv APPEND_LOG_FILE "$append_log_tmp"
    exit 1
fi

if [ ! -s "$record_file" ]; then
    printf '%s\n' "$sha" > "$sentinel" 2>/dev/null || true
    emit_kv FLUSH_STATUS no-records
    emit_kv RECORDS 0
    exit 0
fi

records=$(wc -l < "$record_file" | tr -d '[:space:]')
set +e
"$PLUGIN_ROOT/scripts/larch-log.sh" append \
    --log-root "$LOG_ROOT" \
    --skill implement \
    --run-id "$RUN_ID" \
    --batch execution-issues \
    --record-file "$record_file" \
    >"$append_log_tmp" 2>&1
rc=$?
set +e

if [ "$rc" -eq 0 ]; then
    printf '%s\n' "$sha" > "$sentinel" 2>/dev/null || true
    emit_kv FLUSH_STATUS ok
    emit_kv RECORDS "$records"
    emit_kv APPEND_LOG_FILE "$append_log_tmp"
    exit 0
fi

"$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
    --log "$ISSUE_LOG" \
    --site flush-execution-issues \
    --tool larch-log.sh \
    --exit-code "$rc" \
    --category "Tool Failures" \
    --output-file "$append_log_tmp" \
    --redact >/dev/null 2>&1 || true
emit_kv FLUSH_STATUS failed
emit_kv RECORDS 0
emit_kv APPEND_LOG_FILE "$append_log_tmp"
exit 1
