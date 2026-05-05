#!/usr/bin/env bash
# test-run-external-agent-args.sh — Argument-validation harness for run-external-agent.sh.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$REPO_ROOT/scripts/run-external-agent.sh"

[[ -x "$RUNNER" ]] || { echo "FAIL: runner not executable: $RUNNER" >&2; exit 1; }

PASS_COUNT=0
FAIL_COUNT=0
fail() { echo "FAIL [$1]: $2" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); }

SCRATCH=$(mktemp -d -t run-external-agent-args.XXXXXX)
trap 'rm -rf "$SCRATCH"' EXIT

OUTPUT="$SCRATCH/output.txt"

EXIT=0
ARG_OUTPUT=$("$RUNNER" \
    --timeout 0 \
    --tool foo \
    --output "$OUTPUT" \
    -- /usr/bin/true 2>&1) || EXIT=$?

if [[ "$EXIT" == "1" ]]; then
    pass
else
    fail 1 "zero timeout should exit 1, got $EXIT"
fi

EXPECTED="ERROR: --timeout must be a positive integer, got '0'"
if [[ "$ARG_OUTPUT" == *"$EXPECTED"* ]]; then
    pass
else
    fail 2 "zero timeout should report exact error; got: $ARG_OUTPUT"
fi

# Reject-before-side-effects: parallel to scripts/test-run-external-agent.sh —
# argument validation must happen before any output / sentinel / sidecar files
# are touched, otherwise a future reorder could regress the contract while
# this harness still passes on exit code + stderr substring alone.
for path in "$OUTPUT" "$OUTPUT.done" "$OUTPUT.meta" "$OUTPUT.diag"; do
    if [[ -e "$path" ]]; then
        fail 3 "zero-timeout rejection must not create $path"
    else
        pass
    fi
done

TOTAL=$((PASS_COUNT + FAIL_COUNT))
if (( FAIL_COUNT == 0 )); then
    echo "PASS: test-run-external-agent-args.sh — $PASS_COUNT/$TOTAL assertions"
    exit 0
else
    echo "FAIL: test-run-external-agent-args.sh — $FAIL_COUNT/$TOTAL assertions failed" >&2
    exit 1
fi
