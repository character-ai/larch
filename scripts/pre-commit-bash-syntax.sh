#!/usr/bin/env bash
# Parallel bash -n (syntax-check) wrapper for the pre-commit hook.
# Receives filenames from pre-commit and runs bash -n on each in parallel.
# On macOS /bin/bash is 3.2.57, so this doubles as a bash 3.2 parser check
# for developers on Mac; on Linux it uses whatever bash is on PATH.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
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

max_parallel="$(nproc 2>/dev/null \
              || sysctl -n hw.ncpu 2>/dev/null \
              || getconf _NPROCESSORS_ONLN 2>/dev/null \
              || echo 1)"
[ "${max_parallel:-0}" -ge 1 ] 2>/dev/null || max_parallel=1

printf '%s\0' "$@" | xargs -0 -n 1 -P "$max_parallel" bash -n --
