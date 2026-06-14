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
CLARIFY_HARD_HALT_RC="${CLARIFY_HARD_HALT_RC:-1}"
CLARIFY_FAILURE_LOG="${CLARIFY_FAILURE_LOG:-}"

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
    --exit-code) CLARIFY_HARD_HALT_RC="$2"; shift 2 ;;
    --failure-detail-log) CLARIFY_FAILURE_LOG="$2"; shift 2 ;;
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
design_source_env_optional
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 0b clarify hard halt: DESIGN_TMPDIR required" >&2
  exit 1
fi
design_tmpdir_canon=$(cd "$DESIGN_TMPDIR" && pwd -P)
[ -f "$design_tmpdir_canon/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$design_tmpdir_canon" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}

detail_log="${CLARIFY_FAILURE_LOG:-$design_tmpdir_canon/clarify-loop.failure.log}"
case "$detail_log" in
  "$design_tmpdir_canon"/*) ;;
  *) detail_log="$design_tmpdir_canon/clarify-loop.failure.log" ;;
esac
[ -f "$detail_log" ] || printf 'clarify loop hard halt\n' >"$detail_log"

stage_helper="$CLAUDE_PLUGIN_ROOT/skills/design/scripts/design-stage-terminal-state.sh"
set +e
"$stage_helper" --design-tmpdir "$design_tmpdir_canon" \
  --outcome failed-clarify \
  --step clarify \
  --phase clarify-loop \
  --site clarify-loop \
  --trigger failed \
  --bail-reason clarify-hard-halt \
  --exit-code "$CLARIFY_HARD_HALT_RC" \
  --source-script clarify-loop \
  --summary-outcome failed-clarify \
  --failure-detail-log "$detail_log" \
  >"$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log" \
  2>"$DESIGN_TMPDIR/design-stage-terminal-state.stderr.log"
stage_rc=$?
set -e
if grep -Fxq 'STAGED=false' "$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log" 2>/dev/null; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
    --log "$DESIGN_TMPDIR/execution-issues.md" \
    --site "design Step 0b clarify hard halt" \
    --tool "design-stage-terminal-state.sh" \
    --exit-code 0 \
    --category Warnings \
    --output-file "$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log" \
    --redact >/dev/null 2>&1 || true
elif [[ "$stage_rc" -ne 0 ]]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
    --log "$DESIGN_TMPDIR/execution-issues.md" \
    --site "design Step 0b clarify hard halt" \
    --tool "design-stage-terminal-state.sh" \
    --exit-code "$stage_rc" \
    --category Warnings \
    --output-file "$DESIGN_TMPDIR/design-stage-terminal-state.stderr.log" \
    --redact >/dev/null 2>&1 || true
fi
export SUMMARY_OUTCOME=failed-clarify
