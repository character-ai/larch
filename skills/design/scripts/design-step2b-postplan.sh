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

design_source_env_optional
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
_postplan_site="${SITE:-step2b}"
_postplan_args=(--design-tmpdir "$DESIGN_TMPDIR" --with-plan-size)
case "$_postplan_site" in
  step2b|"") _postplan_args+=(--snapshot-original) ;;
esac
set +e
_postplan_out=$(env LARCH_QUIET_DISABLE=1 "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-postplan-emit.sh" \
  "${_postplan_args[@]}")
_postplan_rc=$?
set -e
printf '%s\n' "${_postplan_out:-}"
case "${_postplan_rc:-1}" in
  0)
    if [[ "$_postplan_site" == step2b || -z "$_postplan_site" ]]; then
      mkdir -p "$DESIGN_TMPDIR/.completed"
      : > "$DESIGN_TMPDIR/.completed/step-2b"
      : > "$DESIGN_TMPDIR/.completed/step-2b.5"
    fi
    ;;
  10)
    printf 'POSTPLAN_RC=%s\n' "${_postplan_rc}"
    VALIDATE_STATUS=""
    VALIDATE_DEFECT_COUNT=""
    VALIDATE_SKIPPED_COUNT=""
    VALIDATE_UNSAFE_TOKEN_COUNT=""
    VALIDATE_LOG_FILE=""
    if [[ -f "$DESIGN_TMPDIR/.design-postplan-emit-result.env" && ! -L "$DESIGN_TMPDIR/.design-postplan-emit-result.env" ]]; then
      while IFS= read -r _postplan_line || [[ -n "$_postplan_line" ]]; do
        _postplan_key="${_postplan_line%%=*}"
        _postplan_value="${_postplan_line#*=}"
        case "$_postplan_key" in
          VALIDATE_STATUS|VALIDATE_DEFECT_COUNT|VALIDATE_SKIPPED_COUNT|VALIDATE_UNSAFE_TOKEN_COUNT|VALIDATE_LOG_FILE)
            printf -v "$_postplan_key" '%s' "$_postplan_value"
            ;;
        esac
      done <"$DESIGN_TMPDIR/.design-postplan-emit-result.env"
    fi
    _step2b_plan_source=""
    if [[ -f "$DESIGN_TMPDIR/.step2b-plan-source" ]]; then
      _step2b_plan_source=$(tr -d '[:space:]' < "$DESIGN_TMPDIR/.step2b-plan-source")
    fi
    _drafter_postplan_fallback_used=false
    if [[ -f "$DESIGN_TMPDIR/.step2b-postplan-fallback-used" ]]; then
      read -r _drafter_postplan_fallback_used < "$DESIGN_TMPDIR/.step2b-postplan-fallback-used" || _drafter_postplan_fallback_used=false
    fi
    _postplan_dirty_recovery=false
    if [[ -f "$DESIGN_TMPDIR/dirty-tree-detected.env" ]]; then
      while IFS= read -r _dirty_env_line || [[ -n "$_dirty_env_line" ]]; do
        case "$_dirty_env_line" in
          RECOVERY_REQUIRED=true) _postplan_dirty_recovery=true ;;
        esac
      done < "$DESIGN_TMPDIR/dirty-tree-detected.env"
    fi
    if [[ "$_step2b_plan_source" == "drafter" && "$_drafter_postplan_fallback_used" != "true" && "$_postplan_dirty_recovery" != "true" ]]; then
      : > "$DESIGN_TMPDIR/.step2b-postplan-inline-retry-done"
      printf 'true\n' > "$DESIGN_TMPDIR/.step2b-postplan-fallback-used"
      printf 'inline\n' > "$DESIGN_TMPDIR/.step2b-plan-source"
      rm -f "$DESIGN_TMPDIR/plan-summary.md"
      : > "$DESIGN_TMPDIR/.step2b-postplan-inline-retry-pending"
      printf '%s\n' "**⚠ 2b: drafter plan failed postplan validation — re-entering inline drafting once**"
    fi
    ;;
  11)
    exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
    ;;
  12)
    printf 'POSTPLAN_RC=%s\n' "${_postplan_rc}"
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-2b"
    ;;
  13)
    printf 'POSTPLAN_RC=%s\n' "${_postplan_rc}"
    mkdir -p "$DESIGN_TMPDIR/.completed"
    : > "$DESIGN_TMPDIR/.completed/step-2b"
    ;;
  2)
    printf '%s\n' "**⚠ Step 2b: design-postplan-emit.sh configuration error (exit 2); aborting /design.**" >&2
    exit 1
    ;;
  1)
    printf '%s\n' "**⚠ Step 2b: design-postplan-emit.sh failed (exit 1); aborting /design.**" >&2
    exit 1
    ;;
  *)
    printf '%s\n' "**⚠ Step 2b: design-postplan-emit.sh unexpected exit (${_postplan_rc}); aborting /design.**" >&2
    exit 1
    ;;
esac
