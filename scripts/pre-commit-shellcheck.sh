#!/usr/bin/env bash
# Parallel shellcheck wrapper for the local pre-commit hook.
# Consumes filename arguments from pre-commit (via $@) and runs
# Invokes shellcheck -x on each file in parallel (one process per file).
# The hook runs in a pre-commit-managed Python env whose dependencies
# include shellcheck-py==0.10.0.1, so `shellcheck` on PATH inside the hook
# env resolves to the pinned 0.10.0 binary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT="$REPO_ROOT"
fi
export CLAUDE_PLUGIN_ROOT

if [ -z "${LARCH_BINARY:-}" ]; then
    for candidate in "$REPO_ROOT/target/debug/larch" "$REPO_ROOT/target/release/larch"; do
        if [ -x "$candidate" ]; then
            LARCH_BINARY="$candidate"
            break
        fi
    done
fi
if [ -n "${LARCH_BINARY:-}" ]; then
    export LARCH_BINARY
fi

larch_residual_paths() {
    "$CLAUDE_PLUGIN_ROOT/scripts/larch.sh" residual-bash paths --root "$REPO_ROOT"
}

filter_manifest_args() {
    if [ "$#" -eq 0 ] || [ ! -f "$REPO_ROOT/scripts/residual-bash-paths.txt" ]; then
        printf '%s\0' "$@"
        return
    fi
    python3 - "$REPO_ROOT" "$@" <<'PY'
import os
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
args = sys.argv[2:]
manifest = subprocess.run(
    [str(root / "scripts/larch.sh"), "residual-bash", "paths", "--root", str(root)],
    env={**os.environ, "CLAUDE_PLUGIN_ROOT": os.environ.get("CLAUDE_PLUGIN_ROOT", str(root))},
    check=True,
    text=True,
    capture_output=True,
).stdout.splitlines()
allowed = set(manifest)
for arg in args:
    rel = arg
    prefix = str(root) + "/"
    if rel.startswith(prefix):
        rel = rel[len(prefix):]
    if rel in allowed:
        print(arg, end="\0")
PY
}

# Zero-args fast path: pre-commit may invoke us with no matching files
# after type/file filtering. BSD xargs lacks --no-run-if-empty, so
# return early to avoid spurious zero-arg shellcheck invocation.
if [ "$#" -eq 0 ]; then
  if [ -f "$REPO_ROOT/scripts/residual-bash-paths.txt" ]; then
    manifest_paths=()
    while IFS= read -r rel; do
      manifest_paths+=("$REPO_ROOT/$rel")
    done < <(larch_residual_paths)
    set -- "${manifest_paths[@]}"
  else
    exit 0
  fi
else
  filtered=()
  while IFS= read -r -d '' item; do
    filtered+=("$item")
  done < <(filter_manifest_args "$@")
  if [ "${#filtered[@]}" -eq 0 ]; then
    exit 0
  fi
  set -- "${filtered[@]}"
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
# SC2329: shellcheck 0.11.0 warns on functions "never invoked" — false positive
# for trap handlers and functions called via sourced/inherited envs.
printf '%s\0' "$@" | xargs -0 -n 1 -P "$max_parallel" shellcheck -x --exclude=SC2329 --
