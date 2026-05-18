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

# Accepts timings formatted as N.NNs within an inclusive numeric range.
timing_in_range() {
  local timing="$1"
  local min="$2"
  local max="$3"
  awk -v timing="$timing" -v min="$min" -v max="$max" '
    BEGIN {
      if (timing !~ /^[0-9]+\.[0-9]{2}s$/) {
        exit 1
      }
      value = timing
      sub(/s$/, "", value)
      exit !(value >= min && value <= max)
    }
  '
}

# Test 1: sleep 0.5 — timing should be between 0.40s and 0.79s (slop for CI)
out=$(bash "$TIMER" test-sleep-half sleep 0.5 2>&1)
timing=$(printf '%s\n' "$out" | extract_timing)
if timing_in_range "$timing" "0.40" "0.79"; then
  ok "sleep 0.5 timing is within 0.40s-0.79s (got: $timing)"
else
  fail "sleep 0.5 timing mismatch (got: '$timing', expected 0.40s-0.79s)"
fi

# Test 2: sleep 2 — timing should be between 1.90s and 4.99s (slop for CI)
out=$(bash "$TIMER" test-sleep-two sleep 2 2>&1)
timing=$(printf '%s\n' "$out" | extract_timing)
if timing_in_range "$timing" "1.90" "4.99"; then
  ok "sleep 2 timing is within 1.90s-4.99s (got: $timing)"
else
  fail "sleep 2 timing mismatch (got: '$timing', expected 1.90s-4.99s)"
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
