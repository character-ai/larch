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
CODEX_PRESENT="${CODEX_PRESENT:-false}"
CURSOR_PRESENT="${CURSOR_PRESENT:-false}"
CODEX_AVAILABLE="${CODEX_AVAILABLE:-$CODEX_PRESENT}"
CURSOR_AVAILABLE="${CURSOR_AVAILABLE:-$CURSOR_PRESENT}"
CODEX_BINARY_FOUND="${CODEX_BINARY_FOUND:-false}"
CURSOR_BINARY_FOUND="${CURSOR_BINARY_FOUND:-false}"
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}"
POSITIONAL_KIND="${POSITIONAL_KIND:-}"
POSITIONAL_VALUE="${POSITIONAL_VALUE:-}"
hard_requested="${hard_requested:-false}"
partition_requested="${partition_requested:-false}"
brainstorm_requested="${brainstorm_requested:-false}"
approve_requested="${approve_requested:-false}"
skip_approve_requested="${skip_approve_requested:-false}"
no_dedup_requested="${no_dedup_requested:-false}"
run_id="${run_id:-}"
design_classification="${design_classification:-}"
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
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_require_plugin_root
_cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  printf '%s\n' "/design Step 0: CLAUDE_PLUGIN_ROOT is empty after export — skill loader must expand ${_cpr_literal} in the template line before Bash runs; abort" >&2
  exit 1
fi
LARCH_TIMING_SKILL=design "${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "design Step 0 — session setup" || true

# Contract pin for CI (scripts/test-design-structure.sh): python/cli.py session setup --prefix claude-design --skip-branch-check --skip-repo-check --check-reviewers
_ss_args=(--prefix claude-design --skip-branch-check --skip-repo-check --check-reviewers)
_ss_rc=0
_ss_out=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session setup "${_ss_args[@]}" 2>&1) || _ss_rc=$?
printf '%s\n' "$_ss_out"
if [ "$_ss_rc" -ne 0 ]; then
  exit "$_ss_rc"
fi

SESSION_TMPDIR="" SESSION_ID="" CODEX_AVAILABLE="" CURSOR_AVAILABLE="" CODEX_PRESENT="" CURSOR_PRESENT="" CODEX_BINARY_FOUND="" CURSOR_BINARY_FOUND=""
while IFS= read -r _line || [ -n "$_line" ]; do
  [ -z "$_line" ] && continue
  case "$_line" in
    SESSION_TMPDIR=*) SESSION_TMPDIR="${_line#SESSION_TMPDIR=}" ;;
    SESSION_ID=*) SESSION_ID="${_line#SESSION_ID=}" ;;
    CODEX_AVAILABLE=*) CODEX_AVAILABLE="${_line#CODEX_AVAILABLE=}" ;;
    CURSOR_AVAILABLE=*) CURSOR_AVAILABLE="${_line#CURSOR_AVAILABLE=}" ;;
    CODEX_PRESENT=*) CODEX_PRESENT="${_line#CODEX_PRESENT=}" ;;
    CURSOR_PRESENT=*) CURSOR_PRESENT="${_line#CURSOR_PRESENT=}" ;;
    CODEX_BINARY_FOUND=*) CODEX_BINARY_FOUND="${_line#CODEX_BINARY_FOUND=}" ;;
    CURSOR_BINARY_FOUND=*) CURSOR_BINARY_FOUND="${_line#CURSOR_BINARY_FOUND=}" ;;
  esac
done <<< "$_ss_out"

DESIGN_TMPDIR="${SESSION_TMPDIR:-}"
if [ -z "$DESIGN_TMPDIR" ] || [ -z "$SESSION_ID" ]; then
  printf '%s\n' "**⚠ /design: session setup output missing SESSION_TMPDIR or SESSION_ID**" >&2
  exit 1
fi

_step0_parsed_src="${HOME}/.cache/larch/sessions/step0-parsed-${CLAUDE_PID}.env"
if [ -f "$_step0_parsed_src" ]; then
  cp "$_step0_parsed_src" "$DESIGN_TMPDIR/.design-step0-parsed.env"
fi

DESIGN_TMPDIR="$DESIGN_TMPDIR" IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:-}" \
  "${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "design Step 0 — session setup" || true

_wdce_args=(
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session write-design-env
  --output "$DESIGN_TMPDIR/source-env.sh"
  --design-tmpdir "$DESIGN_TMPDIR"
  --session-id "$SESSION_ID"
  --claude-pid "$CLAUDE_PID"
)
[ -n "$CODEX_PRESENT" ] && _wdce_args+=(--codex-present "$CODEX_PRESENT")
[ -n "$CURSOR_PRESENT" ] && _wdce_args+=(--cursor-present "$CURSOR_PRESENT")
[ -n "$CODEX_AVAILABLE" ] && _wdce_args+=(--codex-available "$CODEX_AVAILABLE")
[ -n "$CURSOR_AVAILABLE" ] && _wdce_args+=(--cursor-available "$CURSOR_AVAILABLE")
[ -n "$CODEX_BINARY_FOUND" ] && _wdce_args+=(--codex-binary-found "$CODEX_BINARY_FOUND")
[ -n "$CURSOR_BINARY_FOUND" ] && _wdce_args+=(--cursor-binary-found "$CURSOR_BINARY_FOUND")
"${_wdce_args[@]}"
