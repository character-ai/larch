#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
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
      printf '%s\n' 'design-step3b-tail.sh: adapter child controls must be one terminal suffix' >&2
      exit 2
      ;;
  esac
done

DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
REPO="${REPO:-}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-env-path) SESSION_ENV_PATH="$2"; shift 2 ;;
    --claude-pid) CLAUDE_PID="$2"; shift 2 ;;
    --plugin-root) CLAUDE_PLUGIN_ROOT="$2"; shift 2 ;;
    --mode|--site|--outcome|--step3-review-loop-status|--loop-status) shift 2 ;;
    --snapshot-original|--skip-validate) shift ;;
    --) shift; break ;;
    *) printf '%s\n' "$0: unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  _script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
  CLAUDE_PLUGIN_ROOT="$(cd "$_script_dir/../../.." && pwd -P)"
fi
export CLAUDE_PLUGIN_ROOT

if [ -n "${SESSION_ENV_PATH:-}" ]; then
  _resolver_args=(--resolve-session-env --session-env-path "$SESSION_ENV_PATH")
  [ -n "${CLAUDE_PID:-}" ] && _resolver_args[${#_resolver_args[@]}]=--owner-pid && _resolver_args[${#_resolver_args[@]}]="$CLAUDE_PID"
  _resolved_session_env="$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" bgjob adapt "${_resolver_args[@]}")" || {
      printf '%s\n' "${_resolved_session_env:-BGJOB_ERROR=session-env-resolution-failed}"
      exit 2
    }
  eval "$_resolved_session_env"
fi

if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' 'design-step3b-tail.sh: DESIGN_TMPDIR required' >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
export DESIGN_TMPDIR
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2

publish_step4_result() {
  local _status="$1"
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - \
    "$MERGE_RESULT_ENV" "$DESIGN_TMPDIR" "$_status" \
    "${_skip_approve_requested_gatec:-false}" \
    "$DESIGN_TMPDIR/gatec-rejected-findings-framed.md" \
    "$DESIGN_TMPDIR/gatec-preview.md" \
    "$DESIGN_TMPDIR/dialectic-clarifier-digest.md" <<'PY'
from pathlib import Path
import sys
from larch.design.design_core import design_write_merge_env

merge_env, design_tmpdir = Path(sys.argv[1]), Path(sys.argv[2])
status, skip_gatec = sys.argv[3], sys.argv[4]
rejected_path, preview_path, digest_path = map(Path, sys.argv[5:8])
rows = [
    ("STEP4_STATUS", status),
    ("SKIP_APPROVE_REQUESTED_GATEC", skip_gatec),
    ("REJECTED_FINDINGS_BEGIN", "---LARCH-REJECTED-BEGIN---"),
    ("REJECTED_FINDINGS_END", "---LARCH-REJECTED-END---"),
    ("REJECTED_FINDINGS_BODY_PATH", str(rejected_path)),
    ("GATEC_PREVIEW_PATH", str(preview_path)),
]
if digest_path.is_file() and not digest_path.is_symlink():
    rows.append(("DIALECTIC_GATEC_DIGEST_PATH", str(digest_path)))
design_write_merge_env(path=merge_env, design_tmpdir=design_tmpdir, rows=rows)
PY
}

pause_save() {
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save \
    --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
}

if [ "$BGJOB_CHILD" = false ]; then
  [ -n "${DESIGN_TMPDIR:-}" ] && rm -f "$DESIGN_TMPDIR/.pause-save-complete"
  if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save \
      --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE_NUMBER" ${REPO:+--repo "$REPO"}
  fi
  _adapt_args=(
    --step design-step4-tail \
    --tmpdir "$DESIGN_TMPDIR" \
    --budget-s 900
  )
  [ -n "${CLAUDE_PID:-}" ] && _adapt_args[${#_adapt_args[@]}]=--owner-pid && _adapt_args[${#_adapt_args[@]}]="$CLAUDE_PID"
  [ -n "${SESSION_ENV_PATH:-}" ] && _adapt_args[${#_adapt_args[@]}]=--session-env-path && _adapt_args[${#_adapt_args[@]}]="$SESSION_ENV_PATH"
  _step3_sidecar="$DESIGN_TMPDIR/.step3-review-result.env"
  if [ -f "$_step3_sidecar" ] && [ ! -L "$_step3_sidecar" ]; then
    _tail_input_fp="$(shasum -a 256 "$_step3_sidecar" 2>/dev/null | awk '{print $1}')" || _tail_input_fp="compute-failed"
    [ -z "$_tail_input_fp" ] && _tail_input_fp="compute-failed"
  else
    _tail_input_fp="source-absent"
  fi
  _adapt_args[${#_adapt_args[@]}]=--input-fingerprint
  _adapt_args[${#_adapt_args[@]}]="$_tail_input_fp"
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob adapt "${_adapt_args[@]}" -- bash "$0" "${ORIGINAL_ARGS[@]}"
fi

_skip_approve_requested_gatec=false
if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
  pause_save
  publish_step4_result pause-save
  exit 0
fi

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

_rejected_body="$DESIGN_TMPDIR/gatec-rejected-findings-framed.md"
{
  printf '%s\n' '---LARCH-REJECTED-BEGIN---'
  if [ -s "$DESIGN_TMPDIR/rejected-findings.md" ]; then
    if ! python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review emit-rejected --design-tmpdir "$DESIGN_TMPDIR" --report-framing; then
      printf '%s\n\n' '## Considered Plan Review Suggestions (Not Adopted)'
      printf '%s\n\n' 'These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.'
      python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review emit-rejected --design-tmpdir "$DESIGN_TMPDIR" || true
    fi
  fi
  printf '%s\n' '---LARCH-REJECTED-END---'
} >"$_rejected_body"

if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
  pause_save
  publish_step4_result pause-save
  exit 0
fi
LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 4b — gate C" || true
if command -v jq >/dev/null 2>&1; then
  case "$(jq -r '.skip_approve_requested // false' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null)" in
    true) _skip_approve_requested_gatec=true ;;
  esac
elif ( command grep -Eq '"skip_approve_requested"[[:space:]]*:[[:space:]]*true([,}[:space:]]|$)' "$DESIGN_TMPDIR/run-params.json" ) 2>/dev/null; then
  _skip_approve_requested_gatec=true
fi

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR"
mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/dialectic-gatec-terminal"

python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review preview \
  --design-tmpdir "$DESIGN_TMPDIR" \
  --variant gatec >"$DESIGN_TMPDIR/gatec-preview.md"
if [ -f "$DESIGN_TMPDIR/.pause-save-complete" ]; then
  publish_step4_result pause-save
  exit 0
fi

mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-4"
publish_step4_result complete
