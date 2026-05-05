#!/usr/bin/env bash
# launch-gemini-review.sh — Launch a generic Gemini code review and normalize JSON output.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-validate-meta-path.sh
source "$SCRIPT_DIR/lib-validate-meta-path.sh"

ORIGINAL_ARGS=("$@")
OUTPUT=""
TIMEOUT=""
PROMPT=""

# Build a redacted copy of ORIGINAL_ARGS for write_meta() so the full --prompt
# body (which carries inlined diff / log / file-list — see plan FINDING_10) is
# not duplicated to ${OUTPUT}.meta. .meta CMD_JSON= replays the launcher
# invocation as a single-line JSON array, not raw Gemini, so the actual prompt
# content is unnecessary for retry semantics. On the missing-jq fail-closed
# path, write_meta() omits CMD_JSON so write_done() can still run.
REDACTED_ARGS=()
_skip_next=0
for _arg in "${ORIGINAL_ARGS[@]}"; do
    if (( _skip_next == 1 )); then
        _hash="<unhashed>"
        if command -v shasum >/dev/null 2>&1; then
            _hash=$(printf '%s' "$_arg" | shasum -a 256 | awk '{print $1}')
        elif command -v sha256sum >/dev/null 2>&1; then
            _hash=$(printf '%s' "$_arg" | sha256sum | awk '{print $1}')
        fi
        REDACTED_ARGS+=("<REDACTED:sha256=${_hash:0:16},len=${#_arg}>")
        _skip_next=0
        continue
    fi
    REDACTED_ARGS+=("$_arg")
    if [[ "$_arg" == "--prompt" ]]; then
        _skip_next=1
    fi
done
unset _arg _skip_next _hash

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
        # The inner run-external-agent invocation uses --capture-stdout-only;
        # record the actual capture mode here so collector retry paths that
        # rebuild flags from .meta do not silently drop --capture-stdout-only.
        echo "CAPTURE_STDOUT_ONLY=true"
        echo "OUTPUT_FILE=$OUTPUT"
        # CMD_JSON replays the LAUNCHER (not raw gemini) so retry re-runs
        # JSON normalization. The --prompt body is already redacted to a
        # sha256 prefix + byte length in REDACTED_ARGS to avoid persisting
        # inlined diff/log content into the session tmpdir's .meta artifact.
        # If jq is unavailable (the LARCH_TEST_FORCE_MISSING_JQ /
        # MISSING_JQ fail_closed path), omit CMD_JSON entirely; the collector
        # treats missing CMD_JSON as fail-closed while write_done() still runs.
        if command -v jq >/dev/null 2>&1 && [[ "${LARCH_TEST_FORCE_MISSING_JQ:-}" != "true" ]]; then
            if META_CMD_JSON=$(jq -cn --args '$ARGS.positional' -- "$0" "${REDACTED_ARGS[@]}"); then
                printf 'CMD_JSON=%s\n' "$META_CMD_JSON"
            fi
        fi
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

validate_meta_scalar_path --output "$OUTPUT" || exit 2

case "$TIMEOUT" in
    ''|*[!0-9]*|0) echo "launch-gemini-review.sh: --timeout must be a positive integer, got '$TIMEOUT'" >&2; exit 2 ;;
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

GEMINI_MODEL="${LARCH_GEMINI_MODEL:-${CLAUDE_PLUGIN_OPTION_GEMINI_MODEL:-gemini-2.5-pro}}"

RUN_EXIT=0
"$SCRIPT_DIR/run-external-agent.sh" \
    --tool gemini \
    --output "$RAW_OUTPUT" \
    --timeout "$EFFECTIVE_TIMEOUT" \
    --capture-stdout-only \
    -- gemini -m "$GEMINI_MODEL" -p "$PROMPT" -o json --skip-trust --approval-mode plan || RUN_EXIT=$?

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

if [[ ! -s "$RESPONSE_TMP" ]] || [[ -z "$(tr -d '[:space:]' < "$RESPONSE_TMP")" ]]; then
    rm -f "$RESPONSE_TMP"
    fail_closed 1 "Gemini JSON .response was empty (or whitespace-only)"
fi

mv "$RESPONSE_TMP" "$OUTPUT"
write_meta
write_done 0
exit 0
