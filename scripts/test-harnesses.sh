#!/usr/bin/env bash
# test-harnesses.sh — Run all `test-*` Makefile harnesses concurrently.
#
# Discovers harness commands by running `make -n _test-harnesses-list` (the
# Makefile's `_test-harnesses-list` target lists every harness as a
# prerequisite, so this is the single source of truth). Runs up to MAX_JOBS
# (default 10) commands in parallel, capturing each script's stdout+stderr
# into a tmpfile and printing it as a contiguous block in submission order
# once that script finishes. Output blocks never interleave. Exits 1 if any
# harness fails, 0 if all pass.
#
# Bash 3.2 portable (no `wait -n`, no `mapfile`, no associative arrays).
#
# Usage:
#   bash scripts/test-harnesses.sh
#
# Tunables (env):
#   MAX_JOBS   — max concurrent workers (default 10)
#   POLL_MS    — poll interval in milliseconds when no job has finished
#                (default 100); accepts integer, converted to seconds for
#                `sleep`.

# Intentional: do NOT `set -e`. We want to keep running after a child fails
# so all results are collected and printed before exiting non-zero.
set -uo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

MAX_JOBS=${MAX_JOBS:-10}
POLL_MS=${POLL_MS:-100}

# Validate tunables. Invalid values used to wedge the main loop (MAX_JOBS=0
# launched no jobs while polling for status files that would never appear;
# POLL_MS=0 made `sleep` near-instant and busy-spinned the CPU).
case "$MAX_JOBS" in
    ''|*[!0-9]*) echo "ERROR: MAX_JOBS must be a positive integer, got: '$MAX_JOBS'" >&2; exit 2 ;;
esac
[ "$MAX_JOBS" -lt 1 ] && { echo "ERROR: MAX_JOBS must be >= 1, got: $MAX_JOBS" >&2; exit 2; }
case "$POLL_MS" in
    ''|*[!0-9]*) echo "ERROR: POLL_MS must be a non-negative integer, got: '$POLL_MS'" >&2; exit 2 ;;
esac
[ "$POLL_MS" -lt 10 ] && POLL_MS=10  # clamp: never busy-spin under 10ms

# Convert POLL_MS to seconds string acceptable to `sleep` on macOS+Linux.
POLL_SLEEP=$(awk -v ms="$POLL_MS" 'BEGIN{printf "%.3f", ms/1000.0}')

cd "$REPO_ROOT" || { echo "ERROR: cannot cd to $REPO_ROOT" >&2; exit 2; }

# Enumerate harness commands via make -n. The Makefile's
# `_test-harnesses-list` target has every harness as a prerequisite and no
# recipe of its own; `make -n` walks the prereqs and prints each one's
# recipe (the `bash <path>` line). We capture commands in submission order.
LIST_OUTPUT=$(make -n _test-harnesses-list 2>&1)
LIST_RC=$?
if [ "$LIST_RC" -ne 0 ]; then
    echo "ERROR: 'make -n _test-harnesses-list' failed (exit $LIST_RC):" >&2
    printf '%s\n' "$LIST_OUTPUT" >&2
    exit 2
fi

# Filter to harness command lines and whitelist them to a strict shape.
# By convention every harness recipe is a single line of the form
# `bash <repo-relative-path>` (optional trailing single-token args). We REJECT
# any line that doesn't match — multi-line recipes, `&&` chains, embedded
# command substitution, or non-`bash` recipes — to keep the eval surface
# narrow even though Makefile content is repo-controlled.
COMMANDS=()
REJECTED=()
while IFS= read -r line; do
    case "$line" in
        ''|'#'*|'make['*|'make:'*) continue ;;
    esac
    # Whitelist: `bash <path-without-shell-metacharacters> [<simple-args>...]`.
    # Path tokens may contain alnum, `_`, `-`, `.`, `/`. Args may not contain
    # any of: ;|&`$<>(){}[]\\*?"'~ or whitespace beyond single spaces.
    if printf '%s' "$line" | grep -Eq '^bash [A-Za-z0-9_./-]+( [A-Za-z0-9_./=:.,@+-]+)*$'; then
        COMMANDS+=("$line")
    else
        REJECTED+=("$line")
    fi
done <<EOF
$LIST_OUTPUT
EOF

if [ "${#REJECTED[@]}" -gt 0 ]; then
    echo "ERROR: $(printf '%s\n' "${REJECTED[@]}" | wc -l | tr -d ' ') harness recipe line(s) did not match the expected 'bash <path> [args]' shape:" >&2
    printf '  rejected: %s\n' "${REJECTED[@]}" >&2
    echo "Update _test-harnesses-list recipes to a single 'bash <path>' line, or extend the whitelist in scripts/test-harnesses.sh." >&2
    exit 2
fi

TOTAL=${#COMMANDS[@]}
if [ "$TOTAL" -eq 0 ]; then
    # Zero harnesses is treated as an error so 'make test-harnesses' cannot
    # silently pass green when the prereq list is empty / mis-edited / over-
    # filtered. If you genuinely have no harnesses, remove the test-harnesses
    # invocation from CI rather than allowing this path to exit 0.
    echo "ERROR: 'make -n _test-harnesses-list' yielded zero harness commands. Check _test-harnesses-list prerequisites in Makefile." >&2
    exit 2
fi

TMPDIR_RUN=$(mktemp -d -t test-harnesses.XXXXXX)
# Track the process group so signal handlers can kill in-flight workers.
WORKER_PIDS=()
cleanup() {
    rm -rf "$TMPDIR_RUN"
}
on_signal() {
    local sig="$1"
    # Best-effort: kill any still-running worker so a Ctrl-C / SIGTERM does
    # not leave background harnesses running after we exit.
    if [ "${#WORKER_PIDS[@]}" -gt 0 ]; then
        kill "${WORKER_PIDS[@]}" 2>/dev/null || true
    fi
    cleanup
    # Standard exit codes for signal-terminated processes.
    case "$sig" in
        INT)  exit 130 ;;
        TERM) exit 143 ;;
        *)    exit 1 ;;
    esac
}
trap cleanup EXIT
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM

# Per-job state is tracked entirely via on-disk sentinel files
# ($TMPDIR_RUN/<idx>.out and <idx>.status). PIDs are intentionally not
# retained: completion is detected by `.status` file existence, which lets
# the top-up loop free a slot the moment any job (not just the next-to-
# print) finishes. Backgrounded children are reaped via the implicit shell
# child reaper plus the final EXIT trap.

launch() {
    local idx="$1"
    local cmd="${COMMANDS[$idx]}"
    local outfile="$TMPDIR_RUN/$idx.out"
    local statusfile="$TMPDIR_RUN/$idx.status"
    (
        # Run the command in a subshell so its exit code is captured cleanly.
        # `eval` is safe here because each command was vetted by the strict
        # whitelist regex above (`bash <path> [simple-args]`) — no shell
        # metacharacters, command substitution, or chaining can reach this
        # point.
        eval "$cmd" >"$outfile" 2>&1
        echo $? >"$statusfile"
    ) &
    WORKER_PIDS+=($!)
}

count_in_flight() {
    # In-flight = launched index whose .status file has not yet appeared.
    # We only check the "live window" [printed, launched) since indices
    # below `printed` are already drained.
    local n=0 k
    for ((k=printed; k<launched; k++)); do
        [ ! -f "$TMPDIR_RUN/$k.status" ] && n=$((n+1))
    done
    echo "$n"
}

failed=0
launched=0
printed=0

# Initial top-up.
in_flight=0
while [ "$launched" -lt "$TOTAL" ] && [ "$in_flight" -lt "$MAX_JOBS" ]; do
    launch "$launched"
    launched=$((launched+1))
    in_flight=$((in_flight+1))
done

while [ "$printed" -lt "$TOTAL" ]; do
    # Top up: launch as many new jobs as the slot budget allows. Recount
    # in-flight each pass so completions free slots even before we print.
    in_flight=$(count_in_flight)
    while [ "$launched" -lt "$TOTAL" ] && [ "$in_flight" -lt "$MAX_JOBS" ]; do
        launch "$launched"
        launched=$((launched+1))
        in_flight=$((in_flight+1))
    done

    # If next-to-print finished, drain it; otherwise sleep briefly and loop.
    if [ -f "$TMPDIR_RUN/$printed.status" ]; then
        rc=$(cat "$TMPDIR_RUN/$printed.status" 2>/dev/null || echo 1)
        cmd="${COMMANDS[$printed]}"
        if [ "$rc" = "0" ]; then
            printf '===== %s — PASS =====\n' "$cmd"
        else
            printf '===== %s — FAIL (exit %s) =====\n' "$cmd" "$rc"
            failed=$((failed+1))
        fi
        if [ -f "$TMPDIR_RUN/$printed.out" ]; then
            cat "$TMPDIR_RUN/$printed.out"
        fi
        printf '\n'
        printed=$((printed+1))
    else
        sleep "$POLL_SLEEP"
    fi
done

if [ "$failed" -gt 0 ]; then
    printf 'FAILED: %d of %d harness(es) failed\n' "$failed" "$TOTAL" >&2
    exit 1
fi

printf 'PASS: all %d harness(es) passed\n' "$TOTAL"
