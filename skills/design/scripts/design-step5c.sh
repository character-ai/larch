#!/usr/bin/env bash
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
RUN_STEP5C_CHILD=false
ORIGINAL_ARGS=("$@")

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  CLAUDE_PLUGIN_ROOT="$(cd "$_script_dir/../../.." && pwd -P)"
fi
export CLAUDE_PLUGIN_ROOT

while [ "$#" -gt 0 ]; do
  case "$1" in
    --run-step5c-child) RUN_STEP5C_CHILD=true; shift ;;
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; export CLAUDE_PLUGIN_ROOT; shift 2 ;;
    --skip-validate) shift ;;
    --) shift; break ;;
    *) shift ;;
  esac
done

if [ "$RUN_STEP5C_CHILD" = true ]; then
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5c "${ORIGINAL_ARGS[@]:1}"
fi

if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
  # shellcheck source=/dev/null
  . "$SESSION_ENV_PATH"
fi
if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' 'design-step5c.sh: DESIGN_TMPDIR required' >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
export DESIGN_TMPDIR
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2

step5c_recreate_merge_env() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DESIGN_TMPDIR/.design-step5c-status.env" "$DESIGN_TMPDIR" <<'PY'
from pathlib import Path
import sys
from larch.design.design_core import design_recreate_merge_env

design_recreate_merge_env(path=Path(sys.argv[1]), design_tmpdir=Path(sys.argv[2]))
PY
}

step5c_bgjob_registry_state() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DESIGN_TMPDIR" <<'PY'
from pathlib import Path
import sys
from larch.bgjob import registry

path, entry = registry.read_for(tmpdir=Path(sys.argv[1]), step="design-step5c")
if entry is None:
    print("missing")
    raise SystemExit(0)
child_live = registry.child_liveness(entry).live
if child_live or registry.daemon_liveness(entry).live:
    print("live")
    raise SystemExit(0)
registry.unlink_entry(path)
print("cleared")
PY
}

_result_env="$DESIGN_TMPDIR/bgjob/design-step5c.result.env"
if [ -L "$_result_env" ]; then
  printf '%s\n' 'design-step5c.sh: existing bgjob result env must not be a symlink' >&2
  exit 1
fi
if [ -e "$_result_env" ] && [ ! -f "$_result_env" ]; then
  printf '%s\n' 'design-step5c.sh: existing bgjob result env must be a regular file' >&2
  exit 1
fi
if [ -f "$_result_env" ]; then
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait \
    --step design-step5c \
    --tmpdir "$DESIGN_TMPDIR" \
    --max-wait-s 0
fi
_registry_state="$(step5c_bgjob_registry_state)" || {
  printf '%s\n' 'BGJOB_ERROR=registry-check-failed'
  exit 2
}
if [ "$_registry_state" = live ]; then
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait \
    --step design-step5c \
    --tmpdir "$DESIGN_TMPDIR" \
    --max-wait-s 0
fi

mkdir -p "$DESIGN_TMPDIR/.completed" "$DESIGN_TMPDIR/bgjob"
rm -f "$DESIGN_TMPDIR/.completed/step-5c-terminal" "$DESIGN_TMPDIR/bgjob/design-step5c.result.env" 2>/dev/null || true
step5c_recreate_merge_env

_owner_args=()
if [ -n "${CLAUDE_PID:-}" ]; then
  _owner_args=(--owner-pid "$CLAUDE_PID")
fi
exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
  --step design-step5c \
  --tmpdir "$DESIGN_TMPDIR" \
  --budget-s 21600 \
  "${_owner_args[@]}" \
  --sentinel "$DESIGN_TMPDIR/.completed/step-5c-terminal" \
  --merge-result-env "$DESIGN_TMPDIR/.design-step5c-status.env" \
  -- bash "$0" --run-step5c-child "${ORIGINAL_ARGS[@]}"
