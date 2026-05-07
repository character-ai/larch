#!/usr/bin/env bash
# launch-gemini-implement.sh — Launch the Gemini implementer subprocess for /implement Step 2.
#
# This wrapper redirects run-external-agent.sh's progress chatter to a sidecar
# log file so the dispatcher (skills/implement/scripts/step2-implement.sh) only
# sees deterministic KEY=VALUE lines on stdout. The Gemini subprocess writes
# manifest.json and optionally qa-pending.json atomically inside
# $IMPLEMENT_TMPDIR — those paths are passed in as flags.
#
# Usage:
#   launch-gemini-implement.sh \
#     --transcript-path  PATH    # where Gemini transcript lands
#     --sidecar-log      PATH    # where run-external-agent.sh chatter is captured
#     --manifest-path    PATH    # where Gemini must write manifest.json
#     --qa-pending-path  PATH    # where Gemini must write qa-pending.json on needs_qa
#     --plan-file        PATH    # input: plan to implement
#     --feature-file     PATH    # input: original feature description
#     --agent-prompt     PATH    # input: agents/gemini-implementer.md path
#     --timeout          SECS    # wall-clock cap for Gemini subprocess
#     [--answers-file    PATH]   # optional: prior-cycle operator answers (resume)
#
# Stdout (KEY=VALUE only — no human progress text):
#   LAUNCHER_EXIT=<int>
#   MANIFEST_WRITTEN=<true|false>
#   QA_PENDING_WRITTEN=<true|false>
#   TRANSCRIPT=<path>
#   SIDECAR_LOG=<path>
#
# Exit codes:
#   0 — wrapper completed cleanly, regardless of Gemini's own exit code.
#   2 — wrapper-side error (missing flag, missing input file, etc.).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

TRANSCRIPT_PATH=""
SIDECAR_LOG=""
MANIFEST_PATH=""
QA_PENDING_PATH=""
PLAN_FILE=""
FEATURE_FILE=""
AGENT_PROMPT=""
TIMEOUT=""
ANSWERS_FILE=""
TIMING_TASK_KIND="${LARCH_TIMING_TASK_KIND:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --transcript-path)  TRANSCRIPT_PATH="${2:?--transcript-path requires a value}"; shift 2 ;;
        --sidecar-log)      SIDECAR_LOG="${2:?--sidecar-log requires a value}"; shift 2 ;;
        --manifest-path)    MANIFEST_PATH="${2:?--manifest-path requires a value}"; shift 2 ;;
        --qa-pending-path)  QA_PENDING_PATH="${2:?--qa-pending-path requires a value}"; shift 2 ;;
        --plan-file)        PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --feature-file)     FEATURE_FILE="${2:?--feature-file requires a value}"; shift 2 ;;
        --agent-prompt)     AGENT_PROMPT="${2:?--agent-prompt requires a value}"; shift 2 ;;
        --timeout)          TIMEOUT="${2:?--timeout requires a value}"; shift 2 ;;
        --answers-file)     ANSWERS_FILE="${2:?--answers-file requires a value}"; shift 2 ;;
        --timing-task-kind) TIMING_TASK_KIND="${2:?--timing-task-kind requires a value}"; shift 2 ;;
        *) echo "launch-gemini-implement.sh: unknown flag: $1" >&2; exit 2 ;;
    esac
done

for var in TRANSCRIPT_PATH SIDECAR_LOG MANIFEST_PATH QA_PENDING_PATH PLAN_FILE FEATURE_FILE AGENT_PROMPT TIMEOUT; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        echo "launch-gemini-implement.sh: --$flag_lc is required" >&2
        exit 2
    fi
done
[[ -f "$PLAN_FILE" ]]    || { echo "launch-gemini-implement.sh: plan file not found: $PLAN_FILE" >&2; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { echo "launch-gemini-implement.sh: feature file not found: $FEATURE_FILE" >&2; exit 2; }
[[ -f "$AGENT_PROMPT" ]] || { echo "launch-gemini-implement.sh: agent prompt not found: $AGENT_PROMPT" >&2; exit 2; }
if [[ -n "$ANSWERS_FILE" && ! -f "$ANSWERS_FILE" ]]; then
    echo "launch-gemini-implement.sh: --answers-file given but path does not exist: $ANSWERS_FILE" >&2
    exit 2
fi

case "$TIMEOUT" in
    ''|*[!0-9]*|0) echo "launch-gemini-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'" >&2; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    echo "launch-gemini-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'" >&2
    exit 2
fi
: "${TIMING_TASK_KIND:=gemini-implement}"
TIMING_START_S=$(date +%s)

emit_timing_record() {
    local rc="$1"
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor gemini \
        --task-kind "$TIMING_TASK_KIND" \
        --start-s "$TIMING_START_S" \
        --end-s "$end_s" \
        --output "$TRANSCRIPT_PATH" \
        --exit-code "$rc" \
        --status "$status" \
        >/dev/null 2>&1 || true
}

RESUME_BLOCK=""
if [[ -n "$ANSWERS_FILE" ]]; then
    RESUME_BLOCK="$(cat <<EOF

## Resume invocation

This is a RESUME of a prior /implement Step 2 attempt that ended in needs_qa.
Operator answers to your prior questions are in: $ANSWERS_FILE

Per agents/gemini-implementer.md "Resume protocol":
1. Inspect git log main..HEAD and git status FIRST.
2. Read the answers file.
3. If the answers are consistent with prior partial work, continue from there.
4. If not, set status=bailed bail_reason=resume-incompatible — DO NOT git reset.

EOF
)"
fi

PROMPT="$(cat "$AGENT_PROMPT")

## This invocation's parameters

- Plan to implement: $PLAN_FILE
- Original feature description: $FEATURE_FILE
- Write manifest.json (atomically) at: $MANIFEST_PATH
- Write qa-pending.json (atomically, only if status=needs_qa) at: $QA_PENDING_PATH
- Working directory: $PWD (this is the repo root for git operations)
$RESUME_BLOCK

Begin by inspecting the current branch state, then proceed per the system prompt above."

GEMINI_MODEL="${LARCH_GEMINI_MODEL:-${CLAUDE_PLUGIN_OPTION_GEMINI_MODEL:-gemini-2.5-pro}}"

LAUNCHER_EXIT=0
"$SCRIPT_DIR/run-external-agent.sh" \
    --tool gemini \
    --output "$TRANSCRIPT_PATH" \
    --timeout "$TIMEOUT" \
    --capture-stdout \
    -- \
    gemini --prompt "$PROMPT" --approval-mode yolo --skip-trust \
    --model "$GEMINI_MODEL" \
    >"$SIDECAR_LOG" 2>&1 || LAUNCHER_EXIT=$?

MANIFEST_WRITTEN=false
QA_PENDING_WRITTEN=false
[[ -s "$MANIFEST_PATH" ]]   && MANIFEST_WRITTEN=true
[[ -s "$QA_PENDING_PATH" ]] && QA_PENDING_WRITTEN=true
emit_timing_record "$LAUNCHER_EXIT"

printf 'LAUNCHER_EXIT=%s\n'           "$LAUNCHER_EXIT"
printf 'MANIFEST_WRITTEN=%s\n'        "$MANIFEST_WRITTEN"
printf 'QA_PENDING_WRITTEN=%s\n'      "$QA_PENDING_WRITTEN"
printf 'TRANSCRIPT=%s\n'              "$TRANSCRIPT_PATH"
printf 'SIDECAR_LOG=%s\n'             "$SIDECAR_LOG"
exit 0
