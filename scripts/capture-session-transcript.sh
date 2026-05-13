#!/usr/bin/env bash
# capture-session-transcript.sh — best-effort session transcript capture.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

usage() {
    cat <<'USAGE' >&2
Usage:
  capture-session-transcript.sh --source-file PATH --log-root DIR --skill S --run-id R --no-logs-commit true|false --execution-issues-log PATH
USAGE
}

SOURCE_FILE=""
LOG_ROOT=""
SKILL=""
RUN_ID=""
NO_LOGS_COMMIT=""
EXECUTION_ISSUES_LOG=""

while [ $# -gt 0 ]; do
    case "$1" in
        --source-file)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            SOURCE_FILE="$2"; shift 2 ;;
        --log-root)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            LOG_ROOT="$2"; shift 2 ;;
        --skill)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            SKILL="$2"; shift 2 ;;
        --run-id)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            RUN_ID="$2"; shift 2 ;;
        --no-logs-commit)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            NO_LOGS_COMMIT="$2"; shift 2 ;;
        --execution-issues-log)
            [ $# -ge 2 ] || { usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0; }
            EXECUTION_ISSUES_LOG="$2"; shift 2 ;;
        *) usage; echo "SESSION_TRANSCRIPT_STATUS=usage-error"; exit 0 ;;
    esac
done

append_warning() {
    local status="$1"
    local message="$2"

    [ -n "$EXECUTION_ISSUES_LOG" ] || return 0
    "$SCRIPT_DIR/append-execution-issue.sh" \
        --log "$EXECUTION_ISSUES_LOG" \
        --category Warnings \
        --entry "- **Step 18 — session-transcript status=$status:** $message" \
        >/dev/null 2>&1 || true
}

emit_status() {
    local status="$1"
    local message="$2"

    append_warning "$status" "$message"
    echo "SESSION_TRANSCRIPT_STATUS=$status"
    exit 0
}

if [ -z "$SOURCE_FILE" ] || [ ! -f "$SOURCE_FILE" ]; then
    emit_status "source-file-missing" "Claude source file was empty or not a regular file; transcript capture skipped."
fi

TRANSCRIPT_PATH="$(awk 'BEGIN{prefix="TRANSCRIPT_PATH="} index($0, prefix) == 1 {print substr($0, length(prefix) + 1); exit}' "$SOURCE_FILE" 2>/dev/null || true)"
if [ -z "$TRANSCRIPT_PATH" ]; then
    emit_status "transcript-path-missing" "Claude source file did not contain a TRANSCRIPT_PATH entry; transcript capture skipped."
fi

if [ ! -f "$TRANSCRIPT_PATH" ]; then
    emit_status "transcript-file-missing" "TRANSCRIPT_PATH target was missing or not a regular file; transcript capture skipped."
fi

if ! "$SCRIPT_DIR/larch-log.sh" write \
    --log-root "$LOG_ROOT" \
    --skill "$SKILL" \
    --run-id "$RUN_ID" \
    --batch session-transcript \
    --input-file "$TRANSCRIPT_PATH" \
    >/dev/null 2>&1; then
    emit_status "write-failed" "larch-log write failed; transcript was not captured."
fi

if [ "$NO_LOGS_COMMIT" = "true" ]; then
    emit_status "suppressed-no-logs-commit" "--no-logs-commit was set; transcript was written under the staging log root but not committed."
fi

if ! "$SCRIPT_DIR/larch-log.sh" commit \
    --log-root "$LOG_ROOT" \
    --skill "$SKILL" \
    --run-id "$RUN_ID" \
    --no-push \
    >/dev/null 2>&1; then
    emit_status "commit-failed" "write succeeded but git commit failed; transcript remains under the staging log root."
fi

emit_status "captured" "session transcript was written and committed."
