#!/usr/bin/env bash
# Wraps one regression-harness test invocation to emit per-test timing.
# Usage: harness-timer.sh <test-name> <command> [args…]
# Prints LARCH_HARNESS_TIMING\t<name>\t<N.NN>s to stdout on completion.
# Exits with the same exit code as <command>.
# set -e intentionally omitted: rc=$? must capture non-zero inner exit.
name="$1"; shift
start=$(python3 -c 'import time; print(time.time())')
"$@"
rc=$?
end=$(python3 -c 'import time; print(time.time())')
elapsed=$(python3 -c "print(f'{max(0.0, $end - $start):.2f}')")
printf 'LARCH_HARNESS_TIMING\t%s\t%ss\n' "$name" "$elapsed"
exit "$rc"
