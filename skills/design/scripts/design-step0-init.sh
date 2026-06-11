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
   if [ -f "$DESIGN_TMPDIR/.design-step0-parsed.env" ]; then
     # shellcheck source=/dev/null
     . "$DESIGN_TMPDIR/.design-step0-parsed.env"
   fi
   if [ -f "$DESIGN_TMPDIR/.design-step0-route-state.env" ]; then
     # shellcheck source=/dev/null
     . "$DESIGN_TMPDIR/.design-step0-route-state.env"
   fi
   _init_route=""
   if [[ -f "$DESIGN_TMPDIR/.design-route-result.env" ]]; then
     _init_route=$(grep -m1 '^ROUTE=' "$DESIGN_TMPDIR/.design-route-result.env" | cut -d= -f2- || true)
   fi
   if [[ "${_init_route:-}" == proceed ]]; then
     if [[ -f "$DESIGN_TMPDIR/issue-body.txt" ]]; then
       {
         [[ -n "${ISSUE_TITLE:-}" ]] && printf '# %s\n\n' "$ISSUE_TITLE"
         cat "$DESIGN_TMPDIR/issue-body.txt"
       } >"$DESIGN_TMPDIR/feature-description.txt"
     elif [[ "${POSITIONAL_KIND:-}" == verbal && -n "${POSITIONAL_VALUE:-}" ]]; then
       printf '%s\n' "$POSITIONAL_VALUE" >"$DESIGN_TMPDIR/feature-description.txt"
     fi
   fi
   if [[ "${hard_requested:-false}" == true ]]; then
     design_classification=HARD
   else
     design_classification=SIMPLE
   fi
   _init_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-init-stdout.XXXXXX")" || {
     printf '%s\n' "**⚠ Step 0b: could not allocate design-init-runparams stdout capture; aborting /design**" >&2
     exit 1
   }

   set +e
   "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-init-runparams.sh" \
     --design-tmpdir "$DESIGN_TMPDIR" \
     --issue "$ISSUE_NUMBER" \
     --session-id "$SESSION_ID" \
     --claude-pid "$CLAUDE_PID" \
     --classification "$design_classification" \
     --partition-requested "$partition_requested" \
     --brainstorm-requested "$brainstorm_requested" \
     --approve-requested "$approve_requested" \
     --skip-approve-requested "$skip_approve_requested" \
     ${REPO:+--repo "$REPO"} \
     >"$_init_stdout_file"
   _init_rc=$?
   set -e
   if [[ "${_init_rc:-0}" -eq 2 ]]; then
     rm -f "$_init_stdout_file"
     printf '%s\n' "**⚠ Step 0b: design-init-runparams.sh configuration error (exit 2); aborting /design**" >&2
     exit 1
   fi
   if [[ "${_init_rc:-0}" -ne 0 && "${_init_rc:-0}" -ne 1 ]]; then
     rm -f "$_init_stdout_file"
     printf '%s\n' "**⚠ Step 0b: design-init-runparams.sh failed (exit ${_init_rc}); aborting /design**" >&2
     exit 1
   fi
   _safe_init_env="$(mktemp "${TMPDIR:-/tmp}/larch-init-env.XXXXXX")" || {
     rm -f "$_init_stdout_file"
     printf '%s\n' "**⚠ Step 0b: could not allocate safe init result env; aborting /design**" >&2
     exit 1
   }

   set +e
   "${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh" \
     --input "$DESIGN_TMPDIR/.design-init-runparams-result.env" \
     --fallback-input "$_init_stdout_file" \
     --allow INIT_STATUS \
     --allow RENAMED \
     --allow RUN_PARAMS_PATH \
     --allow DESIGN_CLASSIFICATION \
     --output "$_safe_init_env"
   _rre_rc=$?
   set -e
   rm -f "$_init_stdout_file"

   if [[ "${_rre_rc:-0}" -ne 0 ]]; then
     rm -f "$_safe_init_env"
     printf '%s\n' "**⚠ Step 0b: read-result-env.sh failed for design-init-runparams result (exit ${_rre_rc}); aborting /design**" >&2
     exit 1
   fi

   # shellcheck source=/dev/null
   . "$_safe_init_env"
   rm -f "$_safe_init_env"

   if [[ "${_init_rc:-0}" -eq 0 && ( "${INIT_STATUS:-}" != ok || ! -f "$DESIGN_TMPDIR/run-params.json" ) ]]; then
     printf '%s\n' "**⚠ Step 0b: design-init-runparams.sh exited 0 without INIT_STATUS=ok and run-params.json; aborting /design**" >&2
     exit 1
   fi
   if [[ "${_init_rc:-0}" -eq 1 ]]; then
     printf '%s\n' "**⚠ Step 0b: design-init-runparams.sh failed (INIT_STATUS=${INIT_STATUS:-unknown}); aborting /design**" >&2
     exit 1
   fi
   design_source_env_optional
