#!/usr/bin/env bash
# run-external-agent.sh — Monitored wrapper for external agents (Codex, Cursor, Gemini).
# Launches the agent in the background, polls the child PID at the cadence
# configured by RUN_EXTERNAL_AGENT_POLL_INTERVAL (default 10s; tests override
# to a fraction of a second), prints a one-line progress message per elapsed
# minute, and kills after a configurable timeout (e.g., 30 minutes for
# reviews/implementation, 20 minutes for votes/sketches).
#
# The --tool value is used only for log messages and the .meta TOOL= field.
# No validation is performed here by design (see issue #1099 / DECISION_1):
# the wrapper accepts any string label so out-of-tree callers can pass
# arbitrary provenance tags without importing the registry. The canonical
# external-tool name set is owned by scripts/external-tool-registry.sh; see
# scripts/external-tool-registry.md for the registry contract.
#
# Usage:
#   run-external-agent.sh --tool NAME --output FILE --timeout SECS [--capture-stdout|--capture-stdout-only] -- CMD...
#
# Options:
#   --tool            Tool name (e.g., "codex", "cursor") — used only for log messages
#   --output          Path where tool output is written
#   --timeout         Timeout in seconds (e.g., 1800 for 30 minutes)
#   --capture-stdout  Redirect the tool's stdout/stderr to the output file.
#                     Use for tools like Cursor that write results to stdout.
#                     Omit for tools like Codex that use their own output flags.
#   --capture-stdout-only
#                     Redirect the tool's stdout to the output file and stderr
#                     to <output>.diag. Use for JSON stdout protocols whose
#                     parse would be corrupted by stderr noise.
#   --               End of wrapper options. Everything after is the command to execute.
#
# Examples:
#   # Codex review (uses --output-last-message flag to write output)
#   run-external-agent.sh --tool codex --output /tmp/review-abc/codex-output.txt --timeout 1800 -- \
#     codex exec --full-auto -C /path/to/repo --output-last-message /tmp/review-abc/codex-output.txt "Review prompt..."
#
#   # Cursor review (stdout captured to file via --capture-stdout)
#   # Production invocations wrap the prompt via scripts/cursor-wrap-prompt.sh to
#   # engage max-mode; the example below shows the bare shape for clarity.
#   run-external-agent.sh --tool cursor --output /tmp/review-abc/cursor-output.txt --timeout 900 --capture-stdout -- \
#     cursor agent -p --force --trust --workspace /path/to/repo "Review prompt..."
#
#   # Gemini implementer (stdout captured to file via --capture-stdout)
#   run-external-agent.sh --tool gemini --output /tmp/impl-abc/gemini-output.txt --timeout 1800 --capture-stdout -- \
#     gemini --prompt "..." --approval-mode yolo --skip-trust --model gemini-2.5-pro

set -euo pipefail

usage() { echo "Usage: run-external-agent.sh --tool NAME --output FILE --timeout SECS [--capture-stdout] -- CMD..." >&2; }

CAPTURE_STDOUT=false
CAPTURE_STDOUT_ONLY=false
TOOL_NAME=""
OUTPUT_FILE=""
TIMEOUT_SECONDS=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool) TOOL_NAME="${2:?--tool requires a value}"; shift 2 ;;
        --output) OUTPUT_FILE="${2:?--output requires a value}"; shift 2 ;;
        --timeout) TIMEOUT_SECONDS="${2:?--timeout requires a value}"; shift 2 ;;
        --capture-stdout) CAPTURE_STDOUT=true; shift ;;
        --capture-stdout-only) CAPTURE_STDOUT_ONLY=true; shift ;;
        --help) usage; exit 0 ;;
        --) shift; break ;;
        *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
done

if [[ -z "$TOOL_NAME" ]] || [[ -z "$OUTPUT_FILE" ]] || [[ -z "$TIMEOUT_SECONDS" ]]; then
    echo "ERROR: --tool, --output, and --timeout are required" >&2
    usage; exit 1
fi

if [[ "$CAPTURE_STDOUT" == "true" && "$CAPTURE_STDOUT_ONLY" == "true" ]]; then
    echo "ERROR: --capture-stdout and --capture-stdout-only are mutually exclusive" >&2
    usage; exit 1
fi

case "$TIMEOUT_SECONDS" in
    ''|*[!0-9]*) echo "ERROR: --timeout must be a positive integer, got '$TIMEOUT_SECONDS'" >&2; exit 1 ;;
esac

# Poll interval (seconds) for the kill -0 wait loop below. Default 10s keeps
# real-agent invocations cheap on syscalls and bounds the time to notice a
# timeout. Test harnesses that wrap stub binaries (which exit in microseconds)
# override this to a fraction of a second so each invocation does not pay a
# full 10s sleep cycle. Accepts integer or decimal seconds (e.g. 0.05).
POLL_INTERVAL="${RUN_EXTERNAL_AGENT_POLL_INTERVAL:-10}"
case "$POLL_INTERVAL" in
    ''|*[!0-9.]*|.|0|0.|0.0|0.00|0.000) echo "ERROR: RUN_EXTERNAL_AGENT_POLL_INTERVAL must be a positive number, got '$POLL_INTERVAL'" >&2; exit 1 ;;
esac
case "$POLL_INTERVAL" in
    *.*.*) echo "ERROR: RUN_EXTERNAL_AGENT_POLL_INTERVAL must be a positive number, got '$POLL_INTERVAL'" >&2; exit 1 ;;
esac

if [[ $# -eq 0 ]]; then
    echo "ERROR: no command specified after --" >&2
    usage; exit 1
fi

# Clear stale output, sentinel, metadata, and diagnostic files
rm -f "$OUTPUT_FILE" "${OUTPUT_FILE}.done" "${OUTPUT_FILE}.meta" "${OUTPUT_FILE}.diag"

# Write sentinel file on ANY exit — the reliable completion signal for callers.
# Callers poll for <output-file>.done instead of waiting for runtime notifications.
# Installed BEFORE .meta write so that any early exit still creates a sentinel.
EXIT_CODE=99  # default: wrapper crashed before capturing real exit code
trap 'echo "$EXIT_CODE" > "${OUTPUT_FILE}.done" 2>/dev/null || true' EXIT

# Write metadata for collect-agent-results.sh retry support.
# CMD is shell-quoted via printf '%q' to preserve argument boundaries.
META_TOOL_NAME=$(printf '%s' "$TOOL_NAME" | LC_ALL=C tr -d '[:cntrl:]=')
{
    echo "TOOL=$META_TOOL_NAME"
    echo "TIMEOUT=$TIMEOUT_SECONDS"
    echo "CAPTURE_STDOUT=$CAPTURE_STDOUT"
    echo "CAPTURE_STDOUT_ONLY=$CAPTURE_STDOUT_ONLY"
    echo "OUTPUT_FILE=$OUTPUT_FILE"
    printf 'CMD=%s\n' "$(printf '%q ' "$@")"
} > "${OUTPUT_FILE}.meta"

# Launch the agent in the background
if [ "$CAPTURE_STDOUT" = true ]; then
    "$@" > "$OUTPUT_FILE" 2>&1 &
elif [ "$CAPTURE_STDOUT_ONLY" = true ]; then
    "$@" > "$OUTPUT_FILE" 2> "${OUTPUT_FILE}.diag" &
else
    "$@" &
fi
PID=$!
SECONDS=0
LAST_PROGRESS_MINUTE=0

# Poll until the process exits or times out
# Check timeout BEFORE sleeping to avoid overshooting by a full interval.
# Use 10s intervals for more responsive timeout detection.
while kill -0 "$PID" 2>/dev/null; do
    if [ "$SECONDS" -ge "$TIMEOUT_SECONDS" ]; then
        echo "⚠ ${TOOL_NAME} agent: TIMED OUT after $(( TIMEOUT_SECONDS / 60 )) minutes, killing"
        kill "$PID" 2>/dev/null
        sleep 5
        kill -9 "$PID" 2>/dev/null || true
        wait "$PID" 2>/dev/null || true
        # Report diagnostics even on timeout
        OUTPUT_SIZE=0
        if [ -f "$OUTPUT_FILE" ]; then
            OUTPUT_SIZE=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')
        fi
        echo "❌ ${TOOL_NAME} agent: TIMED OUT (exit code 124, ${SECONDS}s elapsed, output ${OUTPUT_SIZE} bytes)"
        # Write diagnostic file for callers
        echo "Timed out after ${SECONDS}s (limit: ${TIMEOUT_SECONDS}s). Process was killed after exceeding the timeout. Output size: ${OUTPUT_SIZE} bytes." >> "${OUTPUT_FILE}.diag"
        EXIT_CODE=124
        exit "$EXIT_CODE"
    fi
    sleep "$POLL_INTERVAL"
    # Print one progress line per elapsed minute. SECONDS is bash's built-in
    # seconds-since-shell-start counter, independent of $POLL_INTERVAL.
    # LAST_PROGRESS_MINUTE de-dups when the poll cadence is sub-second (the
    # default 10s cadence already polls at most once per second of real time
    # within a minute window, but tests run with 0.05s).
    elapsed_minute=$(( SECONDS / 60 ))
    if [ "$elapsed_minute" -ge 1 ] && [ "$elapsed_minute" != "$LAST_PROGRESS_MINUTE" ]; then
        echo "⏳ ${TOOL_NAME} agent: still running (${elapsed_minute}m elapsed)"
        LAST_PROGRESS_MINUTE="$elapsed_minute"
    fi
done

# Capture exit code without triggering set -e (wait propagates child exit code)
wait "$PID" && EXIT_CODE=0 || EXIT_CODE=$?

# Diagnostics: report completion with details to help debug failures
OUTPUT_SIZE=0
if [ -f "$OUTPUT_FILE" ]; then
    OUTPUT_SIZE=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')
fi

if [ "$EXIT_CODE" -ne 0 ]; then
    echo "❌ ${TOOL_NAME} agent: FAILED (exit code ${EXIT_CODE}, ${SECONDS}s elapsed, output ${OUTPUT_SIZE} bytes)"
    DIAG_DETAIL=""
    if [ "$OUTPUT_SIZE" -gt 0 ]; then
        echo "--- ${TOOL_NAME} output (last 5 lines) ---"
        tail -5 "$OUTPUT_FILE"
        echo "--- end ---"
        DIAG_DETAIL=" Last output: $(tail -1 "$OUTPUT_FILE" | head -c 200 | tr '|' ' ')"
    fi
    # Write diagnostic file for callers
    echo "Failed with exit code ${EXIT_CODE} after ${SECONDS}s. Output size: ${OUTPUT_SIZE} bytes.${DIAG_DETAIL}" >> "${OUTPUT_FILE}.diag"
elif [ "$OUTPUT_SIZE" -eq 0 ]; then
    echo "⚠ ${TOOL_NAME} agent: completed but OUTPUT IS EMPTY (exit code 0, ${SECONDS}s elapsed)"
    echo "This typically means ${TOOL_NAME} exited without producing output."
    # Write diagnostic file for callers
    echo "Process exited successfully (code 0) after ${SECONDS}s but produced no output. This typically means the tool started but did not generate a response." >> "${OUTPUT_FILE}.diag"
else
    echo "✓ ${TOOL_NAME} agent: completed (exit code 0, ${SECONDS}s elapsed, output ${OUTPUT_SIZE} bytes)"
fi
exit "$EXIT_CODE"
