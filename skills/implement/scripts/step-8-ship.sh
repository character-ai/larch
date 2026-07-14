#!/usr/bin/env bash
# step-8-ship.sh — /implement Step 8 bgjob adapter and Python ship-driver child.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bgjob-child) BGJOB_CHILD=true; shift ;;
    --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
    --help) printf '%s\n' 'Usage: step-8-ship.sh'; exit 0 ;;
    *) printf '%s\n' "step-8-ship.sh: unknown argument: $1" >&2; exit 2 ;;
  esac
done

rehydrate_plugin_root() {
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
    # shellcheck source=/dev/null
    . "$IMPLEMENT_TMPDIR/plugin-root.env"
  fi
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
  fi
  export CLAUDE_PLUGIN_ROOT
}

read_state_key() {
  local key=$1 default_value=$2 line state_file
  state_file="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
  if [ -f "$state_file" ]; then
    line=$(grep "^${key}=" "$state_file" 2>/dev/null | tail -n 1 || true)
if [ -n "$line" ]; then
      printf '%s\n' "${line#*=}"
      return 0
    fi
  fi
  printf '%s\n' "$default_value"
}

require_value() {
  local name=$1 value=$2
  if [ -z "$value" ]; then
    printf 'step-8-ship.sh: missing %s (not exported and absent from ship-pr-state.sh)\n' "$name" >&2
    exit 2
  fi
}

run_child() {
  local clone_tag_env

  BRANCH_NAME_RESOLVED="${BRANCH_NAME:-$(read_state_key BRANCH_NAME "")}"
  ISSUE_NUMBER_RESOLVED="${ISSUE_NUMBER:-$(read_state_key ISSUE_NUMBER "")}"
  RUN_ID_RESOLVED="${RUN_ID:-$(read_state_key RUN_ID "")}"
  REPO_RESOLVED="${REPO:-$(read_state_key REPO "")}"
  MERGE_RESOLVED="${merge:-$(read_state_key MERGE "")}"
  DRAFT_RESOLVED="${draft:-$(read_state_key DRAFT "")}"
  FORKED_TARGET_RESOLVED="${forked_target:-$(read_state_key FORKED_TARGET "")}"
  REPO_UNAVAILABLE_RESOLVED="${REPO_UNAVAILABLE:-$(read_state_key REPO_UNAVAILABLE "")}"
  MANIFEST_PATH_RESOLVED="${MANIFEST_PATH:-$(read_state_key MANIFEST_PATH "")}"
  TOOL_LABEL_RESOLVED="${coder:-$(read_state_key TOOL_LABEL "")}"
  NO_ADMIN_FALLBACK_RESOLVED="${no_admin_fallback:-$(read_state_key NO_ADMIN_FALLBACK "")}"
  NO_LOGS_COMMIT_RESOLVED="${no_logs_commit:-$(read_state_key NO_LOGS_COMMIT "")}"

  require_value BRANCH_NAME "$BRANCH_NAME_RESOLVED"
  require_value RUN_ID "$RUN_ID_RESOLVED"
  require_value REPO "$REPO_RESOLVED"
  [ -n "$MERGE_RESOLVED" ] || MERGE_RESOLVED=false
  [ -n "$DRAFT_RESOLVED" ] || DRAFT_RESOLVED=false
  [ -n "$FORKED_TARGET_RESOLVED" ] || FORKED_TARGET_RESOLVED=false
  [ -n "$REPO_UNAVAILABLE_RESOLVED" ] || REPO_UNAVAILABLE_RESOLVED=false
  [ -n "$TOOL_LABEL_RESOLVED" ] || TOOL_LABEL_RESOLVED=claude
  [ -n "$NO_ADMIN_FALLBACK_RESOLVED" ] || NO_ADMIN_FALLBACK_RESOLVED=false
  [ -n "$NO_LOGS_COMMIT_RESOLVED" ] || NO_LOGS_COMMIT_RESOLVED=false

  bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-8-python-guard.sh
  clone_tag_env=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement clone-tag) || exit $?
  eval "$clone_tag_env"
  : "${EXPECTED_TMPDIR_BASENAME_PREFIX:?}"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe --step 8-pre-ship >&2
  exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr \
    --branch "$BRANCH_NAME_RESOLVED" \
    --issue "$ISSUE_NUMBER_RESOLVED" \
    --repo "$REPO_RESOLVED" \
    --run-id "$RUN_ID_RESOLVED" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --manifest-path "$MANIFEST_PATH_RESOLVED" \
    --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" \
    --tool-label "$TOOL_LABEL_RESOLVED" \
    --merge "$MERGE_RESOLVED" \
    --draft "$DRAFT_RESOLVED" \
    --forked "$FORKED_TARGET_RESOLVED" \
    --repo-unavailable "$REPO_UNAVAILABLE_RESOLVED" \
    --no-admin-fallback "$NO_ADMIN_FALLBACK_RESOLVED" \
    --no-logs-commit "$NO_LOGS_COMMIT_RESOLVED" \
    --result-env-path "$MERGE_RESULT_ENV" \
    --expected-session-id "$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)" \
    --expected-tmpdir-basename-prefix "$EXPECTED_TMPDIR_BASENAME_PREFIX"
}

rehydrate_plugin_root
export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

if [ "$BGJOB_CHILD" = true ]; then
  [ -n "$MERGE_RESULT_ENV" ] || { printf '%s\n' 'step-8-ship.sh: --merge-result-env is required in child mode' >&2; exit 2; }
  run_child
fi

STEP="implement-step8-ship"
exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob adapt \
  --step "$STEP" \
  --tmpdir "$IMPLEMENT_TMPDIR" \
  --budget-s 21600 \
  --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
  --replace-completed-result \
  -- \
  bash "$SCRIPT_DIR/step-8-ship.sh"
