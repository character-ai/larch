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
    local argument relative manifest_output manifest_path
    local manifest_paths=()
    if ! manifest_output=$(larch_residual_paths); then
        return 1
    fi
    while IFS= read -r manifest_path; do
        manifest_paths[${#manifest_paths[@]}]="$manifest_path"
    done <<<"$manifest_output"
    for argument in "$@"; do
        relative=$argument
        case "$relative" in
            "$REPO_ROOT"/*) relative=${relative#"$REPO_ROOT"/} ;;
        esac
        for manifest_path in "${manifest_paths[@]}"; do
            if [ "$relative" = "$manifest_path" ]; then
                printf '%s\0' "$argument"
                break
            fi
        done
    done
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
