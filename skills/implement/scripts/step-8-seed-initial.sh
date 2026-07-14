#!/usr/bin/env bash
# step-8-seed-initial.sh — create-if-absent initial ship-pr-state seeder.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
  # shellcheck source=/dev/null
  . "$IMPLEMENT_TMPDIR/plugin-root.env"
fi
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || CLAUDE_PLUGIN_ROOT=$PLUGIN_ROOT
export CLAUDE_PLUGIN_ROOT
clone_tag_env=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement clone-tag) || exit $?
eval "$clone_tag_env"
: "${EXPECTED_TMPDIR_BASENAME_PREFIX:?}"

ARG_MERGE=""
ARG_DRAFT=""
ARG_NO_ADMIN_FALLBACK=""
ARG_NO_LOGS_COMMIT=""
ARG_MANIFEST_PATH=""
ARG_TOOL_LABEL=""
ARG_STALL_TRACKING="false"
ARG_STALL_STEP=""
ARG_BAIL_REASON=""
ARG_BAIL_FAILURE_DETAIL_LOG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --merge) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --merge requires a value' >&2; exit 2; }; ARG_MERGE=$2; shift 2 ;;
    --draft) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --draft requires a value' >&2; exit 2; }; ARG_DRAFT=$2; shift 2 ;;
    --no-admin-fallback) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --no-admin-fallback requires a value' >&2; exit 2; }; ARG_NO_ADMIN_FALLBACK=$2; shift 2 ;;
    --no-logs-commit) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --no-logs-commit requires a value' >&2; exit 2; }; ARG_NO_LOGS_COMMIT=$2; shift 2 ;;
    --manifest-path) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --manifest-path requires a value' >&2; exit 2; }; ARG_MANIFEST_PATH=$2; shift 2 ;;
    --tool-label) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --tool-label requires a value' >&2; exit 2; }; ARG_TOOL_LABEL=$2; shift 2 ;;
    --stall-tracking) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --stall-tracking requires a value' >&2; exit 2; }; ARG_STALL_TRACKING=$2; shift 2 ;;
    --stall-step) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --stall-step requires a value' >&2; exit 2; }; ARG_STALL_STEP=$2; shift 2 ;;
    --bail-reason) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --bail-reason requires a value' >&2; exit 2; }; ARG_BAIL_REASON=$2; shift 2 ;;
    --bail-failure-detail-log) [ $# -ge 2 ] || { printf '%s\n' 'step-8-seed-initial.sh: --bail-failure-detail-log requires a value' >&2; exit 2; }; ARG_BAIL_FAILURE_DETAIL_LOG=$2; shift 2 ;;
    --help) printf '%s\n' 'Usage: step-8-seed-initial.sh [--merge true|false] [--draft true|false] [--stall-step STEP]'; exit 0 ;;
    *) printf 'step-8-seed-initial.sh: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

read_session_key() {
  local key=$1 default_value=$2 file
  file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
  if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
  else
    printf '%s\n' "$default_value"
  fi
}

read_kv_file() {
  local file=$1 key=$2 value
  if [ -f "$file" ]; then
    if value=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" kv get --file "$file" --key "$key" --match first 2>/dev/null); then
      printf '%s\n' "$value"
      return 0
    fi
  fi
  printf '\n'
}

read_sentinel_key() {
  local key=$1 sentinel out value
  sentinel="$IMPLEMENT_TMPDIR/parent-issue.md"
  if [ -f "$sentinel" ]; then
    out=$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" tracking-issue read --sentinel "$sentinel" 2>/dev/null || true)
    if value=$(printf '%s\n' "$out" | python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" kv get --key "$key" --match first 2>/dev/null); then
      printf '%s\n' "$value"
      return 0
    fi
  fi
  printf '\n'
}

first_nonempty() {
  local value
  for value in "$@"; do
    if [ -n "$value" ]; then
      printf '%s\n' "$value"
      return 0
    fi
  done
  printf '\n'
}

state_file="$IMPLEMENT_TMPDIR/ship-pr-state.sh"
if [ -s "$state_file" ] && grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=' "$state_file"; then
  printf '%s\n' 'step-8-seed-initial.sh: initial ship state is create-if-absent only; refusing to re-seed non-empty ship-pr-state.sh' >&2
  exit 2
fi

bootstrap_file="$IMPLEMENT_TMPDIR/bootstrap-routing.env"
seed_file="$IMPLEMENT_TMPDIR/ship-seed-input.env"
bootstrap_coder=$(read_kv_file "$bootstrap_file" coder)
case "$bootstrap_coder" in
  codex) mapped_tool=Codex ;;
  cursor) mapped_tool=Cursor ;;
  "") mapped_tool= ;;
  *) mapped_tool=claude ;;
esac

parent_issue_file="$IMPLEMENT_TMPDIR/parent-issue.md"
BRANCH_NAME_RESOLVED=$(first_nonempty "$(read_kv_file "$bootstrap_file" BRANCH_NAME)" "$(read_kv_file "$parent_issue_file" BRANCH_NAME)" "$(read_sentinel_key BRANCH_NAME)")
ISSUE_NUMBER_RESOLVED=$(first_nonempty "$(read_kv_file "$bootstrap_file" ISSUE_NUMBER)" "$(read_kv_file "$parent_issue_file" ISSUE_NUMBER)" "$(read_sentinel_key ISSUE_NUMBER)")
RUN_ID_RESOLVED=$(first_nonempty "$(read_kv_file "$bootstrap_file" RUN_ID)" "$(read_session_key LARCH_RUN_ID "")" "$(read_kv_file "$parent_issue_file" RUN_ID)" "$(read_sentinel_key RUN_ID)")
REPO_RESOLVED=$(first_nonempty "$(read_kv_file "$bootstrap_file" REPO)" "$(read_session_key REPO "")")

if [ -z "$BRANCH_NAME_RESOLVED" ]; then
  printf '%s\n' 'step-8-seed-initial.sh: BRANCH_NAME is required but missing from durable inputs' >&2
  exit 2
fi
if [ -z "$ISSUE_NUMBER_RESOLVED" ] || ! printf '%s' "$ISSUE_NUMBER_RESOLVED" | grep -Eq '^[0-9]+$'; then
  printf '%s\n' 'step-8-seed-initial.sh: ISSUE_NUMBER must be a non-empty digit value' >&2
  exit 2
fi
if [ -z "$RUN_ID_RESOLVED" ]; then
  printf '%s\n' 'step-8-seed-initial.sh: RUN_ID is required but missing from durable inputs' >&2
  exit 2
fi
if [ -z "$REPO_RESOLVED" ]; then
  printf '%s\n' 'step-8-seed-initial.sh: REPO is required but missing from durable inputs' >&2
  exit 2
fi
REPO_UNAVAILABLE_RESOLVED=$(first_nonempty "$(read_kv_file "$bootstrap_file" REPO_UNAVAILABLE)" "$(read_session_key REPO_UNAVAILABLE "")" false)
FORKED_TARGET_RESOLVED=$(first_nonempty "$(read_kv_file "$seed_file" FORKED_TARGET)" "$(read_session_key FORKED_TARGET "")" false)
DEFERRED_RESOLVED=$(first_nonempty "$(read_kv_file "$bootstrap_file" DEFERRED)" "$(read_kv_file "$seed_file" DEFERRED)" false)
MERGE_RESOLVED=$(first_nonempty "$ARG_MERGE" "$(read_kv_file "$seed_file" MERGE)" false)
DRAFT_RESOLVED=$(first_nonempty "$ARG_DRAFT" "$(read_kv_file "$seed_file" DRAFT)" false)
NO_ADMIN_FALLBACK_RESOLVED=$(first_nonempty "$ARG_NO_ADMIN_FALLBACK" "$(read_kv_file "$seed_file" NO_ADMIN_FALLBACK)" false)
NO_LOGS_COMMIT_RESOLVED=$(first_nonempty "$ARG_NO_LOGS_COMMIT" "$(read_kv_file "$seed_file" NO_LOGS_COMMIT)" false)
MANIFEST_PATH_RESOLVED=$(first_nonempty "$ARG_MANIFEST_PATH" "$(read_kv_file "$seed_file" MANIFEST_PATH)")
TOOL_LABEL_RESOLVED=$(first_nonempty "$ARG_TOOL_LABEL" "$(read_kv_file "$seed_file" TOOL_LABEL)" "$mapped_tool" claude)
EXPECTED_SESSION_ID_RESOLVED=""
[ -f "$IMPLEMENT_TMPDIR/session-id" ] && EXPECTED_SESSION_ID_RESOLVED=$(cat "$IMPLEMENT_TMPDIR/session-id" 2>/dev/null || true)

python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship seed-initial-state --tmpdir "$IMPLEMENT_TMPDIR" --state-file "$state_file" --branch "$BRANCH_NAME_RESOLVED" --issue "$ISSUE_NUMBER_RESOLVED" --repo "$REPO_RESOLVED" --run-id "$RUN_ID_RESOLVED" --manifest-path "$MANIFEST_PATH_RESOLVED" --tool-label "$TOOL_LABEL_RESOLVED" --merge "$MERGE_RESOLVED" --draft "$DRAFT_RESOLVED" --forked "$FORKED_TARGET_RESOLVED" --repo-unavailable "$REPO_UNAVAILABLE_RESOLVED" --deferred "$DEFERRED_RESOLVED" --no-admin-fallback "$NO_ADMIN_FALLBACK_RESOLVED" --no-logs-commit "$NO_LOGS_COMMIT_RESOLVED" --expected-session-id "$EXPECTED_SESSION_ID_RESOLVED" --expected-tmpdir-basename-prefix "$EXPECTED_TMPDIR_BASENAME_PREFIX" --stall-tracking "$ARG_STALL_TRACKING" --stall-step "$ARG_STALL_STEP" --bail-reason "$ARG_BAIL_REASON" --bail-failure-detail-log "$ARG_BAIL_FAILURE_DETAIL_LOG"
