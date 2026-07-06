#!/usr/bin/env bash
# step-8-ship.sh — /implement Step 8+ Python ship driver wrapper.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  # shellcheck source=/dev/null
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
export CLAUDE_PLUGIN_ROOT
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
HANDOFF_CAPTURE="$IMPLEMENT_TMPDIR/.step-8-ship-handoff.stdout-capture"
HANDOFF_RC="$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"
HANDOFF_JSON="$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"
rm -f "$HANDOFF_RC" "$HANDOFF_JSON" 2>/dev/null || true
: >"$HANDOFF_CAPTURE"

persist_handoff() {
  local rc=$? line last_json=
  set +e
  printf '%s\n' "$rc" >"$HANDOFF_RC" 2>/dev/null || true
  if [ -f "$HANDOFF_CAPTURE" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        \{*\})
          if printf '%s' "$line" | grep -Fq '"outcome"'; then
            last_json=$line
          fi
          ;;
      esac
    done <"$HANDOFF_CAPTURE"
  fi
  if [ -n "$last_json" ]; then
    printf '%s\n' "$last_json" >"$HANDOFF_JSON" 2>/dev/null || true
  else
    rm -f "$HANDOFF_JSON" 2>/dev/null || true
  fi
  rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true
  return 0
}
trap persist_handoff EXIT

run_and_capture_stdout() {
  local rc
  set +e
  "$@" | tee -a "$HANDOFF_CAPTURE"
  rc=${PIPESTATUS[0]}
  set -e
  return "$rc"
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

# Write bg-wait marker so hooks can deny Monitor/TaskOutput/progress probes
# during the long Step 8 ship-pr wait. Fail-open: marker failures must not
# abort ship-pr. The EXIT trap writes handoff rc/json first, then removes it.
rm -f "$IMPLEMENT_TMPDIR/no-progress-turns.count" "$IMPLEMENT_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
rm -f "$IMPLEMENT_TMPDIR/no-progress-stop-block-emitted" 2>/dev/null || true
rm -f "$IMPLEMENT_TMPDIR"/bg-poll-guard-task-output-read.*.count 2>/dev/null || true
rm -f "$IMPLEMENT_TMPDIR/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count" 2>/dev/null || true
_step8_start=$(date +%s 2>/dev/null) || _step8_start=0
case "$_step8_start" in ''|*[!0-9]*) _step8_start=0 ;; esac
_step8_claude_pid="${LARCH_BG_POLL_GUARD_SESSION_PID:-${PPID:-}}"
_step8_clone_path=""
if [ -f "$IMPLEMENT_TMPDIR/.larch-keepalive" ] && [ ! -L "$IMPLEMENT_TMPDIR/.larch-keepalive" ]; then
  _step8_clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$IMPLEMENT_TMPDIR/.larch-keepalive" 2>/dev/null || true)
fi
printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=implement-step8-ship\nTIMEOUT_S=21600\nCLONE_PATH=%s\n' \
  "$$" "$_step8_claude_pid" "$_step8_start" "$_step8_clone_path" >"$IMPLEMENT_TMPDIR/.bg-wait-active" 2>/dev/null || true

run_and_capture_stdout bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-8-python-guard.sh
clone_tag_env=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement clone-tag) || exit $?
eval "$clone_tag_env"
: "${EXPECTED_TMPDIR_BASENAME_PREFIX:?}"
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe --step 8-pre-ship >&2
run_and_capture_stdout python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr \
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
  --expected-session-id "$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)" \
  --expected-tmpdir-basename-prefix "$EXPECTED_TMPDIR_BASENAME_PREFIX"
