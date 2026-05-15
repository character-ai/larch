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
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-gemini-model-resolver.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-gemini-model-resolver.sh"
# shellcheck source=scripts/lib-external-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-external-launcher-common.sh"

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
TOKEN_BUDGET_CAP=""

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
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { larch_err "launch-gemini-implement.sh: --timing-task-kind requires a non-empty, non-flag-like value"; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) larch_err "launch-gemini-implement.sh: --token-budget-cap requires a positive integer"; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { larch_err "launch-gemini-implement.sh: --token-budget-cap requires a positive integer"; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
        *) larch_err "launch-gemini-implement.sh: unknown flag: $1"; exit 2 ;;
    esac
done

for var in TRANSCRIPT_PATH SIDECAR_LOG MANIFEST_PATH QA_PENDING_PATH PLAN_FILE FEATURE_FILE AGENT_PROMPT TIMEOUT; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        larch_err "launch-gemini-implement.sh: --$flag_lc is required"
        exit 2
    fi
done
[[ -f "$PLAN_FILE" ]]    || { larch_err "launch-gemini-implement.sh: plan file not found: $PLAN_FILE"; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { larch_err "launch-gemini-implement.sh: feature file not found: $FEATURE_FILE"; exit 2; }
[[ -f "$AGENT_PROMPT" ]] || { larch_err "launch-gemini-implement.sh: agent prompt not found: $AGENT_PROMPT"; exit 2; }
if [[ -n "$ANSWERS_FILE" && ! -f "$ANSWERS_FILE" ]]; then
    larch_err "launch-gemini-implement.sh: --answers-file given but path does not exist: $ANSWERS_FILE"
    exit 2
fi

case "$TIMEOUT" in
    ''|*[!0-9]*|0) larch_err "launch-gemini-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    larch_err "launch-gemini-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"
    exit 2
fi

if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/session-id" ]]; then
    file_id=$(tr -d '\r\n' < "${IMPLEMENT_TMPDIR}/session-id" 2>/dev/null || true)
    if [[ -n "$file_id" ]]; then export LARCH_TOKEN_SESSION_ID="$file_id"; fi
fi
if [[ -n "${IMPLEMENT_TMPDIR:-}" && -s "${IMPLEMENT_TMPDIR}/claude-source.env" ]]; then
    export LARCH_CLAUDE_SOURCE_FILE="${IMPLEMENT_TMPDIR}/claude-source.env"
fi

# Apply env-var cap when --token-budget-cap was not passed explicitly; validate
# the value (invalid values silently disable the cap rather than exit 2).
if [[ -z "$TOKEN_BUDGET_CAP" && -n "${LARCH_TOKEN_BUDGET_CAP_IMPLEMENT:-}" ]]; then
    case "$LARCH_TOKEN_BUDGET_CAP_IMPLEMENT" in
        ''|*[!0-9]*) ;;
        *) (( 10#${LARCH_TOKEN_BUDGET_CAP_IMPLEMENT} >= 1 )) && TOKEN_BUDGET_CAP="$LARCH_TOKEN_BUDGET_CAP_IMPLEMENT" ;;
    esac
fi

# Per-step token budget cap: short-circuit before spawning Gemini when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-gemini-implement}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        larch_err "⚠ launch-gemini-implement.sh: step token budget cap of $TOKEN_BUDGET_CAP tokens exceeded ($(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^TOTAL=/){print substr($i,7);exit}}}') combined vendor tokens); external implementer fan-out skipped"
        printf 'STATUS=cap_hit\n' > "$TRANSCRIPT_PATH"
        printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${TRANSCRIPT_PATH}.cap-hit"
        if [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
            printf 'STATUS=cap_hit\n%s\n' "$_budget_out" > "${IMPLEMENT_TMPDIR}/step-budget-cap-hit.env"
        fi
        emit_kv LAUNCHER_EXIT 0
        emit_kv MANIFEST_WRITTEN false
        emit_kv STATUS cap_hit
        exit 0
    fi
    unset _budget_out _budget_status
fi

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="gemini-implement"
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

append_launch_failure() {
    local site="$1" tool_label="$2" rc="$3" diag_file="$4" verdict="${5:-}" retry_count="${6:-}"
    [[ -x "$PLUGIN_ROOT/scripts/append-tool-failure.sh" ]] || return 0
    [[ -n "${IMPLEMENT_TMPDIR:-}" ]] || return 0
    local _args=()
    [[ -n "$verdict" ]] && _args+=(--verdict "$verdict")
    [[ -n "$retry_count" ]] && _args+=(--retry-count "$retry_count")
    "$PLUGIN_ROOT/scripts/append-tool-failure.sh" \
        --log "${IMPLEMENT_TMPDIR}/execution-issues.md" \
        --site "$site" --tool "$tool_label" --exit-code "$rc" \
        --category "Tool Failures" --output-file "$diag_file" \
        "${_args[@]}" --redact >/dev/null 2>&1 || true
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

# intentionally non-stable: plan/feature file paths are per-session; initial task for Gemini (not Claude API)
PROMPT="$(cat "$AGENT_PROMPT")

## This invocation's parameters

- Plan to implement: $PLAN_FILE
- Original feature description: $FEATURE_FILE
- Write manifest.json (atomically) at: $MANIFEST_PATH
- Write qa-pending.json (atomically, only if status=needs_qa) at: $QA_PENDING_PATH
- Working directory: $PWD (this is the repo root for git operations)
$RESUME_BLOCK

Begin by inspecting the current branch state, then proceed per the system prompt above."

GEMINI_MODEL_ERR=$(mktemp)
if GEMINI_MODEL=$(resolve_gemini_model 2> "$GEMINI_MODEL_ERR"); then
    rm -f "$GEMINI_MODEL_ERR"
else
    MODEL_RC=$?
    : > "$SIDECAR_LOG"
    cat "$GEMINI_MODEL_ERR" >> "$SIDECAR_LOG" 2>/dev/null || true
    rm -f "$GEMINI_MODEL_ERR"
    emit_timing_record "$MODEL_RC"
    emit_kv LAUNCHER_EXIT "$MODEL_RC"
    emit_kv MANIFEST_WRITTEN false
    emit_kv QA_PENDING_WRITTEN false
    emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
    emit_kv SIDECAR_LOG "$SIDECAR_LOG"
    exit 0
fi

LAUNCHER_EXIT=0
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "gemini"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
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
    if (( LAUNCHER_EXIT != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) \
        && { external_is_auth_failure "gemini" "$SIDECAR_LOG" || external_is_auth_failure "gemini" "$TRANSCRIPT_PATH"; }; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR_LOG" 2>/dev/null || true
        : > "$TRANSCRIPT_PATH" 2>/dev/null || true
        continue
    fi
    break
done

if (( LAUNCHER_EXIT != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "gemini" "$SIDECAR_LOG" "$TRANSCRIPT_PATH")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    _FAILURE_OUTPUT="$SIDECAR_LOG"
    if [[ ! -s "$_FAILURE_OUTPUT" && -s "$TRANSCRIPT_PATH" ]]; then
        _FAILURE_OUTPUT="$TRANSCRIPT_PATH"
    fi
    append_launch_failure "2" "gemini-implement" "$LAUNCHER_EXIT" "$_FAILURE_OUTPUT" "$_VERDICT" "$AUTH_ATTEMPT"
fi

MANIFEST_WRITTEN=false
QA_PENDING_WRITTEN=false
[[ -s "$MANIFEST_PATH" ]]   && MANIFEST_WRITTEN=true
[[ -s "$QA_PENDING_PATH" ]] && QA_PENDING_WRITTEN=true
emit_timing_record "$LAUNCHER_EXIT"

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
emit_kv MANIFEST_WRITTEN "$MANIFEST_WRITTEN"
emit_kv QA_PENDING_WRITTEN "$QA_PENDING_WRITTEN"
emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
emit_kv SIDECAR_LOG "$SIDECAR_LOG"
exit 0
