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
   if [ -f "$DESIGN_TMPDIR/.design-step0-parsed.env" ]; then
     # shellcheck source=/dev/null
     . "$DESIGN_TMPDIR/.design-step0-parsed.env"
   fi
   case "${POSITIONAL_KIND:-}" in
     issue)
       if [[ "${POSITIONAL_VALUE:-}" =~ ^[0-9]+$ ]]; then
         ISSUE_NUMBER="${POSITIONAL_VALUE}"
       else
         printf '%s\n' "**⚠ Step 0b: POSITIONAL_KIND=issue requires numeric POSITIONAL_VALUE; aborting /design**" >&2
         exit 1
       fi
       ;;
     verbal)
       if [[ -z "${ISSUE_NUMBER:-}" ]]; then
         printf '%s\n' "**⚠ Step 0b: POSITIONAL_KIND=verbal requires ISSUE_NUMBER from /larch:issue before routing; aborting /design**" >&2
         exit 1
       fi
       ;;
     none) ;;
     *)
       printf '%s\n' "**⚠ Step 0b: invalid POSITIONAL_KIND=${POSITIONAL_KIND:-<empty>}; aborting /design**" >&2
       exit 1
       ;;
   esac
   if [[ -n "${ISSUE_NUMBER:-}" ]]; then
     if [ -z "${REPO:-}" ]; then
       if _resolved_repo=$("${CLAUDE_PLUGIN_ROOT}/scripts/resolve-repo.sh" 2>/dev/null); then
         REPO="$_resolved_repo"
       elif _resolved_repo=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null); then
         REPO="$_resolved_repo"
       fi
     fi
     _issue_fetch_rc=1
     for _issue_fetch_try in 1 2; do
       set +e
       if [ -n "${REPO:-}" ]; then
         _issue_json=$(gh issue view "$ISSUE_NUMBER" --repo "$REPO" --json body,labels,number,title 2>/dev/null)
       else
         _issue_json=$(gh issue view "$ISSUE_NUMBER" --json body,labels,number,title 2>/dev/null)
       fi
       _issue_fetch_rc=$?
       set -e
       [ "$_issue_fetch_rc" -eq 0 ] && break
       [ "$_issue_fetch_try" -lt 2 ] && sleep 1
     done
     if [ "$_issue_fetch_rc" -ne 0 ]; then
       printf '%s\n' "**⚠ Step 0b: gh issue view failed for issue ${ISSUE_NUMBER}; aborting /design**" >&2
       exit 1
     fi
     ISSUE_TITLE=$(printf '%s' "$_issue_json" | jq -r '.title // empty')
     printf '%s' "$_issue_json" | jq -r '.body // ""' >"$DESIGN_TMPDIR/issue-body.txt"
     if printf '%s' "$_issue_json" | jq -e '.labels[]? | select(.name == "needs-design-clarification")' >/dev/null 2>&1; then
       HAS_CLARIFY_LABEL=true
     else
       HAS_CLARIFY_LABEL=false
     fi
   fi
   _route_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-route-stdout.XXXXXX")" || {
     printf '%s\n' "**⚠ Step 0b: could not allocate design-route stdout capture; aborting /design**" >&2
     exit 1
   }
   set +e
   "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-route.sh" \
     --design-tmpdir "$DESIGN_TMPDIR" \
     --issue "$ISSUE_NUMBER" \
     --issue-title "$ISSUE_TITLE" \
     --issue-body-file "$DESIGN_TMPDIR/issue-body.txt" \
     --has-clarify-label "$HAS_CLARIFY_LABEL" \
     --claude-pid "$CLAUDE_PID" \
     --session-id "$SESSION_ID" \
     --partition-requested "$partition_requested" \
     --brainstorm-requested "$brainstorm_requested" \
     --approve-requested "$approve_requested" \
     --skip-approve-requested "$skip_approve_requested" \
     ${REPO:+--repo "$REPO"} \
     >"$_route_stdout_file"
   _route_rc=$?
   set -e
   if [[ "${_route_rc:-0}" -eq 2 ]]; then
     rm -f "$_route_stdout_file"
     printf '%s\n' "**⚠ Step 0b: design-route.sh configuration error (exit 2); aborting /design**" >&2
     exit 1
   fi
   if [[ "${_route_rc:-0}" -ne 0 ]]; then
     rm -f "$_route_stdout_file"
     printf '%s\n' "**⚠ Step 0b: design-route.sh failed (exit ${_route_rc}); aborting /design**" >&2
     exit 1
   fi
   ROUTE=""
   BRAINSTORM_PREFIX=false
   TITLE_FILTER_REASON=""
   TITLE_FILTER_MARKER=""
   MARKER_AGE=0
   MARKER_TTL=300
   DESIGN_REENTRY_MARKER_PATH=""
   RESUME_STEP=""
   _safe_route_env="$(mktemp "${TMPDIR:-/tmp}/larch-route-env.XXXXXX")" || {
     rm -f "$_route_stdout_file"
     printf '%s\n' "**⚠ Step 0b: could not allocate safe route result env; aborting /design**" >&2
     exit 1
   }
   set +e
   "${CLAUDE_PLUGIN_ROOT}/scripts/read-result-env.sh" \
     --input "$DESIGN_TMPDIR/.design-route-result.env" \
     --fallback-input "$_route_stdout_file" \
     --allow ROUTE \
     --allow BRAINSTORM_PREFIX \
     --allow TITLE_FILTER_REASON \
     --allow TITLE_FILTER_MARKER \
     --allow MARKER_AGE \
     --allow MARKER_TTL \
     --allow DESIGN_REENTRY_MARKER_PATH \
     --allow RESUME_STEP \
     --allow SESSION_ID \
     --allow RUN_ID \
     --allow TIER \
     --allow BRAINSTORM_DONE \
     --allow MARKER_CLEARED \
     --output "$_safe_route_env"
   _rre_rc=$?
   set -e
   if [[ "${_rre_rc:-0}" -ne 0 ]]; then
     rm -f "$_route_stdout_file" "$_safe_route_env"
     printf '%s\n' "**⚠ Step 0b: could not read design-route result env; aborting /design**" >&2
     exit 1
   fi
   # shellcheck source=/dev/null
   . "$_safe_route_env"
   rm -f "$_route_stdout_file" "$_safe_route_env"
   if [[ "$BRAINSTORM_PREFIX" == true ]]; then
     brainstorm_requested=true
     printf '%s\n' "**ℹ /design: detected Brainstorm title prefix — auto-enabling brainstorm mode (run-params \`brainstorm_requested=true\`) even though --brainstorm was not on argv.**"
   fi
   case "${ROUTE:-}" in
     cancel-pause-load)
       printf '%s\n' "**⚠ /design: pause resume state could not be loaded safely; aborting before fresh routing. Inspect pause-load ERROR breadcrumbs above, fix the pause block, then re-invoke /design.**" >&2
       exit 1 ;;
     cancel-title-filter)
       # Side effects and stderr live in design-route.sh; post-fence handles final-summary emit/abort.
       ;;
     cancel-reentry-guard)
       # Side effects and stderr live in design-route.sh; post-fence handles final-summary emit/abort.
       ;;
     resume@*)
       RESUME_STEP="${ROUTE#resume@}"
       [[ -z "${MARKER_CLEARED:-}" ]] || printf '%s\n' "MARKER_CLEARED=${MARKER_CLEARED}"
       printf '%s\n' "🔓 resumed from STEP=${RESUME_STEP}" ;;
   esac
   _route_valid=false
   case "${ROUTE:-}" in
     proceed|clarify|already-planned|cancel-title-filter|cancel-reentry-guard|cancel-pause-load) _route_valid=true ;;
     resume@*) [[ -n "${ROUTE#resume@}" ]] && _route_valid=true ;;
   esac
   if [[ "$_route_valid" != true ]]; then
     printf '%s\n' "**⚠ Step 0b: missing or invalid ROUTE after design-route.sh; aborting /design**" >&2
     exit 1
   fi
