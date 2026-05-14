#!/usr/bin/env bash
# Regression harness for detect-wholesale-rejection.sh.

set -euo pipefail

DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)

assert_stdout_cap() {
    local text="$1" cap="${2:-2048}" bytes
    bytes=${#text}
    [[ "$bytes" -le "$cap" ]] || { echo "FAIL: stdout ${bytes}B > ${cap}B cap" >&2; exit 1; }
}

out=$("$DIR/detect-wholesale-rejection.sh" --accepted-count 0)
assert_stdout_cap "$out"
grep -Fq 'TERMINATE_EARLY=true' <<< "$out"
out=$("$DIR/detect-wholesale-rejection.sh" --accepted-count 1)
assert_stdout_cap "$out"
grep -Fq 'TERMINATE_EARLY=false' <<< "$out"
echo "All assertions passed."
