#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2154
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
MODE="regular"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

DESIGN_TMPDIR=""
if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  # shellcheck source=/dev/null
  . "$SESSION_ENV_PATH"
fi
if [[ -z "${DESIGN_TMPDIR:-}" ]]; then
  printf '%s\n' "$0: DESIGN_TMPDIR required after session rehydration" >&2
  exit 1
fi

_launched_paths=()
case "${MODE:-regular}" in
  regular)
    [[ "${CURSOR_AVAILABLE:-$CURSOR_PRESENT}" == true ]] && _launched_paths+=("$DESIGN_TMPDIR/cursor-sketch-arch-output.txt")
    if [[ "${CODEX_AVAILABLE:-$CODEX_PRESENT}" == true ]]; then
      _launched_paths+=("$DESIGN_TMPDIR/codex-sketch-innovation-output.txt")
      _launched_paths+=("$DESIGN_TMPDIR/codex-sketch-pragmatic-output.txt")
    fi
    ;;
  quick)
    [[ "${CURSOR_AVAILABLE:-$CURSOR_PRESENT}" == true ]] && _launched_paths+=("$DESIGN_TMPDIR/cursor-sketch-generic-output.txt")
    [[ "${CODEX_AVAILABLE:-$CODEX_PRESENT}" == true ]] && _launched_paths+=("$DESIGN_TMPDIR/codex-sketch-generic-output.txt")
    ;;
  *)
    printf '%s\n' "$0: --mode required (regular|quick)" >&2
    exit 2
    ;;
esac

{
  if ((${#_launched_paths[@]} > 0)); then
    printf '%s\n' "${_launched_paths[@]}"
  fi
} >"$DESIGN_TMPDIR/sketch-launched-paths.txt"

printf 'SKETCH_LAUNCHED_COUNT=%s\n' "${#_launched_paths[@]}"
