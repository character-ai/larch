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

read_run_flag_key() {
    local key=$1 default_value=$2 file
    file="${IMPLEMENT_TMPDIR:-}/run-flags.sh"
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

first_commit_kv_value() {
  local key
  key=$1
  awk -v key="$key" 'BEGIN { p = key "=" } index($0, p) == 1 { print substr($0, length(p) + 1); found = 1; exit } END { exit found ? 0 : 1 }'
}

relay_commit_kvs() {
  awk -F= '$1 == "NEXT_ACTION" || $1 == "COMMITTED" || $1 == "ERROR" || $1 == "SHA" || $1 == "COMMIT_OUTCOME" { print }'
}

relay_commit_kvs_without_next_action() {
  awk -F= '$1 == "COMMITTED" || $1 == "ERROR" || $1 == "SHA" || $1 == "COMMIT_OUTCOME" { print }'
}

commit_kv_count() {
  local key
  key=$1
  awk -v key="$key" 'BEGIN { p = key "="; count = 0 } index($0, p) == 1 { count += 1 } END { print count }'
}

rehydrate_plugin_root
rehydrate_larch_triplet
DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" timing mark "Step 5 — review handoff" || true
round_start_file="$IMPLEMENT_TMPDIR/round-$FINAL_ROUND_NUM/round-start-s"
if [ -f "$round_start_file" ]; then
  round_start_s="$(tr -d '\r\n' < "$round_start_file" 2>/dev/null || true)"
  ledger="$IMPLEMENT_TMPDIR/timing-ledger.tsv"
  round_decimal=$((10#$FINAL_ROUND_NUM))
  needs_record=true
  if [[ "$round_start_s" =~ ^[0-9]+$ ]] && [ -f "$ledger" ]; then
    if awk -F '\t' -v r="$round_decimal" -v s="$round_start_s" \
      '$2 == "round" && $4 == "implement" && $5 == "Step 5 — code review" && $6 == r && $7 == s { found=1 } END { exit found ? 0 : 1 }' \
      "$ledger" 2>/dev/null; then
      needs_record=false
    fi
  fi
  if [ "$needs_record" = true ] && [[ "$round_start_s" =~ ^[0-9]+$ ]]; then
    end_s="$(date +%s)"
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix record-round-timing \
      --implement-tmpdir "$IMPLEMENT_TMPDIR" \
      --round "$FINAL_ROUND_NUM" \
      --start-s "$round_start_s" \
      --end-s "$end_s" || true
  fi
fi
if [ "$RECORD_ONLY" = true ]; then
  exit 0
fi
if [ "$READY" = true ] || [ "${STEP5_HANDOFF_READY_TO_COMMIT:-false}" = true ]; then
  set +e
  commit_output="$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement commit-route --site step5-resume-handoff)"
  commit_rc=$?
  set -e
  next_action_count="$(printf '%s\n' "$commit_output" | commit_kv_count NEXT_ACTION)"
  next_action="$(printf '%s\n' "$commit_output" | first_commit_kv_value NEXT_ACTION || true)"
  case "$next_action_count:$next_action" in
    1:continue)
      printf 'NEXT_ACTION=%s\n' "$next_action"
      printf '%s\n' "$commit_output" | relay_commit_kvs_without_next_action
      if [ "$commit_rc" -ne 0 ]; then
        exit "$commit_rc"
      fi
      ;;
    1:stall)
      printf 'NEXT_ACTION=%s\n' "$next_action"
      printf '%s\n' "$commit_output" | relay_commit_kvs_without_next_action
      if [ "$commit_rc" -ne 0 ]; then
        exit "$commit_rc"
      fi
      exit 1
      ;;
    *)
      printf '%s\n' "$commit_output" | relay_commit_kvs
      if [ "$commit_rc" -ne 0 ]; then
        exit "$commit_rc"
      fi
      exit 1
      ;;
  esac
fi
printf '%s
' 'progress: type p (or progress) at any time'
difficulty_override=$(read_run_flag_key DIFFICULTY_OVERRIDE "")
case "$difficulty_override" in ""|TRIVIAL|MODERATE|HARD) ;; *) difficulty_override="" ;; esac
if [ -n "$difficulty_override" ]; then
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --mode loop \
    --starting-round "$((FINAL_ROUND_NUM + 1))" \
    --difficulty "$difficulty_override"
else
  python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
    --implement-tmpdir "$IMPLEMENT_TMPDIR" \
    --mode loop \
    --starting-round "$((FINAL_ROUND_NUM + 1))"
fi
