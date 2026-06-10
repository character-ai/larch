#!/usr/bin/env bash
# step-5-resume.sh — record main-agent review handoff timing, optionally commit, then resume review loop.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
FINAL_ROUND_NUM=""
READY=false
RECORD_ONLY=false
while [ $# -gt 0 ]; do
    case "$1" in
        --final-round-num) [ $# -ge 2 ] || exit 2; FINAL_ROUND_NUM=$2; shift 2 ;;
        --ready-to-commit) READY=true; shift ;;
        --record-only) RECORD_ONLY=true; shift ;;
        --help) printf '%s
' 'Usage: step-5-resume.sh --final-round-num N [--ready-to-commit|--record-only]'; exit 0 ;;
        *) printf '%s
' "step-5-resume.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -n "$FINAL_ROUND_NUM" ] || { printf '%s
' 'step-5-resume.sh: --final-round-num is required' >&2; exit 2; }
IMPLEMENT_TMPDIR="${IMPLEMENT_TMPDIR:?IMPLEMENT_TMPDIR required}"
export IMPLEMENT_TMPDIR

rehydrate_plugin_root() {
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ]; then
        # shellcheck source=/dev/null
        . "$IMPLEMENT_TMPDIR/plugin-root.env"
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/session-env.sh" ]; then
        CLAUDE_PLUGIN_ROOT=$(awk 'BEGIN{p="LARCH_CLAUDE_PLUGIN_ROOT="} index($0,p)==1{print substr($0,length(p)+1); exit}' "$IMPLEMENT_TMPDIR/session-env.sh" 2>/dev/null || true)
    fi
    if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
        CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
    fi
    export CLAUDE_PLUGIN_ROOT
}

read_session_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/session-env.sh"
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$file" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session read-key --file "$file" --key "$key" --default "$default_value" 2>/dev/null || printf '%s\n' "$default_value"
    else
        printf '%s\n' "$default_value"
    fi
}

rehydrate_larch_triplet() {
    LARCH_TOKEN_SESSION_ID=$(read_session_key LARCH_TOKEN_SESSION_ID "${LARCH_TOKEN_SESSION_ID:-}")
    LARCH_CLAUDE_SOURCE_FILE=$(read_session_key LARCH_CLAUDE_SOURCE_FILE "${LARCH_CLAUDE_SOURCE_FILE:-}")
    LARCH_TIMING_LEDGER=$(read_session_key LARCH_TIMING_LEDGER "${LARCH_TIMING_LEDGER:-}")
    export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER
}

rehydrate_plugin_root
rehydrate_larch_triplet
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement "$CLAUDE_PLUGIN_ROOT/scripts/timing-ledger.sh" mark "Step 5 — review handoff" || true
round_start_file="$IMPLEMENT_TMPDIR/round-$FINAL_ROUND_NUM/round-start-s"
if [ -f "$round_start_file" ]; then
  round_start_s="$(tr -d '\r\n' < "$round_start_file" 2>/dev/null || true)"
  end_s="$(date +%s)"
  "$CLAUDE_PLUGIN_ROOT/skills/review-and-fix/scripts/record-implement-review-round-timing.sh" \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --round "$FINAL_ROUND_NUM" \
    --start-s "$round_start_s" \
    --end-s "$end_s" || true
fi
if [ "$RECORD_ONLY" = true ]; then
  exit 0
fi
if [ "$READY" = true ] || [ "${STEP5_HANDOFF_READY_TO_COMMIT:-false}" = true ]; then
  "$CLAUDE_PLUGIN_ROOT/skills/implement/scripts/commit-review-fixes.sh" --stage-all || true
fi
printf '%s
' 'progress: type p (or progress) at any time'
"$CLAUDE_PLUGIN_ROOT/scripts/run-step5-review.sh"   --implement-tmpdir "$IMPLEMENT_TMPDIR"   --mode loop   --starting-round "$((FINAL_ROUND_NUM + 1))"
