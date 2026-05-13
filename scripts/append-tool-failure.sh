#!/usr/bin/env bash
# append-tool-failure.sh — append verbatim captured tool failure output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

fail_usage() {
    echo "FAILED=true"
    echo "ERROR=usage: $1"
    exit 1
}

LOG_FILE=""
SITE=""
TOOL_LABEL=""
EXIT_CODE=""
CATEGORY=""
OUTPUT_FILE=""
REDACT=false

while [ $# -gt 0 ]; do
    case "$1" in
        --log)
            [ $# -ge 2 ] || fail_usage "--log requires a value"
            LOG_FILE=$2; shift 2 ;;
        --site)
            [ $# -ge 2 ] || fail_usage "--site requires a value"
            SITE=$2; shift 2 ;;
        --tool)
            [ $# -ge 2 ] || fail_usage "--tool requires a value"
            TOOL_LABEL=$2; shift 2 ;;
        --exit-code)
            [ $# -ge 2 ] || fail_usage "--exit-code requires a value"
            EXIT_CODE=$2; shift 2 ;;
        --category)
            [ $# -ge 2 ] || fail_usage "--category requires a value"
            CATEGORY=$2; shift 2 ;;
        --output-file)
            [ $# -ge 2 ] || fail_usage "--output-file requires a value"
            OUTPUT_FILE=$2; shift 2 ;;
        --redact)
            REDACT=true; shift ;;
        *)
            fail_usage "unknown flag: $1" ;;
    esac
done

[ -n "$LOG_FILE" ] || fail_usage "--log is required"
[ -n "$SITE" ] || fail_usage "--site is required"
[ -n "$TOOL_LABEL" ] || fail_usage "--tool is required"
[ -n "$EXIT_CODE" ] || fail_usage "--exit-code is required"
[ -n "$CATEGORY" ] || fail_usage "--category is required"
[ -n "$OUTPUT_FILE" ] || fail_usage "--output-file is required"

case "$CATEGORY" in
    "Tool Failures"|"External Reviewer Issues"|"CI Issues"|"Warnings") ;;
    *) fail_usage "unsupported category: $CATEGORY" ;;
esac

case "$EXIT_CODE" in
    ""|*[!0-9]*) fail_usage "--exit-code must be a non-negative integer" ;;
esac

if [ ! -f "$OUTPUT_FILE" ]; then
    echo "FAILED=true"
    echo "ERROR=output file not found: $OUTPUT_FILE"
    exit 2
fi

content_file=$OUTPUT_FILE
tmp_content=""
entry_file=""
cleanup() {
    [ -z "$tmp_content" ] || rm -f "$tmp_content"
    [ -z "$entry_file" ] || rm -f "$entry_file"
}
trap cleanup EXIT

if [ "$REDACT" = "true" ]; then
    [ -x "$SCRIPT_DIR/redact-secrets.sh" ] || {
        echo "FAILED=true"
        echo "ERROR=redaction helper missing: $SCRIPT_DIR/redact-secrets.sh"
        exit 2
    }
    tmp_content="$(mktemp "${TMPDIR:-/tmp}/append-tool-failure-redacted.XXXXXX")" || {
        echo "FAILED=true"
        echo "ERROR=cannot create redaction temp file"
        exit 2
    }
    if ! "$SCRIPT_DIR/redact-secrets.sh" < "$OUTPUT_FILE" > "$tmp_content"; then
        echo "FAILED=true"
        echo "ERROR=redaction failed for: $OUTPUT_FILE"
        exit 2
    fi
    content_file=$tmp_content
fi

entry_file="$(mktemp "${TMPDIR:-/tmp}/append-tool-failure-entry.XXXXXX")" || {
    echo "FAILED=true"
    echo "ERROR=cannot create entry temp file"
    exit 2
}

{
    printf -- '- **Step %s — %s failed (exit %s)**:\n' "$SITE" "$TOOL_LABEL" "$EXIT_CODE"
    printf '  ```\n'
    cat "$content_file"
    if [ -s "$content_file" ] && [ "$(tail -c 1 "$content_file" | tr -d '\n' | wc -c | tr -d ' ')" != "0" ]; then
        printf '\n'
    fi
    printf '  ```\n'
} > "$entry_file" || {
    echo "FAILED=true"
    echo "ERROR=failed to compose entry"
    exit 2
}

"$SCRIPT_DIR/append-execution-issue.sh" \
    --log "$LOG_FILE" \
    --category "$CATEGORY" \
    --entry "$(cat "$entry_file")"
