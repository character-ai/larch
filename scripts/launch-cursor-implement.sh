#!/usr/bin/env bash
# launch-cursor-implement.sh — Launch the Cursor implementer subprocess for /implement Step 2.
#
# Modeled after launch-review.sh --tool cursor but with a tighter stdout contract:
# this wrapper redirects run-external-agent.sh's progress chatter (⏳, ✓, ❌)
# to a sidecar log file so the dispatcher (skills/implement/scripts/step2-implement.sh)
# only sees deterministic KEY=VALUE lines on stdout. The dispatcher's parser
# would otherwise be brittle against the wrapper's human-readable progress
# messages.
#
# The Cursor subprocess writes manifest.json and (optionally) qa-pending.json
# atomically inside $IMPLEMENT_TMPDIR — those paths are passed in as flags
# so this launcher does not need to know how the dispatcher organizes its
# tmpdir.
#
# Usage:
#   launch-cursor-implement.sh \
#     --transcript-path  PATH    # where Cursor transcript lands
#     --sidecar-log      PATH    # where run-external-agent.sh chatter is captured
#     --manifest-path    PATH    # where Cursor must write manifest.json
#     --qa-pending-path  PATH    # where Cursor must write qa-pending.json on needs_qa
#     --plan-file        PATH    # input: plan to implement
#     --feature-file     PATH    # input: original feature description
#     --agent-prompt     PATH    # input: agents/cursor-implementer.md path
#     --timeout          SECS    # wall-clock cap for Cursor subprocess
#     [--answers-file    PATH]   # optional: prior-cycle operator answers (resume)
#
# Stdout (KEY=VALUE only — no human progress text):
#   LAUNCHER_EXIT=<int>            # exit code reported by run-external-agent.sh
#   MANIFEST_WRITTEN=<true|false>  # whether manifest.json exists post-run
#   QA_PENDING_WRITTEN=<true|false># whether qa-pending.json exists post-run
#   TRANSCRIPT=<path>              # path to Cursor transcript on disk (sidecar)
#   SIDECAR_LOG=<path>             # path to run-external-agent.sh chatter log
#
# Exit codes:
#   0 — wrapper completed cleanly, regardless of Cursor's own exit code
#       (the dispatcher inspects MANIFEST_WRITTEN + LAUNCHER_EXIT to decide
#       what happened).
#       Preflight failures in model-args loading emit the same five-line KV
#       envelope and exit 0, with LAUNCHER_EXIT carrying the failure rc.
#   2 — wrapper-side error (missing flag, missing input file, etc.); exit
#       before launching Cursor.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
# shellcheck source=scripts/lib-failed-agent-stderr-tail.sh
source "$SCRIPT_DIR/lib-failed-agent-stderr-tail.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-cursor-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-cursor-launcher-common.sh"

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
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { larch_err "launch-cursor-implement.sh: --timing-task-kind requires a non-empty, non-flag-like value"; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) larch_err "launch-cursor-implement.sh: --token-budget-cap requires a positive integer"; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { larch_err "launch-cursor-implement.sh: --token-budget-cap requires a positive integer"; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
        *) larch_err "launch-cursor-implement.sh: unknown flag: $1"; exit 2 ;;
    esac
done

for var in TRANSCRIPT_PATH SIDECAR_LOG MANIFEST_PATH QA_PENDING_PATH PLAN_FILE FEATURE_FILE AGENT_PROMPT TIMEOUT; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        larch_err "launch-cursor-implement.sh: --$flag_lc is required"
        exit 2
    fi
done
# shellcheck disable=SC2154
[[ -f "$PLAN_FILE" ]]    || { larch_err "launch-cursor-implement.sh: plan file not found: $PLAN_FILE"; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { larch_err "launch-cursor-implement.sh: feature file not found: $FEATURE_FILE"; exit 2; }
[[ -f "$AGENT_PROMPT" ]] || { larch_err "launch-cursor-implement.sh: agent prompt not found: $AGENT_PROMPT"; exit 2; }
if [[ -n "$ANSWERS_FILE" && ! -f "$ANSWERS_FILE" ]]; then
    larch_err "launch-cursor-implement.sh: --answers-file given but path does not exist: $ANSWERS_FILE"
    exit 2
fi

case "$TIMEOUT" in
    ''|*[!0-9]*|0) larch_err "launch-cursor-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    larch_err "launch-cursor-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"
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

# Per-step token budget cap: short-circuit before spawning Cursor when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-cursor-implement}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        larch_err "⚠ launch-cursor-implement.sh: step token budget cap of $TOKEN_BUDGET_CAP tokens exceeded ($(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^TOTAL=/){print substr($i,7);exit}}}') combined vendor tokens); external implementer fan-out skipped"
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

# Token-ledger step mark runs here (not in step2-implement.sh before launch):
# check-step-token-budget.sh sums vendor totals since the last JSONL "mark"
# row; an early mark would reset the window and hide spend that must trigger
# cap_hit before Cursor spawns.
"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 2 — implementation" || true

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="cursor-implement"
fi
: "${TIMING_TASK_KIND:=cursor-implement}"
TIMING_START_S=$(date +%s)

emit_timing_record() {
    local rc="$1"
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor cursor \
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

# Compose the Cursor prompt by concatenating the agent system prompt with
# inline references to the plan, feature, manifest path, qa-pending path,
# and (optionally) the answers file. Keeping this composition in shell (not
# in agent-side prose) lets the launcher's contract document exactly what
# Cursor sees on every invocation without depending on Cursor's tool use to
# read referenced files.
RESUME_BLOCK=""
if [[ -n "$ANSWERS_FILE" ]]; then
    RESUME_BLOCK="$(cat <<EOF

## Resume invocation

This is a RESUME of a prior /implement Step 2 attempt that ended in needs_qa.
Operator answers to your prior questions are in: $ANSWERS_FILE

Per agents/cursor-implementer.md "Resume protocol":
1. Inspect git log main..HEAD and git status FIRST.
2. Read the answers file.
3. If the answers are consistent with prior partial work, continue from there.
4. If not, set status=bailed bail_reason=resume-incompatible — DO NOT git reset.

EOF
)"
fi

# intentionally non-stable: plan/feature file paths are per-session; initial task for Cursor (not Claude API)
PROMPT="$(cat "$AGENT_PROMPT")

## This invocation's parameters

- Plan to implement: $PLAN_FILE
- Original feature description: $FEATURE_FILE
- Write manifest.json (atomically) at: $MANIFEST_PATH
- Write qa-pending.json (atomically, only if status=needs_qa) at: $QA_PENDING_PATH
- Working directory: $PWD (this is the repo root for git operations)
$RESUME_BLOCK

Begin by inspecting the current branch state, then proceed per the system prompt above."

PROMPT_FILE_SIDECAR="${TRANSCRIPT_PATH}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE_SIDECAR"

MODEL_ARGS_ERR=$(mktemp)
MODEL_ARGS_RC=0
cursor_launcher_load_model_args 2> "$MODEL_ARGS_ERR" || MODEL_ARGS_RC=$?
if [[ "$MODEL_ARGS_RC" -ne 0 ]]; then
    : > "$SIDECAR_LOG"
    cat "$MODEL_ARGS_ERR" >> "$SIDECAR_LOG" 2>/dev/null || true
    rm -f "$MODEL_ARGS_ERR"
    write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true
    emit_timing_record "$MODEL_ARGS_RC"
    emit_kv LAUNCHER_EXIT "$MODEL_ARGS_RC"
    emit_kv MANIFEST_WRITTEN false
    emit_kv QA_PENDING_WRITTEN false
    emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
    emit_kv SIDECAR_LOG "$SIDECAR_LOG"
    exit 0
fi
rm -f "$MODEL_ARGS_ERR"
WRAPPED_PROMPT=$("$SCRIPT_DIR/cursor-wrap-prompt.sh" "$PROMPT")

# Run Cursor auth preflight. On preflight failure (Darwin + empty
# CURSOR_API_KEY + missing `cursor-user` keychain entry), emit the standard
# KV envelope before exiting so step2-implement.sh's parser surfaces a
# specific failure (LAUNCHER_EXIT=2 + actionable SIDECAR_LOG content)
# instead of a generic timeout/missing-manifest message.
PREFLIGHT_RC=0
PREFLIGHT_ERR=$(mktemp)
cursor_launcher_setup_auth_argv 2> "$PREFLIGHT_ERR" || PREFLIGHT_RC=$?
cat "$PREFLIGHT_ERR" >> "$SIDECAR_LOG" 2>/dev/null || true
rm -f "$PREFLIGHT_ERR"
if [[ "$PREFLIGHT_RC" != "0" ]]; then
    write_failed_agent_stderr_tail "$SIDECAR_LOG" "$TRANSCRIPT_PATH" || true
    emit_timing_record "$PREFLIGHT_RC"
    emit_kv LAUNCHER_EXIT "$PREFLIGHT_RC"
    emit_kv MANIFEST_WRITTEN false
    emit_kv QA_PENDING_WRITTEN false
    emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
    emit_kv SIDECAR_LOG "$SIDECAR_LOG"
    # Exit 0 keeps the launcher contract (LAUNCHER_EXIT is the failure
    # signal, not the wrapper's process exit). The dispatcher reads
    # LAUNCHER_EXIT=2 and surfaces the SIDECAR_LOG content.
    exit 0
fi

# Run the wrapper, redirecting its stdout AND stderr to the sidecar log so
# Claude (the dispatcher's caller) never sees the wrapper's progress lines.
# The wrapper's own exit code is captured into LAUNCHER_EXIT.
LAUNCHER_EXIT=0
unset CURSOR_CONFIG_DIR_TMP CURSOR_CONFIG_DIR
cursor_launcher_setup_private_config_dir
# shellcheck disable=SC2154 # CURSOR_CONFIG_DIR_TMP set by cursor_launcher_setup_private_config_dir.
trap 'cursor_launcher_cleanup_private_config_dir' EXIT
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
AUTH_ATTEMPT=1
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "cursor"
    RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done \
    "$SCRIPT_DIR/run-external-agent.sh" \
        --tool cursor \
        --output "$TRANSCRIPT_PATH" \
        --timeout "$TIMEOUT" \
        --capture-stdout-only \
        -- \
        cursor agent -p --force --trust \
        --output-format json \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        ${CURSOR_AUTH_ARGS[@]+"${CURSOR_AUTH_ARGS[@]}"} \
        --workspace "$PWD" \
        "$WRAPPED_PROMPT" \
        >"$SIDECAR_LOG" 2>&1 &
    WRAPPER_PID=$!
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    wait "$WRAPPER_PID" && LAUNCHER_EXIT=0 || LAUNCHER_EXIT=$?
    if (( LAUNCHER_EXIT != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) \
        && { external_is_auth_failure "cursor" "$SIDECAR_LOG" || external_is_auth_failure "cursor" "${TRANSCRIPT_PATH}.diag"; }; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR_LOG" 2>/dev/null || true
        : > "${TRANSCRIPT_PATH}.diag" 2>/dev/null || true
        # Preserve .stderr-tail across retry; run-external-agent overwrites it on
        # a new failure or removes it on success, so deletion here is a no-op at best
        # and loses the prior tail at worst (when the retry fails with empty diag).
        continue
    fi
    break
done
cursor_launcher_cleanup_private_config_dir

if (( LAUNCHER_EXIT != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "cursor" "$SIDECAR_LOG" "${TRANSCRIPT_PATH}.diag")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    _FAILURE_OUTPUT="$SIDECAR_LOG"
    if [[ ! -s "$_FAILURE_OUTPUT" && -s "${TRANSCRIPT_PATH}.diag" ]]; then
        _FAILURE_OUTPUT="${TRANSCRIPT_PATH}.diag"
    fi
    append_launch_failure "2" "cursor-implement" "$LAUNCHER_EXIT" "$_FAILURE_OUTPUT" "$_VERDICT" "$AUTH_ATTEMPT"
    write_failed_agent_stderr_tail "$_FAILURE_OUTPUT" "$TRANSCRIPT_PATH" || true
fi

cursor_launcher_append_outer_meta "${TRANSCRIPT_PATH}.meta" "$SCRIPT_DIR/launch-cursor-implement.sh" "$PROMPT_FILE_SIDECAR" "$PWD"

if command -v jq >/dev/null 2>&1; then
    read -r INP OUT CR CW < <(jq -r '.usage // {} | "\(.inputTokens // 0) \(.outputTokens // 0) \(.cacheReadTokens // 0) \(.cacheWriteTokens // 0)"' "$TRANSCRIPT_PATH" 2>/dev/null || echo "0 0 0 0")
    if [[ "$INP" =~ ^[0-9]+$ && "$OUT" =~ ^[0-9]+$ && "$CR" =~ ^[0-9]+$ && "$CW" =~ ^[0-9]+$ ]]; then
        TOT=$((INP + OUT + CR + CW))
        "$PLUGIN_ROOT/scripts/token-ledger.sh" record-vendor cursor input="$INP" output="$OUT" cache_read="$CR" cache_create="$CW" total="$TOT" raw="cursor_implement" >/dev/null 2>&1 || true
    fi
fi
emit_timing_record "$LAUNCHER_EXIT"

cursor_launcher_promote_inner_done "$TRANSCRIPT_PATH"

MANIFEST_WRITTEN=false
QA_PENDING_WRITTEN=false
[[ -s "$MANIFEST_PATH" ]]   && MANIFEST_WRITTEN=true
[[ -s "$QA_PENDING_PATH" ]] && QA_PENDING_WRITTEN=true

if [[ "$MANIFEST_WRITTEN" == true ]] && command -v jq >/dev/null 2>&1; then
    _manifest_status=$(jq -r 'if type=="object" then .status // "" else "" end' "$MANIFEST_PATH" 2>/dev/null || true)
    if [[ "$_manifest_status" == "bailed" ]]; then
        _bailed_tail_src="${TRANSCRIPT_PATH}.diag"
        if [[ ! -s "$_bailed_tail_src" ]]; then
            _bailed_tail_src="$SIDECAR_LOG"
        fi
        write_failed_agent_stderr_tail "$_bailed_tail_src" "$TRANSCRIPT_PATH" || true
    fi
fi

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
emit_kv MANIFEST_WRITTEN "$MANIFEST_WRITTEN"
emit_kv QA_PENDING_WRITTEN "$QA_PENDING_WRITTEN"
emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
emit_kv SIDECAR_LOG "$SIDECAR_LOG"
exit 0
