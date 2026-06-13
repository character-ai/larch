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
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}


design_bg_wait_marker_start() {
  local step="$1"
  _bg_wait_marker="$DESIGN_TMPDIR/.bg-wait-active"
  _bg_wait_tmp="${_bg_wait_marker}.tmp.$$"
  {
    printf 'PID=%s\n' "$$"
    printf 'CLAUDE_PID=%s\n' "${CLAUDE_PID:-}"
    printf 'START_EPOCH=%s\n' "$(date +%s)"
    printf 'STEP=%s\n' "$step"
    printf 'TIMEOUT_S=21600\n'
  } >"$_bg_wait_tmp" || return 1
  mv -f "$_bg_wait_tmp" "$_bg_wait_marker" || { rm -f "$_bg_wait_tmp" 2>/dev/null || true; return 1; }
  trap 'rm -f "${_bg_wait_marker:-}" "${_bg_wait_tmp:-}"' EXIT
  return 0
}
design_require_plugin_root
design_source_env_optional
if [ -z "${DESIGN_TMPDIR:-}" ]; then
  printf '%s\n' "/design Step 5c: DESIGN_TMPDIR required" >&2
  exit 1
fi
if [[ ! -f "$DESIGN_TMPDIR/.completed/step-5b" ]]; then
  printf '%s\n' "**⚠ Step 5c: missing .completed/step-5b — OOS filing incomplete; repair Step 5b before publish**" >&2
  exit 1
fi
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/design-pause-save.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
# Marker step id: STEP=design-step5c
design_bg_wait_marker_start design-step5c || true
emit_report_gate_sidecars_from_disk() {
  local sidecar handoff="$DESIGN_TMPDIR/design-report-gate-sidecars.md"
  : >"$handoff"
  for sidecar in "$DESIGN_TMPDIR/design-failure-chat-print.md" "$DESIGN_TMPDIR/design-failure-operator-action-chat.md"; do
    [ -s "$sidecar" ] || continue
    cat "$sidecar" >>"$handoff"
    printf '\n' >>"$handoff"
  done
  if [ -s "$handoff" ]; then
    printf 'REPORT_GATE_SIDECARS_FILE=%s\n' "$handoff"
  fi
}
   _publish_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-publish-stdout.XXXXXX")" || {
     printf '%s\n' "**⚠ Step 5c: could not allocate design-publish stdout capture; aborting /design**" >&2
     exit 1
   }
   set +e
   "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-publish.sh" \
     --design-tmpdir "$DESIGN_TMPDIR" \
     --issue "$ISSUE_NUMBER" \
     --session-id "$SESSION_ID" \
     --claude-pid "$CLAUDE_PID" \
     ${REPO:+--repo "$REPO"} \
     ${SKIP_VALIDATE:+--skip-validate} \
     >"$_publish_stdout_file"
   _publish_rc=$?
   set -e
   abort_failed_publish_tail() {
     local rc=$1
     [[ -n "${DESIGN_TMPDIR:-}" && -d "$DESIGN_TMPDIR" ]] || return 0
     design_require_plugin_root
     local stage_helper="$CLAUDE_PLUGIN_ROOT/skills/design/scripts/design-stage-terminal-state.sh"
     local design_tmpdir_canon detail_log
     design_tmpdir_canon=$(cd "$DESIGN_TMPDIR" && pwd -P)
     detail_log="$design_tmpdir_canon/design-publish-tail.failure.log"
     [[ -x "$stage_helper" ]] || return 0
     [ -f "$detail_log" ] || printf 'design-publish.sh failed (exit %s)\n' "$rc" >"$detail_log"
     set +e
     "$stage_helper" --design-tmpdir "$design_tmpdir_canon" \
       --outcome failed-publish-tail \
       --step publish \
       --phase publish \
       --site design-publish \
       --trigger publish-tail-failed \
       --bail-reason publish-tail-failed \
       --exit-code "$rc" \
       --source-script design-step5c \
       --summary-outcome failed-publish-tail \
       --failure-detail-log "$detail_log" \
       >"$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log" \
       2>"$DESIGN_TMPDIR/design-stage-terminal-state.stderr.log"
     local stage_rc=$?
     set -e
     if grep -Fxq 'STAGED=false' "$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log" 2>/dev/null; then
       python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
         --log "$DESIGN_TMPDIR/execution-issues.md" \
         --site "design Step 5c publish-tail staging" \
         --tool "design-stage-terminal-state.sh" \
         --exit-code 0 \
         --category Warnings \
         --output-file "$DESIGN_TMPDIR/design-stage-terminal-state.stdout.log" \
         --redact >/dev/null 2>&1 || true
     elif [[ "$stage_rc" -ne 0 ]]; then
       python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
         --log "$DESIGN_TMPDIR/execution-issues.md" \
         --site "design Step 5c publish-tail staging" \
         --tool "design-stage-terminal-state.sh" \
         --exit-code "$stage_rc" \
         --category Warnings \
         --output-file "$DESIGN_TMPDIR/design-stage-terminal-state.stderr.log" \
         --redact >/dev/null 2>&1 || true
     fi
     export SUMMARY_OUTCOME=failed-publish-tail
     "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/render-final-summary.sh" \
       --outcome failed-publish-tail \
       --mode "${MODE:-N/A}" \
       ${REPO:+--repo "$REPO"} \
       --post-publish-only || true
     emit_report_gate_sidecars_from_disk
   }
   if [[ "${_publish_rc:-0}" -eq 2 ]]; then
     rm -f "$_publish_stdout_file"
     abort_failed_publish_tail 2
     printf '%s\n' "**⚠ Step 5c: design-publish.sh configuration error (exit 2); aborting /design**" >&2
     exit 1
   fi
   if [[ "${_publish_rc:-0}" -eq 3 ]]; then
     printf '%s\n' "**⚠ Step 5c: design-publish.sh result-env write failed (exit 3); continuing with stdout parse**" >&2
   fi
   if [[ "${_publish_rc:-0}" -ne 0 && "${_publish_rc:-0}" -ne 1 && "${_publish_rc:-0}" -ne 3 && "${_publish_rc:-0}" -ne 4 ]]; then
     rm -f "$_publish_stdout_file"
     abort_failed_publish_tail "${_publish_rc:-1}"
     printf '%s\n' "**⚠ Step 5c: design-publish.sh failed (exit ${_publish_rc}); aborting /design**" >&2
     exit 1
   fi
   PLAN_WRITE_OK=""
   VALIDATE_STATUS=""
   VALIDATE_DEFECT_COUNT=""
   VALIDATE_SKIPPED_COUNT=""
   VALIDATE_UNSAFE_TOKEN_COUNT=""
   VALIDATE_LOG_FILE=""
   PUBLISH_OK=""
   RENAMED=""
   UPSERT_STATUS=""
   ARCHITECTURE_SOURCE=""
   FINAL_SUMMARY_PATH=""
   PR_NUMBER=""
   PR_URL=""
   RECOVERY_BRANCH=""
   LOG_RECOVERY_BRANCH=""
   _publish_input="$DESIGN_TMPDIR/.design-publish-result.env"
   _publish_input_is_temp=false
   if [[ "${_publish_rc:-0}" -eq 1 || "${_publish_rc:-0}" -eq 3 || "${_publish_rc:-0}" -eq 4 ]]; then
     _publish_input="$DESIGN_TMPDIR/.design-publish-result.env.rc${_publish_rc:-0}-primary-missing.$$"
     _publish_input_is_temp=true
     rm -f "$_publish_input"
   fi
   _safe_publish_env="$(mktemp "${TMPDIR:-/tmp}/larch-publish-env.XXXXXX")" || {
     rm -f "$_publish_stdout_file"
     if [[ "$_publish_input_is_temp" == true ]]; then rm -f "$_publish_input"; fi
     printf '%s\n' "**⚠ Step 5c: could not allocate safe publish result env; aborting /design**" >&2
     exit 1
   }
   set +e
   "${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh" \
     --input "$_publish_input" \
     --fallback-input "$_publish_stdout_file" \
     --allow PLAN_WRITE_OK \
     --allow VALIDATE_STATUS \
     --allow VALIDATE_DEFECT_COUNT \
     --allow VALIDATE_SKIPPED_COUNT \
     --allow VALIDATE_UNSAFE_TOKEN_COUNT \
     --allow VALIDATE_LOG_FILE \
     --allow PUBLISH_OK \
     --allow RENAMED \
     --allow UPSERT_STATUS \
     --allow ARCHITECTURE_SOURCE \
     --allow FINAL_SUMMARY_PATH \
     --allow PR_NUMBER \
     --allow PR_URL \
     --allow RECOVERY_BRANCH \
     --allow LOG_RECOVERY_BRANCH \
     --output "$_safe_publish_env"
   _rre_rc=$?
   set -e
   if [[ "${_rre_rc:-0}" -ne 0 ]]; then
     rm -f "$_publish_stdout_file" "$_safe_publish_env"
     if [[ "$_publish_input_is_temp" == true ]]; then rm -f "$_publish_input"; fi
     printf '%s\n' "**⚠ Step 5c: design-publish result env missing or unreadable; aborting /design**" >&2
     exit 1
   fi
   # shellcheck source=/dev/null
   . "$_safe_publish_env"
   rm -f "$_publish_stdout_file" "$_safe_publish_env"
   if [[ "$_publish_input_is_temp" == true ]]; then rm -f "$_publish_input"; fi
if [[ "${PLAN_WRITE_OK:-}" == true ]]; then
  mkdir -p "$DESIGN_TMPDIR/.completed"
  : > "$DESIGN_TMPDIR/.completed/step-5c"
fi

_cleanup_eligible=false
if [[ "${PLAN_WRITE_OK:-}" == true && "${STANDALONE_HEAVY_FAILED:-false}" != true ]]; then
  if [[ -z "${SESSION_ID:-}" || "${PUBLISH_OK:-}" == true ]]; then
    _cleanup_eligible=true
  fi
fi

cat > "$DESIGN_TMPDIR/.design-step5c-status.env" <<EOF_STATUS
PLAN_WRITE_OK=${PLAN_WRITE_OK:-}
PUBLISH_OK=${PUBLISH_OK:-}
STANDALONE_HEAVY_FAILED=${STANDALONE_HEAVY_FAILED:-}
SESSION_ID=${SESSION_ID:-}
PUBLISH_RC=${_publish_rc:-}
PUBLISH_STDOUT_FALLBACK=${_publish_input_is_temp:-false}
CLEANUP_ELIGIBLE=${_cleanup_eligible}
EOF_STATUS

printf 'PUBLISH_RC=%s\nPLAN_WRITE_OK=%s\nPUBLISH_OK=%s\n' "${_publish_rc:-}" "${PLAN_WRITE_OK:-}" "${PUBLISH_OK:-}"
printf 'VALIDATE_STATUS=%s\nVALIDATE_DEFECT_COUNT=%s\nVALIDATE_SKIPPED_COUNT=%s\n' "${VALIDATE_STATUS:-}" "${VALIDATE_DEFECT_COUNT:-}" "${VALIDATE_SKIPPED_COUNT:-}"
printf 'VALIDATE_UNSAFE_TOKEN_COUNT=%s\nVALIDATE_LOG_FILE=%s\n' "${VALIDATE_UNSAFE_TOKEN_COUNT:-}" "${VALIDATE_LOG_FILE:-}"
printf 'FINAL_SUMMARY_PATH=%s\nUPSERT_STATUS=%s\nARCHITECTURE_SOURCE=%s\n' "${FINAL_SUMMARY_PATH:-}" "${UPSERT_STATUS:-}" "${ARCHITECTURE_SOURCE:-}"
printf 'CLEANUP_ELIGIBLE=%s\n' "${_cleanup_eligible}"

if [[ "${_publish_rc:-0}" -eq 4 ]]; then
  printf 'STEP5C_STATUS=validator-defects\n'
fi

emit_report_gate_sidecars_from_disk
