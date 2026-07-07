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
RUN_LOOP_CHILD=false

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
    --run-loop-child) RUN_LOOP_CHILD=true; shift ;;
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
design_require_plugin_root
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

step3_review_recreate_merge_env() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DESIGN_TMPDIR/.step3-review-result.env" "$DESIGN_TMPDIR" <<'PY'
from pathlib import Path
import sys

from larch.design.design_terminal import phase_driver_recreate_result_env

phase_driver_recreate_result_env(path=Path(sys.argv[1]), design_tmpdir=Path(sys.argv[2]))
PY
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

step3_review_bgjob_registry_state() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DESIGN_TMPDIR" <<'PY'
from pathlib import Path
import sys
from larch.bgjob import registry

path, entry = registry.read_for(tmpdir=Path(sys.argv[1]), step="design-step3-review")
if entry is None:
    print("missing")
    raise SystemExit(0)
if registry.daemon_liveness(entry).live:
    print("live")
    raise SystemExit(0)
registry.unlink_entry(path)
print("cleared")
PY
}

step3_review_prelaunch_failure() {
  local _reason="${1:-scope-anchor-missing}"
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review prelaunch-failure \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --reason "$_reason"
}

step3_review_child_args() {
  printf '%s\0' bash "$0" --run-loop-child --plugin-root "$CLAUDE_PLUGIN_ROOT"
  if [ -n "${SESSION_ENV_PATH:-}" ]; then
    printf '%s\0' --session-env-path "$SESSION_ENV_PATH"
  fi
  if [ -n "${CLAUDE_PID:-}" ]; then
    printf '%s\0' --claude-pid "$CLAUDE_PID"
  fi
  if [ "$STARTING_ROUND_SEEN" = true ]; then
    printf '%s\0' --starting-round "$STARTING_ROUND"
  fi
  if [ "$RESUME_PHASE_SEEN" = true ]; then
    printf '%s\0' --phase "$RESUME_PHASE"
  fi
  if [ "$RESUME_FINDINGS_FILE_SEEN" = true ]; then
    printf '%s\0' --findings-file "$RESUME_FINDINGS_FILE"
  fi
  if [ "${POSTPLAN_OPERATOR_CONTINUE:-false}" = true ]; then
    printf '%s\0' --postplan-operator-continue
  fi
}

if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' "/design wrapper: DESIGN_TMPDIR required" >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2

if [ "$READ_RESULT_ENV" = true ]; then
  exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status --design-tmpdir "$DESIGN_TMPDIR" --read-result-env
fi

step3_review_validate_resume_state
if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = true ]; then
  step3_review_write_resume_state
fi
[ -f "$DESIGN_TMPDIR/.pause-requested" ] && exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}

if [ "$RUN_LOOP_CHILD" = false ]; then
  _result_env="$DESIGN_TMPDIR/bgjob/design-step3-review.result.env"
  if [ -L "$_result_env" ]; then
    printf '%s\n' 'design-step3-review.sh: existing bgjob result env must not be a symlink' >&2
    exit 1
  fi
  if [ -e "$_result_env" ] && [ ! -f "$_result_env" ]; then
    printf '%s\n' 'design-step3-review.sh: existing bgjob result env must be a regular file' >&2
    exit 1
  fi
  if [ -f "$_result_env" ]; then
    exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait \
      --step design-step3-review \
      --tmpdir "$DESIGN_TMPDIR" \
      --max-wait-s 0
  fi
  _registry_state="$(step3_review_bgjob_registry_state)" || {
    printf '%s\n' 'BGJOB_ERROR=registry-check-failed'
    exit 2
  }
  if [ "$_registry_state" = live ]; then
    exec python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob wait \
      --step design-step3-review \
      --tmpdir "$DESIGN_TMPDIR" \
      --max-wait-s 0
  fi
  if [ "$STEP3_REVIEW_HAS_RESUME_STATE" = false ]; then
    rm -f "$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
  else
    rm -f "$DESIGN_TMPDIR/.completed/step-3" 2>/dev/null || true
  fi
  mkdir -p "$DESIGN_TMPDIR/.completed" "$DESIGN_TMPDIR/bgjob"
  rm -f "$DESIGN_TMPDIR/.completed/step-3-terminal" "$DESIGN_TMPDIR/.step3-terminal-persisted-this-run" 2>/dev/null || true
  rm -f "$DESIGN_TMPDIR/bgjob/design-step3-review.result.env" 2>/dev/null || true
  step3_review_recreate_merge_env

  _owner_args=()
  if [ -n "${CLAUDE_PID:-}" ]; then
    _owner_args=(--owner-pid "$CLAUDE_PID")
  fi
  _child_argv_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-child-argv.XXXXXX")" || {
    printf '%s\n' 'BGJOB_ERROR=child-argv-tempfile-failed'
    exit 2
  }
  step3_review_child_args >"$_child_argv_file"
  # Bash 3.2 has no readarray; use xargs -0 to preserve the validated argv cells.
  exec xargs -0 python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob start \
    --step design-step3-review \
    --tmpdir "$DESIGN_TMPDIR" \
    --budget-s 21600 \
    "${_owner_args[@]}" \
    --sentinel "$DESIGN_TMPDIR/.completed/step-3-terminal" \
    --merge-result-env "$DESIGN_TMPDIR/.step3-review-result.env" \
    -- <"$_child_argv_file"
fi

if ! python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" scope-anchor validate \
  --mode design \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --path "$DESIGN_TMPDIR/plan-review-scope-anchor.txt" >/dev/null; then
  larch_err "**⚠ Step 3: plan-review-scope-anchor.txt is missing, empty, invalid, or outside DESIGN_TMPDIR; treating plan review as panel-init-failed before launch**"
  step3_review_prelaunch_failure scope-anchor-missing
  printf '%s\n' 'SUMMARY_OUTCOME=failed-judge-panel'
  exit 1
fi

_plan_review_stdout_file="$(mktemp "${TMPDIR:-/tmp}/larch-step3-review-stdout.XXXXXX")" || {
  printf '%s\n' "**⚠ Step 3: could not allocate plan-review stdout capture; aborting plan review**" >&2
  exit 1
}

set +e
if [ -n "$STARTING_ROUND" ]; then
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --starting-round "$STARTING_ROUND" \
    --new-process-group \
    --orphan-timeout-s 7200 \
    >"$_plan_review_stdout_file" 2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log"
else
  python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review run \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --mode loop \
    --new-process-group \
    --orphan-timeout-s 7200 \
    >"$_plan_review_stdout_file" 2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log"
fi
_plan_review_rc=$?
set -e
_step3_normalize_rc=0
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review normalize-status \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --stdout-file "$_plan_review_stdout_file" \
  --loop-rc "$_plan_review_rc" || _step3_normalize_rc=$?
rm -f "$_plan_review_stdout_file"
exit "$_step3_normalize_rc"
