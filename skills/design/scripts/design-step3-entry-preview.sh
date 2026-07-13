#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2317,SC2329,SC2206,SC2207
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
MODE=""
SITE=""
SUMMARY_OUTCOME="${SUMMARY_OUTCOME:-}"
SKIP_VALIDATE=""
PUBLIC_ARGV_WORDS=()

# Prompt-side values may be supplied only as environment variables by Claude Code.
# Default them before sourced session env overrides to preserve the old inline-fence no-set-u behavior.
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
SESSION_TMPDIR="${SESSION_TMPDIR:-}"
SESSION_ID="${SESSION_ID:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
ISSUE_TITLE="${ISSUE_TITLE:-}"
HAS_CLARIFY_LABEL="${HAS_CLARIFY_LABEL:-false}"
REPO="${REPO:-}"
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
POSITIONAL_KIND="${POSITIONAL_KIND:-}"
POSITIONAL_VALUE="${POSITIONAL_VALUE:-}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
STEP3_REVIEW_LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS:-}"
LOOP_STATUS="${LOOP_STATUS:-}"
VALIDATE_STATUS="${VALIDATE_STATUS:-}"
VALIDATE_DEFECT_COUNT="${VALIDATE_DEFECT_COUNT:-}"
VALIDATE_UNSAFE_TOKEN_COUNT="${VALIDATE_UNSAFE_TOKEN_COUNT:-}"
VALIDATE_SKIPPED_COUNT="${VALIDATE_SKIPPED_COUNT:-}"
VALIDATE_LOG_FILE="${VALIDATE_LOG_FILE:-}"
_validator_target_file="${_validator_target_file:-}"
PUBLISH_OK="${PUBLISH_OK:-}"
PLAN_WRITE_OK="${PLAN_WRITE_OK:-}"
STANDALONE_HEAVY_FAILED="${STANDALONE_HEAVY_FAILED:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --site) SITE="$2"; shift 2 ;;
    --snapshot-original) SNAPSHOT_ORIGINAL=true; shift ;;
    --outcome) SUMMARY_OUTCOME="$2"; shift 2 ;;
    --skip-validate) SKIP_VALIDATE=1; shift ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --) shift; PUBLIC_ARGV_WORDS=("$@"); break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

design_require_plugin_root() {
  _cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
  if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort" >&2
    exit 1
  fi
  if [ "${CLAUDE_PLUGIN_ROOT:-}" = "$_cpr_literal" ]; then
    printf '%s\n' "/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal ${_cpr_literal}; abort" >&2
    exit 1
  fi
  export CLAUDE_PLUGIN_ROOT
}

design_source_env_optional() {
  if [ -z "${SESSION_ENV_PATH:-}" ]; then
    return 0
  fi
  if [ -L "$SESSION_ENV_PATH" ]; then
    # PID-keyed symlink: resolve through the trusted session resolver so a
    # swapped link or replaced target cannot redirect what gets dot-sourced.
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] || [ -z "${CLAUDE_PID:-}" ]; then
      printf '%s\n' "/design wrapper: refusing session-env symlink without plugin root and PID" >&2
      exit 1
    fi
    _resolved_env_line="$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session resolve-trusted-design-env \
      --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" 2>/dev/null)" || {
      printf '%s\n' "/design wrapper: refusing untrusted session-env symlink: $SESSION_ENV_PATH" >&2
      exit 1
    }
    case "$_resolved_env_line" in
      TRUSTED_SOURCE=*) ;;
      *) printf '%s\n' "/design wrapper: unresolvable session-env symlink: $SESSION_ENV_PATH" >&2; exit 1 ;;
    esac
    _resolved_env="${_resolved_env_line#TRUSTED_SOURCE=}"
    if [ -f "$_resolved_env" ]; then
      # shellcheck source=/dev/null
      . "$_resolved_env"
    fi
    return 0
  fi
  if [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_source_env_optional
design_derive_binary_found() {
  if [ -z "${CODEX_BINARY_FOUND:-}" ]; then
    if command -v codex >/dev/null 2>&1; then CODEX_BINARY_FOUND=true; else CODEX_BINARY_FOUND=false; fi
  fi
  if [ -z "${CURSOR_BINARY_FOUND:-}" ]; then
    if command -v cursor >/dev/null 2>&1; then CURSOR_BINARY_FOUND=true; else CURSOR_BINARY_FOUND=false; fi
  fi
  export CODEX_BINARY_FOUND CURSOR_BINARY_FOUND
}
design_derive_binary_found
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
_step3_entry_tmpdir_allowed=0
if python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from session_env import validate_design_tmpdir; ok, _ = validate_design_tmpdir(sys.argv[2]); sys.exit(0 if ok else 1)' \
    "${CLAUDE_PLUGIN_ROOT}/python" "$DESIGN_TMPDIR" 2>/dev/null; then
  _step3_entry_tmpdir_allowed=1
fi
if [[ "$_step3_entry_tmpdir_allowed" -eq 1 && -d "$DESIGN_TMPDIR" && -e "$DESIGN_TMPDIR/.step3-entry-plan-printed" ]]; then
  exit 0
fi
_preview_out="$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review preview \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --variant step3)"
printf '%s
' "$_preview_out"
if [[ -d "$DESIGN_TMPDIR" && "$_preview_out" == *'## Plan Candidate for Review'* ]]; then
  touch "$DESIGN_TMPDIR/.step3-entry-plan-printed" || true
fi
