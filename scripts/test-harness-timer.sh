#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMER="$SCRIPT_DIR/harness-timer.sh"
REAL_PYTHON3="$(command -v python3)"

pass=0
fail=0
tmpdir=""

cleanup() {
  if [ -n "$tmpdir" ] && [ -d "$tmpdir" ]; then
    rm -rf "$tmpdir"
  fi
}
trap cleanup EXIT

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

# Test 1: sleep 0.5 — allow slack for shell and python startup on busy hosts.
out=$(bash "$TIMER" test-sleep-half sleep 0.5 2>&1)
timing=$(printf '%s\n' "$out" | extract_timing)
if timing_in_range "$timing" "0.40" "1.20"; then
  ok "sleep 0.5 timing is within 0.40s-1.20s (got: $timing)"
else
  fail "sleep 0.5 timing mismatch (got: '$timing', expected 0.40s-1.20s)"
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
if timing_in_range "$timing" "0.00" "60.00"; then
  ok "false: LARCH_HARNESS_TIMING emitted with contract-shaped timing (got: $timing)"
else
  fail "false: expected contract-shaped timing token, got '$timing'"
fi

# Test 4: backward wall clock clamps to 0.00s instead of emitting a negative token.
tmpdir=$(mktemp -d "${TMPDIR:-/tmp}/test-harness-timer.XXXXXX")
cat >"$tmpdir/python3" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

counter_file="${TEST_HARNESS_TIMER_COUNTER:?}"
if [ "${1:-}" = "-c" ] && [ "${2:-}" = "import time; print(time.time())" ]; then
  count=0
  if [ -f "$counter_file" ]; then
    count=$(cat "$counter_file")
  fi
  count=$((count + 1))
  printf '%s\n' "$count" >"$counter_file"
  if [ "$count" -eq 1 ]; then
    printf '100\n'
  else
    printf '99\n'
  fi
  exit 0
fi

exec "${REAL_PYTHON3:?}" "$@"
EOF
chmod +x "$tmpdir/python3"
counter_file="$tmpdir/counter"
out=$(PATH="$tmpdir:$PATH" REAL_PYTHON3="$REAL_PYTHON3" TEST_HARNESS_TIMER_COUNTER="$counter_file" bash "$TIMER" test-backward-clock true 2>&1)
timing=$(printf '%s\n' "$out" | extract_timing)
if [ "$timing" = "0.00s" ]; then
  ok "backward clock: timing clamps to 0.00s"
else
  fail "backward clock: expected 0.00s, got '$timing'"
fi

echo ""
printf 'Results: %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
