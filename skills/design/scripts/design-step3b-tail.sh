#!/usr/bin/env bash
# Generated /design wrapper. Keep in sync with skills/design/SKILL.md.
# shellcheck disable=SC1090,SC1091,SC2016,SC2034,SC2086,SC2154,SC2164,SC2312,SC2317,SC2329
set -euo pipefail

SESSION_ENV_PATH=""
CLAUDE_PID=""
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
RUN_TAIL_CHILD=false
ORIGINAL_ARGS=("$@")

# Prompt-side values may be supplied only as environment variables by Claude Code.
DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
SESSION_TMPDIR="${SESSION_TMPDIR:-}"
SESSION_ID="${SESSION_ID:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
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
    --run-tail-child) RUN_TAIL_CHILD=true; shift ;;
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

design_step4_tail_recreate_merge_env() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DESIGN_TMPDIR/.design-step4-tail-result.env" "$DESIGN_TMPDIR" <<'PY'
from pathlib import Path
import sys
from larch.design.design_core import design_recreate_merge_env

design_recreate_merge_env(path=Path(sys.argv[1]), design_tmpdir=Path(sys.argv[2]))
PY
}

design_step4_tail_write_merge_env() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - \
    "$DESIGN_TMPDIR/.design-step4-tail-result.env" \
    "$DESIGN_TMPDIR" \
    "$_skip_approve_requested_gatec" \
    "$DESIGN_TMPDIR/gatec-rejected-findings-framed.md" \
    "$DESIGN_TMPDIR/gatec-preview.md" \
    "$DESIGN_TMPDIR/dialectic-clarifier-digest.md" <<'PY'
from pathlib import Path
import sys
from larch.design.design_core import design_write_merge_env

merge_env = Path(sys.argv[1])
design_tmpdir = Path(sys.argv[2])
skip_gatec = sys.argv[3]
rejected_path = Path(sys.argv[4])
preview_path = Path(sys.argv[5])
digest_path = Path(sys.argv[6])
rows = [
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

design_step4_tail_bgjob_registry_state() {
  PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/python${PYTHONPATH:+:$PYTHONPATH}" python3 - "$DESIGN_TMPDIR" <<'PY'
from pathlib import Path
import sys
from larch.bgjob import registry

path, entry = registry.read_for(tmpdir=Path(sys.argv[1]), step="design-step4-tail")
if entry is None:
    print("missing")
    raise SystemExit(0)
if registry.child_liveness(entry).live or registry.daemon_liveness(entry).live:
    print("live")
    raise SystemExit(0)
registry.unlink_entry(path)
print("cleared")
PY
}

design_source_env_optional
[ -n "${DESIGN_TMPDIR:-}" ] && rm -f "$DESIGN_TMPDIR/.pause-save-complete"
if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
  printf '%s\n' 'design-step3b-tail.sh: DESIGN_TMPDIR required' >&2
  exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
export DESIGN_TMPDIR
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2

if [ "$RUN_TAIL_CHILD" = false ]; then
  _result_env="$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env"
  if [ -L "$_result_env" ]; then
    printf '%s\n' 'design-step3b-tail.sh: existing bgjob result env must not be a symlink' >&2
    exit 1
  fi
  if [ -e "$_result_env" ] && [ ! -f "$_result_env" ]; then
    printf '%s\n' 'design-step3b-tail.sh: existing bgjob result env must be a regular file' >&2
    exit 1
  fi
  if [ -f "$_result_env" ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait \
      --step design-step4-tail \
      --tmpdir "$DESIGN_TMPDIR" \
      --max-wait-s 0
  fi
  _registry_state="$(design_step4_tail_bgjob_registry_state)" || {
    printf '%s\n' 'BGJOB_ERROR=registry-check-failed'
    exit 2
  }
  if [ "$_registry_state" = live ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob wait \
      --step design-step4-tail \
      --tmpdir "$DESIGN_TMPDIR" \
      --max-wait-s 0
  fi
  mkdir -p "$DESIGN_TMPDIR/.completed" "$DESIGN_TMPDIR/bgjob"
  rm -f "$DESIGN_TMPDIR/.completed/step-4" "$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env" 2>/dev/null || true
  design_step4_tail_recreate_merge_env
  _owner_args=()
  if [ -n "${CLAUDE_PID:-}" ]; then
    _owner_args=(--owner-pid "$CLAUDE_PID")
  fi
  exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step design-step4-tail \
    --tmpdir "$DESIGN_TMPDIR" \
    --budget-s 900 \
    "${_owner_args[@]}" \
    --sentinel "$DESIGN_TMPDIR/.completed/step-4" \
    --merge-result-env "$DESIGN_TMPDIR/.design-step4-tail-result.env" \
    -- bash "$0" --run-tail-child "${ORIGINAL_ARGS[@]}"
fi

design_pause_check
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

design_pause_check
LARCH_TIMING_SKILL=design python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" timing mark "design Step 4b — gate C" || true
_skip_approve_requested_gatec=false
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
[ -f "$DESIGN_TMPDIR/.pause-save-complete" ] && exit 0

mkdir -p "$DESIGN_TMPDIR/.completed"
: > "$DESIGN_TMPDIR/.completed/step-4"
design_step4_tail_write_merge_env
