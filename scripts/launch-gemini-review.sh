#!/usr/bin/env bash
# launch-gemini-review.sh — Launch a generic Gemini code review and normalize JSON output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ORIGINAL_ARGS=("$@")
OUTPUT=""
TIMEOUT=""
PROMPT=""

usage() {
    echo "Usage: launch-gemini-review.sh --output FILE --timeout SECS --prompt TEXT" >&2
}

write_empty_output() {
    local tmp
    tmp=$(mktemp "${OUTPUT}.tmp.XXXXXX")
    : > "$tmp"
    mv "$tmp" "$OUTPUT"
}

write_done() {
    local code="$1"
    local tmp
    tmp=$(mktemp "${OUTPUT}.done.tmp.XXXXXX")
    printf '%s\n' "$code" > "$tmp"
    mv "$tmp" "${OUTPUT}.done"
}

write_meta() {
    local tmp
    tmp=$(mktemp "${OUTPUT}.meta.tmp.XXXXXX")
    {
        echo "TOOL=gemini"
        echo "TIMEOUT=$EFFECTIVE_TIMEOUT"
        echo "CAPTURE_STDOUT=false"
        echo "CAPTURE_STDOUT_ONLY=false"
        echo "OUTPUT_FILE=$OUTPUT"
        printf 'CMD=%s\n' "$(printf '%q ' "$0" "${ORIGINAL_ARGS[@]}")"
    } > "$tmp"
    mv "$tmp" "${OUTPUT}.meta"
}

fail_closed() {
    local code="$1"
    local reason="$2"
    write_empty_output
    {
        [[ -n "$reason" ]] && printf '%s\n' "$reason"
        [[ -f "$RAW_OUTPUT.diag" ]] && cat "$RAW_OUTPUT.diag"
    } >> "${OUTPUT}.diag"
    write_meta
    write_done "$code"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output) OUTPUT="${2:?--output requires a value}"; shift 2 ;;
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --prompt) PROMPT="${2:?--prompt requires a value}"; shift 2 ;;
        --agent-file|--mode|--description-text|--scope-files|--competition-notice)
            echo "launch-gemini-review.sh: specialist mode is not supported in v1" >&2
            exit 2 ;;
        --help) usage; exit 0 ;;
        *) echo "launch-gemini-review.sh: unknown flag: $1" >&2; usage; exit 2 ;;
    esac
done

if [[ -z "$OUTPUT" || -z "$TIMEOUT" || -z "$PROMPT" ]]; then
    echo "launch-gemini-review.sh: --output, --timeout, and --prompt are required" >&2
    usage
    exit 2
fi

case "$TIMEOUT" in
    ''|*[!0-9]*) echo "launch-gemini-review.sh: --timeout must be a positive integer, got '$TIMEOUT'" >&2; exit 2 ;;
esac

EFFECTIVE_TIMEOUT="$TIMEOUT"
if (( EFFECTIVE_TIMEOUT > 600 )); then
    EFFECTIVE_TIMEOUT=600
fi

RAW_OUTPUT="${OUTPUT}.raw"
rm -f "$OUTPUT" "${OUTPUT}.done" "${OUTPUT}.meta" "${OUTPUT}.diag" \
      "$RAW_OUTPUT" "${RAW_OUTPUT}.done" "${RAW_OUTPUT}.meta" "${RAW_OUTPUT}.diag"

if [[ "${LARCH_TEST_FORCE_MISSING_JQ:-}" == "true" ]] || ! command -v jq >/dev/null 2>&1; then
    RAW_OUTPUT="${OUTPUT}.raw"
    fail_closed 127 "MISSING_JQ: jq is required to parse Gemini JSON output"
fi

RUN_EXIT=0
"$SCRIPT_DIR/run-external-agent.sh" \
    --tool gemini \
    --output "$RAW_OUTPUT" \
    --timeout "$EFFECTIVE_TIMEOUT" \
    --capture-stdout-only \
    -- gemini -m pro -p "$PROMPT" -o json --skip-trust --approval-mode plan || RUN_EXIT=$?

if [[ "$RUN_EXIT" -ne 0 ]]; then
    fail_closed "$RUN_EXIT" "Gemini exited with code $RUN_EXIT"
fi

if jq -e '.error? // empty' "$RAW_OUTPUT" >/dev/null 2>&1; then
    GEMINI_ERROR=$(jq -r '.error' "$RAW_OUTPUT" 2>/dev/null | head -c 500 | tr '\n\r' '  ')
    fail_closed 1 "Gemini returned error: $GEMINI_ERROR"
fi

RESPONSE_TMP=$(mktemp "${OUTPUT}.tmp.XXXXXX")
if ! jq -er '.response // empty' "$RAW_OUTPUT" > "$RESPONSE_TMP"; then
    rm -f "$RESPONSE_TMP"
    fail_closed 1 "Gemini JSON missing non-empty .response"
fi

if [[ ! -s "$RESPONSE_TMP" ]]; then
    rm -f "$RESPONSE_TMP"
    fail_closed 1 "Gemini JSON .response was empty"
fi

mv "$RESPONSE_TMP" "$OUTPUT"
write_meta
write_done 0
exit 0
