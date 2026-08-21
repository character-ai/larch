#!/usr/bin/env bash
# step-2-dispatch.sh — /implement Step 2 durable dispatcher adapter.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
DISPATCH_ARGS=()
REPLACE_COMPLETED_RESULT=false
while [ $# -gt 0 ]; do
  case "$1" in
    --bgjob-child) BGJOB_CHILD=true; shift ;;
    --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
    --answers) [ $# -ge 2 ] || exit 2; REPLACE_COMPLETED_RESULT=true; DISPATCH_ARGS+=("$1" "$2"); shift 2 ;;
    --help) printf '%s\n' 'Usage: step-2-dispatch.sh --coder CODER [--answers PATH]'; exit 0 ;;
    *) DISPATCH_ARGS+=("$1"); shift ;;
  esac
done

if [ "${#DISPATCH_ARGS[@]}" -gt 0 ]; then
  export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
  if [ "$BGJOB_CHILD" = true ]; then
    [ -n "$MERGE_RESULT_ENV" ] || { printf '%s\n' 'step-2-dispatch.sh: --merge-result-env is required in child mode' >&2; exit 2; }
    exec "$PLUGIN_ROOT/scripts/larch.sh" implement run-dispatch --implement-tmpdir "$IMPLEMENT_TMPDIR" --bgjob-child --merge-result-env "$MERGE_RESULT_ENV" "${DISPATCH_ARGS[@]}"
  fi

  [ -n "${LARCH_CLAUDE_PID:-}" ] || LARCH_CLAUDE_PID=$PPID
  if [ "$REPLACE_COMPLETED_RESULT" = true ]; then
    exec "$PLUGIN_ROOT/scripts/larch.sh" bgjob adapt \
      --step implement-step2-dispatch \
      --tmpdir "$IMPLEMENT_TMPDIR" \
      --budget-s 7200 \
      --owner-pid "$LARCH_CLAUDE_PID" \
      --replace-completed-result \
      -- \
      bash "$SCRIPT_DIR/step-2-dispatch.sh" "${DISPATCH_ARGS[@]}"
  fi
  exec "$PLUGIN_ROOT/scripts/larch.sh" bgjob adapt \
    --step implement-step2-dispatch \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s 7200 \
    --owner-pid "$LARCH_CLAUDE_PID" \
    -- \
    bash "$SCRIPT_DIR/step-2-dispatch.sh" "${DISPATCH_ARGS[@]}"
fi

printf '%s\n' 'step-2-dispatch.sh: dispatch arguments are required' >&2
exit 2
