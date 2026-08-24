#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2206,SC2207
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
MODE=""
SITE=""
SUMMARY_OUTCOME="${SUMMARY_OUTCOME:-}"
SKIP_VALIDATE=""
PUBLIC_ARGV_WORDS=()
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
ORIGINAL_ARGS=("$@")

_arg_count=${#ORIGINAL_ARGS[@]}
if [ "$_arg_count" -ge 3 ] \
  && [ "${ORIGINAL_ARGS[$((_arg_count - 3))]}" = "--bgjob-child" ] \
  && [ "${ORIGINAL_ARGS[$((_arg_count - 2))]}" = "--merge-result-env" ] \
  && [ -n "${ORIGINAL_ARGS[$((_arg_count - 1))]}" ]; then
  BGJOB_CHILD=true
  MERGE_RESULT_ENV="${ORIGINAL_ARGS[$((_arg_count - 1))]}"
  set -- "${ORIGINAL_ARGS[@]:0:$((_arg_count - 3))}"
  ORIGINAL_ARGS=("$@")
fi
for _adapter_control in "$@"; do
  case "$_adapter_control" in
    --bgjob-child|--merge-result-env)
      printf '%s\n' 'design-step3-review.sh: adapter child controls must be one terminal suffix' >&2
      exit 2
      ;;
  esac
done

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
DEGRADED_PANEL_WARNING="${DEGRADED_PANEL_WARNING:-}"
INVALID_SLOT_PANEL_WARNING="${INVALID_SLOT_PANEL_WARNING:-}"
VALIDATE_STATUS="${VALIDATE_STATUS:-}"
VALIDATE_DEFECT_COUNT="${VALIDATE_DEFECT_COUNT:-}"
VALIDATE_UNSAFE_TOKEN_COUNT="${VALIDATE_UNSAFE_TOKEN_COUNT:-}"
VALIDATE_SKIPPED_COUNT="${VALIDATE_SKIPPED_COUNT:-}"
VALIDATE_LOG_FILE="${VALIDATE_LOG_FILE:-}"
_validator_target_file="${_validator_target_file:-}"
PUBLISH_OK="${PUBLISH_OK:-}"
PLAN_WRITE_OK="${PLAN_WRITE_OK:-}"
STANDALONE_HEAVY_FAILED="${STANDALONE_HEAVY_FAILED:-}"
STARTING_ROUND=""
STARTING_ROUND_SEEN=false
RESUME_PHASE=""
RESUME_PHASE_SEEN=false
RESUME_FINDINGS_FILE=""
RESUME_FINDINGS_FILE_SEEN=false
POSTPLAN_OPERATOR_CONTINUE=false
READ_RESULT_ENV=false

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
    --starting-round)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' 'design-step3-review.sh: --starting-round requires a non-empty positive integer' >&2
        exit 2
      fi
      STARTING_ROUND_SEEN=true
      STARTING_ROUND="${2:-}"
      shift 2
      ;;
    --phase)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' 'design-step3-review.sh: --phase requires a value' >&2
        exit 2
      fi
      RESUME_PHASE_SEEN=true
      RESUME_PHASE="${2:-}"
      shift 2
      ;;
    --findings-file)
      if [ "$#" -lt 2 ]; then
        printf '%s\n' 'design-step3-review.sh: --findings-file requires a value' >&2
        exit 2
      fi
      RESUME_FINDINGS_FILE_SEEN=true
      RESUME_FINDINGS_FILE="${2:-}"
      shift 2
      ;;
    --postplan-operator-continue) POSTPLAN_OPERATOR_CONTINUE=true; shift ;;
    --step3-review-loop-status) STEP3_REVIEW_LOOP_STATUS="$2"; shift 2 ;;
    --loop-status) LOOP_STATUS="$2"; shift 2 ;;
    --read-result-env) READ_RESULT_ENV=true; shift ;;
    --) shift; PUBLIC_ARGV_WORDS=("$@"); break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ "$STARTING_ROUND_SEEN" = true ]; then
  case "$STARTING_ROUND" in
    ''|*[!0-9]*)
      printf '%s\n' 'design-step3-review.sh: --starting-round requires a non-empty positive integer' >&2
      exit 2
      ;;
  esac
  if [ "$((10#$STARTING_ROUND))" -le 0 ]; then
    printf '%s\n' 'design-step3-review.sh: --starting-round requires a non-empty positive integer' >&2
    exit 2
  fi
fi

if [ "$RESUME_PHASE_SEEN" = true ] && [ -z "$RESUME_PHASE" ]; then
  printf '%s\n' 'design-step3-review.sh: --phase requires a value' >&2
  exit 2
fi

if [ "$RESUME_FINDINGS_FILE_SEEN" = true ] && [ -z "$RESUME_FINDINGS_FILE" ]; then
  printf '%s\n' 'design-step3-review.sh: --findings-file requires a value' >&2
  exit 2
fi

design_require_plugin_root() {
  _cpr_literal='${CLAUDE_PLUGIN_ROOT}'
  _cpr_cli_root="${CLAUDE_PLUGIN_ROOT:-}"
  case "${_cpr_cli_root}" in
    ""|"$_cpr_literal")
      _cpr_cli_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
      CLAUDE_PLUGIN_ROOT="$_cpr_cli_root"
      ;;
  esac
  export CLAUDE_PLUGIN_ROOT
  CLAUDE_PLUGIN_ROOT="$_cpr_cli_root" "${_cpr_cli_root}/scripts/larch.sh" session require-plugin-root || exit $?
}

design_require_plugin_root
if [ -n "${SESSION_ENV_PATH:-}" ]; then
  _resolver_args=(--resolve-session-env --session-env-path "$SESSION_ENV_PATH")
  [ -n "${CLAUDE_PID:-}" ] && _resolver_args[${#_resolver_args[@]}]=--owner-pid && _resolver_args[${#_resolver_args[@]}]="$CLAUDE_PID"
  _resolved_session_env="$("${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" bgjob adapt "${_resolver_args[@]}")" || {
      printf '%s\n' "${_resolved_session_env:-BGJOB_ERROR=session-env-resolution-failed}"
      exit 2
    }
  eval "$_resolved_session_env"
fi
larch_err() { printf '%s\n' "$*" >&2; }

STEP3_REVIEW_HAS_RESUME_STATE=false
if [ "$RESUME_PHASE_SEEN" = true ] || [ "$RESUME_FINDINGS_FILE_SEEN" = true ] || [ "${POSTPLAN_OPERATOR_CONTINUE:-false}" = true ]; then
  STEP3_REVIEW_HAS_RESUME_STATE=true
fi

step3_review_usage_error() {
  printf '%s\n' "design-step3-review.sh: $*" >&2
  exit 2
}

step3_review_read_round_count() {
  local _count_file="$DESIGN_TMPDIR/review-round-count.txt" _raw=""
  if [ -s "$_count_file" ]; then
    _raw="$(tr -d '[:space:]' <"$_count_file" 2>/dev/null || true)"
    case "$_raw" in
      ''|*[!0-9]*) printf '0\n' ;;
      *) printf '%s\n' "$((10#$_raw))" ;;
    esac
  else
    printf '0\n'
  fi
}

step3_review_canonical_file() {
  local _path="$1" _dir _base
  _dir="$(dirname "$_path")"
  _base="$(basename "$_path")"
  (cd "$_dir" 2>/dev/null && printf '%s/%s\n' "$(pwd -P)" "$_base") || return 1
}

step3_review_validate_resume_state() {
  local _last_count _start_dec _canon_findings
  [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ] || return 0
  [ "$STARTING_ROUND_SEEN" = true ] || step3_review_usage_error 'resume-state flags require --starting-round'
  case "${RESUME_PHASE:-}" in
    ''|awaiting-apply|awaiting-revise|awaiting-post-apply|awaiting-postplan-operator|awaiting-continuation) ;;
    awaiting-vote) step3_review_usage_error '--phase awaiting-vote is internal and cannot be used as a resume phase' ;;
    *) step3_review_usage_error "invalid --phase: ${RESUME_PHASE}" ;;
  esac
  _last_count="$(step3_review_read_round_count)"
  _start_dec=$((10#$STARTING_ROUND))
  if [ "$_start_dec" -gt "$((_last_count + 1))" ]; then
    step3_review_usage_error "--starting-round cannot exceed last consumed review round + 1 (got: $STARTING_ROUND, last consumed: $_last_count)"
  fi
  if [ -n "${RESUME_FINDINGS_FILE:-}" ]; then
    case "$RESUME_FINDINGS_FILE" in
      /*) ;;
      *) step3_review_usage_error '--findings-file must be an absolute path' ;;
    esac
    case "$RESUME_FINDINGS_FILE" in
      *$'\n'*|*$'\r'*) step3_review_usage_error '--findings-file must not contain newline or carriage return' ;;
    esac
    [ ! -L "$RESUME_FINDINGS_FILE" ] || step3_review_usage_error '--findings-file must not be a symlink'
    [ -f "$RESUME_FINDINGS_FILE" ] || step3_review_usage_error '--findings-file must be a regular file'
    [ -r "$RESUME_FINDINGS_FILE" ] || step3_review_usage_error '--findings-file must be readable'
    _canon_findings="$(step3_review_canonical_file "$RESUME_FINDINGS_FILE")" || step3_review_usage_error '--findings-file parent cannot be resolved'
    case "$_canon_findings" in
      "$DESIGN_TMPDIR"/*) RESUME_FINDINGS_FILE="$_canon_findings" ;;
      *) step3_review_usage_error '--findings-file must resolve under DESIGN_TMPDIR' ;;
    esac
  fi
}

step3_review_write_resume_state() {
  local _phase_file _phase_tmp _approval_env _approval_tmp _continue_file _continue_tmp
  [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ] || return 0
  if [ -n "${RESUME_PHASE:-}" ]; then
    _phase_file="$DESIGN_TMPDIR/.step3-round-${STARTING_ROUND}.phase"
    _phase_tmp="${_phase_file}.tmp.$$"
    printf '%s\n' "$RESUME_PHASE" >"$_phase_tmp"
    mv "$_phase_tmp" "$_phase_file"
  fi
  if [ -n "${RESUME_FINDINGS_FILE:-}" ]; then
    _approval_env="$DESIGN_TMPDIR/.gate-b-per-round-approval-round-${STARTING_ROUND}.env"
    _approval_tmp="${_approval_env}.tmp.$$"
    printf 'FINDINGS_FILE=%s\n' "$RESUME_FINDINGS_FILE" >"$_approval_tmp"
    mv "$_approval_tmp" "$_approval_env"
  fi
  if [ "${POSTPLAN_OPERATOR_CONTINUE:-false}" = true ]; then
    _continue_file="$DESIGN_TMPDIR/.postplan-operator-continue-${STARTING_ROUND}"
    _continue_tmp="${_continue_file}.tmp.$$"
    : >"$_continue_tmp"
    mv "$_continue_tmp" "$_continue_file"
  fi
}

step3_review_prelaunch_failure() {
  local _reason="${1:-scope-anchor-missing}"
  "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" plan-review prelaunch-failure \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --reason "$_reason"
}

step3_review_publish_merge() {
  "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" bgjob write-merge-result-env \
    --path "$MERGE_RESULT_ENV" \
    --tmpdir "$DESIGN_TMPDIR" \
    --source "$DESIGN_TMPDIR/.step3-review-result.env" \
    --require-key NEXT_ACTION \
    --require-any-key STEP3_REVIEW_LOOP_STATUS \
    --require-any-key LOOP_STATUS
}

step3_review_write_pause_result() {
  "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" bgjob write-merge-result-env \
    --path "$DESIGN_TMPDIR/.step3-review-result.env" \
    --tmpdir "$DESIGN_TMPDIR" \
    --row NEXT_ACTION=pause-save \
    --row STEP3_REVIEW_LOOP_STATUS=pause-save \
    --row LOOP_STATUS=pause-save \
    --row PAUSE_OK=true
}

if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' "/design wrapper: DESIGN_TMPDIR required" >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2

if [ "$READ_RESULT_ENV" = true ]; then
  exec "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" plan-review normalize-status --design-tmpdir "$DESIGN_TMPDIR" --read-result-env
fi

step3_review_validate_resume_state
if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ]; then
  step3_review_write_resume_state
fi
if [ "$BGJOB_CHILD" = false ]; then
  [ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec "$CLAUDE_PLUGIN_ROOT/scripts/larch.sh" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  _adapt_args=(
    --step design-step3-review \
    --tmpdir "$DESIGN_TMPDIR" \
    --budget-s 21600
  )
  [ -n "${CLAUDE_PID:-}" ] && _adapt_args[${#_adapt_args[@]}]=--owner-pid && _adapt_args[${#_adapt_args[@]}]="$CLAUDE_PID"
  [ -n "${SESSION_ENV_PATH:-}" ] && _adapt_args[${#_adapt_args[@]}]=--session-env-path && _adapt_args[${#_adapt_args[@]}]="$SESSION_ENV_PATH"
  [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ] && _adapt_args[${#_adapt_args[@]}]=--replace-completed-result
  _adapt_args[${#_adapt_args[@]}]=--clear-on-fresh
  _adapt_args[${#_adapt_args[@]}]="$DESIGN_TMPDIR/.completed/step-3"
  _plan_file="$DESIGN_TMPDIR/plan.txt"
  if [ -f "$_plan_file" ] && [ ! -L "$_plan_file" ]; then
    _step3_input_fp="$(shasum -a 256 "$_plan_file" 2>/dev/null | awk '{print $1}')" || _step3_input_fp="compute-failed"
    [ -z "$_step3_input_fp" ] && _step3_input_fp="compute-failed"
  else
    _step3_input_fp="source-absent"
  fi
  _adapt_args[${#_adapt_args[@]}]=--input-fingerprint
  _adapt_args[${#_adapt_args[@]}]="$_step3_input_fp"
  exec "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" bgjob adapt "${_adapt_args[@]}" -- bash "$0" "${ORIGINAL_ARGS[@]}"
fi

STEP3_PRIOR_SIDECAR=""
if [ -e "$DESIGN_TMPDIR/.step3-review-result.env" ] || [ -L "$DESIGN_TMPDIR/.step3-review-result.env" ]; then
  [ -f "$DESIGN_TMPDIR/.step3-review-result.env" ] && [ ! -L "$DESIGN_TMPDIR/.step3-review-result.env" ] || exit 1
  STEP3_PRIOR_SIDECAR="$DESIGN_TMPDIR/.step3-review-result.env.prior.$$"
  mv "$DESIGN_TMPDIR/.step3-review-result.env" "$STEP3_PRIOR_SIDECAR"
fi

if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
  "$CLAUDE_PLUGIN_ROOT/scripts/larch.sh" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  step3_review_write_pause_result
  step3_review_publish_merge
  [ -z "$STEP3_PRIOR_SIDECAR" ] || rm -f "$STEP3_PRIOR_SIDECAR"
  exit 0
fi

if ! "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" scope-anchor validate \
  --mode design \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --path "$DESIGN_TMPDIR/plan-review-scope-anchor.txt" >/dev/null; then
  larch_err "**⚠ Step 3: plan-review-scope-anchor.txt is missing, empty, invalid, or outside DESIGN_TMPDIR; treating plan review as panel-init-failed before launch**"
  step3_review_prelaunch_failure scope-anchor-missing
  step3_review_publish_merge
  [ -z "$STEP3_PRIOR_SIDECAR" ] || rm -f "$STEP3_PRIOR_SIDECAR"
  exit 0
fi

_plan_review_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-stdout.XXXXXX")" || {
  printf '%s\n' "**⚠ Step 3: could not allocate plan-review stdout capture; aborting plan review**" >&2
  exit 1
}

set +e
if [ -n "$STARTING_ROUND" ]; then
  "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --starting-round "$STARTING_ROUND" \
    --new-process-group \
    --orphan-timeout-s 7200 \
    >"$_plan_review_stdout_file" 2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log"
else
  "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --new-process-group \
    --orphan-timeout-s 7200 \
    >"$_plan_review_stdout_file" 2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log"
fi
_plan_review_rc=$?
set -e
_step3_normalize_rc=0
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" plan-review normalize-status \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --stdout-file "$_plan_review_stdout_file" \
  --loop-rc "$_plan_review_rc" || _step3_normalize_rc=$?
rm -f "$_plan_review_stdout_file"
step3_review_publish_merge || exit 1
[ -z "$STEP3_PRIOR_SIDECAR" ] || rm -f "$STEP3_PRIOR_SIDECAR"
exit 0
