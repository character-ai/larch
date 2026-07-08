#!/usr/bin/env bash
# step-5-resume.sh — record Step 5 handoff timing and launch bgjob-owned resume work.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
FINAL_ROUND_NUM=""
READY=false
RECORD_ONLY=false
BGJOB_CHILD=false
MERGE_RESULT_ENV=""
CHECKS_SITE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --bgjob-child) BGJOB_CHILD=true; shift ;;
        --merge-result-env) [ $# -ge 2 ] || exit 2; MERGE_RESULT_ENV=$2; shift 2 ;;
        --checks-site) [ $# -ge 2 ] || exit 2; CHECKS_SITE=$2; shift 2 ;;
        --final-round-num) [ $# -ge 2 ] || exit 2; FINAL_ROUND_NUM=$2; shift 2 ;;
        --ready-to-commit) READY=true; shift ;;
        --record-only) RECORD_ONLY=true; shift ;;
        --help) printf '%s
' 'Usage: step-5-resume.sh --final-round-num N [--checks-site SITE] [--ready-to-commit|--record-only]'; exit 0 ;;
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

record_handoff_timing() {
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
}

run_resume_worker() {
    record_handoff_timing
    if [ "$RECORD_ONLY" = true ]; then
      exit 0
    fi
    if [ -n "$CHECKS_SITE" ]; then
      python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" implement checks-step5-resume --checks-site "$CHECKS_SITE" --final-round-num "$FINAL_ROUND_NUM"
      exit $?
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
}

rehydrate_plugin_root
rehydrate_larch_triplet
export PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python${PYTHONPATH:+:$PYTHONPATH}"

if [ "$BGJOB_CHILD" = true ]; then
    [ -n "$MERGE_RESULT_ENV" ] || { printf '%s
' 'step-5-resume.sh: --merge-result-env is required in child mode' >&2; exit 2; }
    MERGE_RESULT_ENV_PARENT="${MERGE_RESULT_ENV%/*}"
    [ -L "$MERGE_RESULT_ENV_PARENT" ] && { printf '%s
' 'step-5-resume.sh: refusing symlinked merge-result-env parent' >&2; exit 2; }
    MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
    trap 'rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true' EXIT
    set +e
    run_resume_worker | tee "$MERGE_RESULT_ENV_TMP"
    pipe_status=("${PIPESTATUS[@]}")
    set -e
    rc=${pipe_status[0]}
    tee_rc=${pipe_status[1]}
    if [ "$tee_rc" -ne 0 ]; then
        rc=$tee_rc
    fi
    if [ -L "$MERGE_RESULT_ENV" ]; then
        exit 2
    fi
    mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || rc=$?
    exit "$rc"
fi

if [ "$RECORD_ONLY" = true ]; then
    record_handoff_timing
    exit 0
fi

if [ -L "$IMPLEMENT_TMPDIR/bgjob" ]; then
    printf '%s
' 'step-5-resume.sh: refusing symlinked bgjob directory' >&2
    exit 2
fi
mkdir -p "$IMPLEMENT_TMPDIR/bgjob" "$IMPLEMENT_TMPDIR/.completed"
STEP="implement-step5-resume"
MERGE_RESULT_ENV="$IMPLEMENT_TMPDIR/bgjob/$STEP.merge.env"
MERGE_RESULT_ENV_TMP="$(mktemp "${MERGE_RESULT_ENV}.tmp.XXXXXX")" || exit 2
: >"$MERGE_RESULT_ENV_TMP"
[ -L "$MERGE_RESULT_ENV" ] && { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; printf '%s
' 'step-5-resume.sh: refusing symlinked merge-result-env' >&2; exit 2; }
mv -f "$MERGE_RESULT_ENV_TMP" "$MERGE_RESULT_ENV" 2>/dev/null || { rm -f "$MERGE_RESULT_ENV_TMP" 2>/dev/null || true; exit 2; }
rm -f "$IMPLEMENT_TMPDIR/.completed/step-5-resume-terminal" 2>/dev/null || true

CHILD_ARGS=(--bgjob-child --merge-result-env "$MERGE_RESULT_ENV" --final-round-num "$FINAL_ROUND_NUM")
if [ "$READY" = true ]; then
    CHILD_ARGS+=(--ready-to-commit)
fi
if [ -n "$CHECKS_SITE" ]; then
    CHILD_ARGS+=(--checks-site "$CHECKS_SITE")
fi

python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" bgjob start \
    --step "$STEP" \
    --tmpdir "$IMPLEMENT_TMPDIR" \
    --budget-s 32700 \
    --owner-pid "${LARCH_CLAUDE_PID:-$PPID}" \
    --merge-result-env "$MERGE_RESULT_ENV" \
    --sentinel "$IMPLEMENT_TMPDIR/.completed/step-5-resume-terminal" \
    -- \
    bash "$SCRIPT_DIR/step-5-resume.sh" "${CHILD_ARGS[@]}"
