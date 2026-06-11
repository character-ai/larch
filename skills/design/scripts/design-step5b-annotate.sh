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
design_source_env_optional
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 5b annotate: DESIGN_TMPDIR required" >&2
  exit 1
fi
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER"
_oos_issue_stdout="$DESIGN_TMPDIR/oos-issue.stdout.txt"
set +e
_oos_ann_out=$("${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/file-design-oos.sh" annotate --design-tmpdir "$DESIGN_TMPDIR" --issue-stdout-file "$_oos_issue_stdout" 2>"$DESIGN_TMPDIR/oos-filing-annotate.stderr.log")
_oos_ann_rc=$?
printf '%s\n' "$_oos_ann_out" > "$DESIGN_TMPDIR/oos-filing-annotate.stdout.txt"
set -e
printf '%s\n' "$_oos_ann_out"
printf 'OOS_ANN_RC=%s\n' "${_oos_ann_rc:-0}"

FILE_DESIGN_OOS_STATUS=""
WARN=""
while IFS= read -r _ann_line || [[ -n "$_ann_line" ]]; do
  case "$_ann_line" in
    FILE_DESIGN_OOS_STATUS=*) FILE_DESIGN_OOS_STATUS="${_ann_line#FILE_DESIGN_OOS_STATUS=}" ;;
    WARN=*) WARN="${_ann_line#WARN=}" ;;
  esac
done <<<"$_oos_ann_out"

if [[ "${_oos_ann_rc:-0}" -ne 0 ]]; then
  _issues_failed=0
  if grep -Eq '^ISSUES_FAILED=[1-9][0-9]*' "$_oos_issue_stdout" 2>/dev/null; then
    _issues_failed=1
  fi
  if [[ -s "$DESIGN_TMPDIR/oos-filing-annotate.stderr.log" ]]; then
    "${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" \
      --log "$DESIGN_TMPDIR/execution-issues.md" \
      --site "design Step 5b" \
      --tool "file-design-oos.sh annotate" \
      --exit-code "${_oos_ann_rc}" \
      --category "Tool Failures" \
      --output-file "$DESIGN_TMPDIR/oos-filing-annotate.stderr.log" \
      --redact || true
  fi
  if [[ "$_issues_failed" -eq 1 ]]; then
    printf '%s\n' "**⚠ /design: OOS filing completed with ISSUES_FAILED>0 — see execution-issues and oos-issue.stdout.txt**"
  fi
elif [[ "${FILE_DESIGN_OOS_STATUS:-}" == annotate-skipped-empty-stdout && -n "${WARN:-}" ]]; then
  "${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" \
    --log "$DESIGN_TMPDIR/execution-issues.md" \
    --site "design Step 5b annotate-skip" \
    --tool "file-design-oos.sh annotate" \
    --exit-code 0 \
    --category Warnings \
    --output-file "$DESIGN_TMPDIR/oos-filing-annotate.stderr.log" \
    --redact || true
  printf '%s\n' "**⚠ /design: annotate skipped (empty issue stdout) — OOS filing status unclear; see execution-issues**"
fi

mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-5b"
printf 'STEP5B_STATUS=annotate-complete\n'
