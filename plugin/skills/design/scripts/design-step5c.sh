#!/usr/bin/env bash
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
FRESH_ATTEMPT=false
ORIGINAL_ARGS=("$@")

_arg_count=${#ORIGINAL_ARGS[@]}
if [ "$_arg_count" -ge 3 ] \
  && [ "${ORIGINAL_ARGS[$((_arg_count - 3))]}" = "--bgjob-child" ] \
  && [ "${ORIGINAL_ARGS[$((_arg_count - 2))]}" = "--merge-result-env" ] \
  && [ -n "${ORIGINAL_ARGS[$((_arg_count - 1))]}" ]; then
  BGJOB_CHILD=true
  MERGE_RESULT_ENV="${ORIGINAL_ARGS[$((_arg_count - 1))]}"
  set -- "${ORIGINAL_ARGS[@]:0:$((_arg_count - 3))}"
  ORIGINAL_ARGS=("$@")
fi
for _adapter_control in "$@"; do
  case "$_adapter_control" in
    --bgjob-child|--merge-result-env)
      printf '%s\n' 'design-step5c.sh: adapter child controls must be one terminal suffix' >&2
      exit 2
      ;;
  esac
done

FORWARD_ARGS=()
_before_public=true
for _arg in "${ORIGINAL_ARGS[@]}"; do
  if [ "$_before_public" = true ] && [ "$_arg" = "--" ]; then
    _before_public=false
  fi
  if [ "$_before_public" = true ] && [ "$_arg" = "--fresh-attempt" ]; then
    [ "$FRESH_ATTEMPT" = false ] || { printf '%s\n' 'design-step5c.sh: duplicate --fresh-attempt' >&2; exit 2; }
    FRESH_ATTEMPT=true
    continue
  fi
  FORWARD_ARGS[${#FORWARD_ARGS[@]}]="$_arg"
done
if [ "${#FORWARD_ARGS[@]}" -gt 0 ]; then
  set -- "${FORWARD_ARGS[@]}"
else
  set --
fi

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  CLAUDE_PLUGIN_ROOT="$(cd "$_script_dir/../../.." && pwd -P)"
fi
export CLAUDE_PLUGIN_ROOT

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; export CLAUDE_PLUGIN_ROOT; shift 2 ;;
    --skip-validate) shift ;;
    --) shift; break ;;
    *) shift ;;
  esac
done

if [ -n "${SESSION_ENV_PATH:-}" ]; then
  _resolver_args=(--resolve-session-env --session-env-path "$SESSION_ENV_PATH")
  [ -n "${CLAUDE_PID:-}" ] && _resolver_args[${#_resolver_args[@]}]=--owner-pid && _resolver_args[${#_resolver_args[@]}]="$CLAUDE_PID"
  _resolved_session_env="$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob adapt "${_resolver_args[@]}")" || {
      printf '%s\n' "${_resolved_session_env:-BGJOB_ERROR=session-env-resolution-failed}"
      exit 2
    }
  eval "$_resolved_session_env"
fi
if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' 'design-step5c.sh: DESIGN_TMPDIR required' >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
export DESIGN_TMPDIR
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2

publish_step5c_result() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - \
    "$DESIGN_TMPDIR/.design-step5c-status.env" "$MERGE_RESULT_ENV" "$DESIGN_TMPDIR" <<'PY'
import sys
from pathlib import Path

from larch import io as larch_io
from larch.design.design_core import design_write_merge_env

source, destination, root = map(Path, sys.argv[1:4])
values = larch_io.read_kvs(source, reject_cr=True, reject_symlink=True)
required = {
    "PUBLISH_RC", "PLAN_WRITE_OK", "PUBLISH_OK", "VALIDATE_STATUS",
    "FINAL_SUMMARY_PATH", "CLEANUP_ELIGIBLE",
}
if not required.issubset(values):
    raise SystemExit(1)
design_write_merge_env(path=destination, design_tmpdir=root, rows=values.items())
PY
}

if [ "$BGJOB_CHILD" = true ]; then
  set +e
  if [ "${#FORWARD_ARGS[@]}" -gt 0 ]; then
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5c "${FORWARD_ARGS[@]}"
  else
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5c
  fi
  _step5c_rc=$?
  set -e
  publish_step5c_result || exit 1
  exit "$_step5c_rc"
fi

_adapt_args=(
  --step design-step5c \
  --tmpdir "$DESIGN_TMPDIR" \
  --budget-s 21600
)
[ -n "${CLAUDE_PID:-}" ] && _adapt_args[${#_adapt_args[@]}]=--owner-pid && _adapt_args[${#_adapt_args[@]}]="$CLAUDE_PID"
[ -n "${SESSION_ENV_PATH:-}" ] && _adapt_args[${#_adapt_args[@]}]=--session-env-path && _adapt_args[${#_adapt_args[@]}]="$SESSION_ENV_PATH"
[ "$FRESH_ATTEMPT" = true ] && _adapt_args[${#_adapt_args[@]}]=--replace-completed-result
_step3_sidecar="$DESIGN_TMPDIR/.step3-review-result.env"
if [ -f "$_step3_sidecar" ] && [ ! -L "$_step3_sidecar" ]; then
  _step5c_input_fp="$(shasum -a 256 "$_step3_sidecar" 2>/dev/null | awk '{print $1}')" || _step5c_input_fp="compute-failed"
  [ -z "$_step5c_input_fp" ] && _step5c_input_fp="compute-failed"
else
  _step5c_input_fp="source-absent"
fi
_adapt_args[${#_adapt_args[@]}]=--input-fingerprint
_adapt_args[${#_adapt_args[@]}]="$_step5c_input_fp"
if [ "${#FORWARD_ARGS[@]}" -gt 0 ]; then
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob adapt "${_adapt_args[@]}" -- bash "$0" "${FORWARD_ARGS[@]}"
else
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob adapt "${_adapt_args[@]}" -- bash "$0"
fi
