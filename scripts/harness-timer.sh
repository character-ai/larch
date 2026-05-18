#!/usr/bin/env bash
# Wraps one regression-harness test invocation to emit per-test timing.
# Usage: harness-timer.sh <test-name> <command> [args…]
# Prints LARCH_HARNESS_TIMING\t<name>\t<N>s to stdout on completion.
# Exits with the same exit code as <command>.
name="$1"; shift
start=$(date +%s)
"$@"
rc=$?
end=$(date +%s)
printf 'LARCH_HARNESS_TIMING\t%s\t%ds\n' "$name" "$((end - start))"
exit "$rc"
