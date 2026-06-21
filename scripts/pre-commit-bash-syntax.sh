#!/usr/bin/env bash
# Parallel bash -n (syntax-check) wrapper for the pre-commit hook.
# Receives filenames from pre-commit and runs bash -n on each in parallel.
# On macOS /bin/bash is 3.2.57, so this doubles as a bash 3.2 parser check
# for developers on Mac; on Linux it uses whatever bash is on PATH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

if [ "$#" -eq 0 ]; then
  if [ -f "$REPO_ROOT/scripts/residual-bash-paths.txt" ]; then
    manifest_paths=()
    while IFS= read -r rel; do
      manifest_paths+=("$REPO_ROOT/$rel")
    done < <(python3 "$REPO_ROOT/python/cli.py" residual-bash paths --root "$REPO_ROOT")
    set -- "${manifest_paths[@]}"
  else
    exit 0
  fi
fi

max_parallel="$(nproc 2>/dev/null \
              || sysctl -n hw.ncpu 2>/dev/null \
              || getconf _NPROCESSORS_ONLN 2>/dev/null \
              || echo 1)"
[ "${max_parallel:-0}" -ge 1 ] 2>/dev/null || max_parallel=1

printf '%s\0' "$@" | xargs -0 -n 1 -P "$max_parallel" bash -n --
