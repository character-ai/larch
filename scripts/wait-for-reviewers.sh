#!/usr/bin/env bash
# wait-for-reviewers.sh — Poll for external reviewer sentinel files with compact progress.
#
# Usage:
#   wait-for-reviewers.sh [--timeout <seconds>] <sentinel.done> [sentinel2.done ...]
#
# Sentinel files are the .done files created by run-external-agent.sh.
# Progress (dots, status lines) goes to stderr.
# Machine-parseable results (DONE/TIMEOUT lines) go to stdout.
# Stdout grammar (one record per sentinel, in argv order):
#   DONE <idx> <basename>: exit=<code>
#   TIMEOUT <idx> <basename>
# <idx> is the 1-based argv position of the sentinel; <basename> is
# informational only. Callers must key on <idx>, not basename.
# Always exits 0 for normal operation (including timeouts) — callers inspect stdout
# to determine which reviewers completed vs timed out. Exits 1 only for usage errors.
#
# The default timeout is 1860 seconds (31 minutes), matching the run-external-agent.sh
# review timeout of 30 minutes + 1 minute grace period. Override with --timeout if a different
# wrapper timeout was used (e.g., 1260 for the 20-minute vote/sketch timeout).

# No -e: script always exits 0 for normal operation; subshell failures must not abort.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# --- Parse arguments ---
usage() { larch_err "Usage: wait-for-reviewers.sh [--timeout SECONDS] <sentinel.done> [sentinel2.done ...]"; }

TIMEOUT=1860
while [[ $# -gt 0 ]]; do
    case "$1" in
        --timeout) TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        -*) larch_err "Unknown option: $1"; usage; exit 1 ;;
        *) break ;;
    esac
done

case "$TIMEOUT" in
    ''|*[!0-9]*) larch_err "Error: --timeout value must be a positive integer, got '$TIMEOUT'"; exit 1 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    larch_err "Error: --timeout value must be a positive integer, got '$TIMEOUT'"
    exit 1
fi
TIMEOUT=$((10#$TIMEOUT))

# Sentinel-poll interval. Default 5s for production callers (real reviewers
# take many minutes; 5s noise is negligible). Test harnesses that wrap stub
# binaries via run-external-agent.sh override via env to avoid paying a 5s
# delay per probe. Accepts integer or decimal seconds.
WAIT_POLL_INTERVAL="${WAIT_FOR_REVIEWERS_POLL_INTERVAL:-5}"
case "$WAIT_POLL_INTERVAL" in
    ''|*[!0-9.]*|.|0|0.|0.0|0.00|0.000) larch_err "Error: WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '$WAIT_POLL_INTERVAL'"; exit 1 ;;
esac
case "$WAIT_POLL_INTERVAL" in
    *.*.*) larch_err "Error: WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '$WAIT_POLL_INTERVAL'"; exit 1 ;;
esac
if [[ "$WAIT_POLL_INTERVAL" != *.* ]]; then
    if (( 10#$WAIT_POLL_INTERVAL < 1 )); then
        larch_err "Error: WAIT_FOR_REVIEWERS_POLL_INTERVAL must be a positive number, got '$WAIT_POLL_INTERVAL'"
        exit 1
    fi
fi
MAX_POLLS=$(awk -v t="$TIMEOUT" -v p="$WAIT_POLL_INTERVAL" 'BEGIN{print int((t + p - 0.001) / p)}')
[ "${MAX_POLLS:-0}" -ge 1 ] 2>/dev/null || MAX_POLLS=1

if [[ $# -eq 0 ]]; then
    larch_err "ERROR: at least one sentinel file path is required"
    usage; exit 1
fi

TOTAL=$#
MARKER_DIR=$(mktemp -d /tmp/wait-reviewers-XXXXXX) || { larch_err "fatal: mktemp failed"; exit 1; }
trap 'rm -rf "$MARKER_DIR"' EXIT

# read_exit_code <sentinel-file> — read and validate the exit code from a sentinel file.
read_exit_code() {
    local code
    code=$(tr -d '[:space:]' < "$1" 2>/dev/null)
    case "$code" in
        ''|*[!0-9]*) code="unknown" ;;
    esac
    printf '%s' "$code"
}

# check_sentinels — scan all sentinel files, update markers and found_count.
check_sentinels() {
    local idx=0
    for sentinel in "$@"; do
        idx=$((idx + 1))
        if [ -f "$MARKER_DIR/$idx" ]; then
            continue
        fi
        if [ -f "$sentinel" ]; then
            local exit_code
            exit_code=$(read_exit_code "$sentinel")
            echo "$exit_code" > "$MARKER_DIR/$idx"
            found_count=$((found_count + 1))
            larch_errf "\n✓ %s: exit=%s\n" "$(basename "$sentinel" .done)" "$exit_code"
        fi
    done
}

# --- Polling loop ---
SECONDS=0
found_count=0
checks=0
suspend_refunds=0
last_progress_minute=0

# Check before first sleep — detect pre-existing sentinels immediately
check_sentinels "$@"

while [ "$found_count" -lt "$TOTAL" ] && [ "$checks" -lt "$MAX_POLLS" ]; do
    iter_start=$(date +%s)
    # Print dot progress
    larch_errf "."
    checks=$((checks + 1))
    # Print status line on every elapsed-minute boundary. Driven by $SECONDS so
    # the cadence is minute-based regardless of $WAIT_POLL_INTERVAL — at the
    # default 5s production cadence this fires every ~12 checks; at the test
    # harnesses' 0.05s cadence it would fire every ~1200 checks if any test ran
    # long enough to cross a minute.
    elapsed_minute=$(( SECONDS / 60 ))
    if [ "$elapsed_minute" -ge 1 ] && [ "$elapsed_minute" != "$last_progress_minute" ]; then
        larch_errf "\n⏳ Waiting: %dm elapsed, %d checks, %d/%d done\n" \
            "$elapsed_minute" "$checks" "$found_count" "$TOTAL"
        last_progress_minute="$elapsed_minute"
    fi

    sleep "$WAIT_POLL_INTERVAL"

    check_sentinels "$@"
    iter_delta=$(( $(date +%s) - iter_start ))
    if [ "$iter_delta" -gt 60 ]; then
        larch_errf "\n⚠ suspend detected — iteration took %ds, not counting toward poll budget\n" "$iter_delta"
        # Cap refunds at MAX_POLLS to prevent an infinite wait when the host is
        # so slow that *every* iteration exceeds 60s (e.g. heavy load, debugger).
        if [ "$suspend_refunds" -lt "$MAX_POLLS" ]; then
            checks=$((checks - 1))
            suspend_refunds=$((suspend_refunds + 1))
        fi
    fi
done

# Snapshot elapsed time before summary output
ELAPSED=$SECONDS

# --- Summary output (stdout, machine-parseable) ---
larch_errf "\n"
idx=0
timed_out=0
for sentinel in "$@"; do
    idx=$((idx + 1))
    name=$(basename "$sentinel" .done)
    if [ -f "$MARKER_DIR/$idx" ]; then
        exit_code=$(cat "$MARKER_DIR/$idx" 2>/dev/null)
        emit "DONE $idx $name: exit=$exit_code"
    else
        emit "TIMEOUT $idx $name"
        timed_out=$((timed_out + 1))
        pid_file="${sentinel%.done}.pid"
        if [ -f "$pid_file" ]; then
            _stuck_pid=$(tr -d '[:space:]' < "$pid_file" 2>/dev/null)
            if [ -n "$_stuck_pid" ] && [ "$_stuck_pid" -gt 0 ] 2>/dev/null; then
                larch_errf "⚠ Sending SIGTERM to stuck subprocess PID %s for %s\n" "$_stuck_pid" "$name"
                kill -TERM "$_stuck_pid" 2>/dev/null || true
            fi
        fi
    fi
done

if [ "$timed_out" -gt 0 ]; then
    larch_errf "⚠ %d/%d reviewer(s) timed out after %d seconds\n" "$timed_out" "$TOTAL" "$TIMEOUT"
else
    larch_errf "✓ All %d reviewer(s) completed in %ds\n" "$TOTAL" "$ELAPSED"
fi

exit 0
