#!/usr/bin/env bash
# Parallel shellcheck wrapper for the local pre-commit hook.
# Consumes filename arguments from pre-commit (via $@) and runs
# Invokes shellcheck -x on each file in parallel (one process per file).
# The hook runs in a pre-commit-managed Python env whose dependencies
# include shellcheck-py==0.10.0.1, so `shellcheck` on PATH inside the hook
# env resolves to the pinned 0.10.0 binary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

# Zero-args fast path: pre-commit may invoke us with no matching files
# after type/file filtering. BSD xargs lacks --no-run-if-empty, so
# return early to avoid spurious zero-arg shellcheck invocation.
if [ "$#" -eq 0 ]; then
  exit 0
fi

if ! command -v shellcheck >/dev/null 2>&1; then
  echo "pre-commit-shellcheck.sh: shellcheck binary not found on PATH" >&2
  echo "  expected: shellcheck-py-bundled binary inside the pre-commit hook env" >&2
  echo "  if running outside pre-commit: install via apt-get install shellcheck (Linux) or brew install shellcheck (macOS)" >&2
  exit 1
fi

# Portable CPU count: nproc (Linux), sysctl (macOS), getconf, fallback 1.
max_parallel="$(nproc 2>/dev/null \
              || sysctl -n hw.ncpu 2>/dev/null \
              || getconf _NPROCESSORS_ONLN 2>/dev/null \
              || echo 1)"
# Defensive clamp: xargs -P 0 is implementation-defined.
[ "${max_parallel:-0}" -ge 1 ] 2>/dev/null || max_parallel=1

# NUL-delimited paths to handle filenames with spaces; -- guards against
# any leading-dash filename being misinterpreted as a shellcheck option.
# xargs exits non-zero if any child failed -> we propagate that exit.
printf '%s\0' "$@" | xargs -0 -n 1 -P "$max_parallel" shellcheck -x --
