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
  if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
  fi
}

design_pause_check() {
  if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  fi
}

design_step4_tail_cleanup() {
  [ -n "${DESIGN_TMPDIR:-}" ] || return 0
  mkdir -p "$DESIGN_TMPDIR/.completed" 2>/dev/null || true
  printf '' >"$DESIGN_TMPDIR/.completed/step-4" 2>/dev/null || true
  rm -f "$DESIGN_TMPDIR/.bg-wait-active" 2>/dev/null || true
}

design_step4_tail_marker() {
  local start claude_pid clone_path
  [ -n "${DESIGN_TMPDIR:-}" ] || return 0
  rm -f "$DESIGN_TMPDIR/no-progress-turns.count" "$DESIGN_TMPDIR/no-progress-circuit-breaker-armed" 2>/dev/null || true
  rm -f "$DESIGN_TMPDIR/.completed/step-4" 2>/dev/null || true
  start=$(date +%s 2>/dev/null) || start=0
  case "$start" in ''|*[!0-9]*) start=0 ;; esac
  claude_pid="${LARCH_BG_POLL_GUARD_SESSION_PID:-${CLAUDE_PID:-${PPID:-}}}"
  clone_path=""
  if [ -f "$DESIGN_TMPDIR/.larch-keepalive" ] && [ ! -L "$DESIGN_TMPDIR/.larch-keepalive" ]; then
    clone_path=$(awk -F= '$1 == "CLONE_PATH" { sub(/^[^=]*=/, ""); print; exit }' "$DESIGN_TMPDIR/.larch-keepalive" 2>/dev/null || true)
  fi
  printf 'PID=%s\nCLAUDE_PID=%s\nSTART_EPOCH=%s\nSTEP=design-step4-tail\nTIMEOUT_S=900\nCLONE_PATH=%s\n' \
    "$$" "$claude_pid" "$start" "$clone_path" >"$DESIGN_TMPDIR/.bg-wait-active" 2>/dev/null || true
}

design_source_env_optional
[ -n "${DESIGN_TMPDIR:-}" ] && rm -f "$DESIGN_TMPDIR/.pause-save-complete"

design_pause_check
trap design_step4_tail_cleanup EXIT
design_step4_tail_marker
LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 4 — rejected findings" || true
if [ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]; then
  set +e
  printf '%s\n' 'ACTION=FINALIZE' \
    | python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design driver --design-tmpdir "$DESIGN_TMPDIR"
  _finalize_rc=$?
  set -e
  if [ "$_finalize_rc" -ne 0 ]; then
    printf '%s\n' '**⚠ FINALIZE failed; repair the missing artifact before Step 5.**'
    exit "$_finalize_rc"
  fi
fi

printf '%s\n' '---LARCH-REJECTED-BEGIN---'
if [ -s "$DESIGN_TMPDIR/rejected-findings.md" ]; then
  # Drop findings already applied in an earlier plan-review round, then frame
  # any remaining operator output as considered-not-adopted suggestions. Fall
  # back to filtered emit-rejected (without --report-framing) on any failure so Step 4
  # still emits something without re-showing already-applied findings.
  # The on-disk file is left unchanged.
  if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review emit-rejected --design-tmpdir "$DESIGN_TMPDIR" --report-framing; then
    printf '%s\n\n' '## Considered Plan Review Suggestions (Not Adopted)'
    printf '%s\n\n' 'These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.'
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review emit-rejected --design-tmpdir "$DESIGN_TMPDIR" || true
  fi
fi
printf '%s\n' '---LARCH-REJECTED-END---'

design_pause_check
LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 4b — gate C" || true
_skip_approve_requested_gatec=false
if command -v jq >/dev/null 2>&1; then
  case "$(jq -r '.skip_approve_requested // false' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null)" in
    true) _skip_approve_requested_gatec=true ;;
  esac
elif command grep -Eq '"skip_approve_requested"[[:space:]]*:[[:space:]]*true([,}[:space:]]|$)' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null; then
  _skip_approve_requested_gatec=true
fi

if [ "$_skip_approve_requested_gatec" = false ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR"
else
  # Skip auto debate launches on --skip-approve. The Python helper prints only a
  # fingerprint-valid cached digest, if one already exists.
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR"
fi
mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/dialectic-gatec-terminal"

python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review preview \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --variant gatec
[ -f "$DESIGN_TMPDIR/.pause-save-complete" ] && exit 0

printf 'SKIP_APPROVE_REQUESTED_GATEC=%s\n' "$_skip_approve_requested_gatec"
mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-4"
