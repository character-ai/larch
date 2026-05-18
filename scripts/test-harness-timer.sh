#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMER="$SCRIPT_DIR/harness-timer.sh"

pass=0
fail=0

ok() { printf 'PASS: %s\n' "$1"; pass=$(( pass + 1 )); }
fail() { printf 'FAIL: %s\n' "$1"; fail=$(( fail + 1 )); }

# Extracts the timing token (e.g. "0.34s") from a LARCH_HARNESS_TIMING line.
extract_timing() {
  awk -F'\t' '/^LARCH_HARNESS_TIMING\t/ { print $3; exit }'
}

# Test 1: sleep 0.5 — timing should be between 0.40s and 0.69s (slop for CI)
out=$(bash "$TIMER" test-sleep-half sleep 0.5 2>&1)
timing=$(printf '%s\n' "$out" | extract_timing)
if printf '%s\n' "$timing" | grep -qE '^0\.[4-6][0-9]s$'; then
  ok "sleep 0.5 timing matches ^0\\.[4-6][0-9]s\\$ (got: $timing)"
else
  fail "sleep 0.5 timing mismatch (got: '$timing', expected ^0\\.[4-6][0-9]s\\$)"
fi

# Test 2: sleep 2 — timing should match ^[12]\.[0-9]{2}s$
out=$(bash "$TIMER" test-sleep-two sleep 2 2>&1)
timing=$(printf '%s\n' "$out" | extract_timing)
if printf '%s\n' "$timing" | grep -qE '^[12]\.[0-9]{2}s$'; then
  ok "sleep 2 timing matches ^[12]\\.[0-9]{2}s\\$ (got: $timing)"
else
  fail "sleep 2 timing mismatch (got: '$timing', expected ^[12]\\.[0-9]{2}s\\$)"
fi

# Test 3: false — exit code 1 mirrored AND LARCH_HARNESS_TIMING line emitted
out=$(bash "$TIMER" test-false false 2>&1) && rc=0 || rc=$?
timing=$(printf '%s\n' "$out" | extract_timing)
if [ "$rc" -eq 1 ]; then
  ok "false: exit code 1 mirrored"
else
  fail "false: expected exit code 1, got $rc"
fi
if [ -n "$timing" ]; then
  ok "false: LARCH_HARNESS_TIMING emitted (got: $timing)"
else
  fail "false: LARCH_HARNESS_TIMING line not emitted"
fi

echo ""
printf 'Results: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
