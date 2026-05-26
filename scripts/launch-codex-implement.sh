#!/usr/bin/env bash
# launch-codex-implement.sh — Launch the Codex implementer subprocess for /implement Step 2.
#
# Modeled after launch-review.sh --tool codex but with a tighter stdout contract:
# this wrapper redirects run-external-agent.sh's progress chatter (⏳, ✓, ❌)
# to a sidecar log file so the dispatcher (skills/implement/scripts/step2-implement.sh)
# only sees deterministic KEY=VALUE lines on stdout. The dispatcher's parser
# would otherwise be brittle against the wrapper's human-readable progress
# messages.
#
# The Codex subprocess writes manifest.json and (optionally) qa-pending.json
# atomically inside $IMPLEMENT_TMPDIR — those paths are passed in as flags
# so this launcher does not need to know how the dispatcher organizes its
# tmpdir.
#
# Usage:
#   launch-codex-implement.sh \
#     --transcript-path  PATH    # where Codex's --output-last-message lands
#     --sidecar-log      PATH    # where run-external-agent.sh chatter is captured
#     --manifest-path    PATH    # where Codex must write manifest.json
#     --qa-pending-path  PATH    # where Codex must write qa-pending.json on needs_qa
#     --plan-file        PATH    # input: plan to implement
#     --feature-file     PATH    # input: original feature description
#     --agent-prompt     PATH    # input: agents/codex-implementer.md path
#     --timeout          SECS    # wall-clock cap for Codex subprocess
#     [--answers-file    PATH]   # optional: prior-cycle operator answers (resume)
#
# Stdout (KEY=VALUE only — no human progress text):
#   LAUNCHER_EXIT=<int>            # exit code reported by run-external-agent.sh
#   MANIFEST_WRITTEN=<true|false>  # whether manifest.json exists post-run
#   QA_PENDING_WRITTEN=<true|false># whether qa-pending.json exists post-run
#   TRANSCRIPT=<path>              # path to Codex transcript on disk (sidecar)
#   SIDECAR_LOG=<path>             # path to run-external-agent.sh chatter log
#
# Exit codes:
#   0 — wrapper completed cleanly, regardless of Codex's own exit code
#       (the dispatcher inspects MANIFEST_WRITTEN + LAUNCHER_EXIT to decide
#       what happened).
#       Preflight failures in model-args resolution emit the same five-line
#       KV envelope and exit 0, with LAUNCHER_EXIT carrying the failure rc.
#   2 — wrapper-side error (missing flag, missing input file, etc.); exit
#       before launching Codex.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-codex-launcher-common.sh
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib-codex-launcher-common.sh"

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
        --timing-task-kind) [[ -n "${2:-}" && "${2}" != --* ]] || { larch_err "launch-codex-implement.sh: --timing-task-kind requires a non-empty, non-flag-like value"; exit 2; }; TIMING_TASK_KIND="$2"; shift 2 ;;
        --token-budget-cap) case "${2:-}" in ''|*[!0-9]*) larch_err "launch-codex-implement.sh: --token-budget-cap requires a positive integer"; exit 2 ;; esac; (( 10#${2:-0} >= 1 )) || { larch_err "launch-codex-implement.sh: --token-budget-cap requires a positive integer"; exit 2; }; TOKEN_BUDGET_CAP="$2"; shift 2 ;;
        *) larch_err "launch-codex-implement.sh: unknown flag: $1"; exit 2 ;;
    esac
done

for var in TRANSCRIPT_PATH SIDECAR_LOG MANIFEST_PATH QA_PENDING_PATH PLAN_FILE FEATURE_FILE AGENT_PROMPT TIMEOUT; do
    if [[ -z "${!var}" ]]; then
        flag_lc=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
        larch_err "launch-codex-implement.sh: --$flag_lc is required"
        exit 2
    fi
done
# shellcheck disable=SC2154
[[ -f "$PLAN_FILE" ]]    || { larch_err "launch-codex-implement.sh: plan file not found: $PLAN_FILE"; exit 2; }
[[ -f "$FEATURE_FILE" ]] || { larch_err "launch-codex-implement.sh: feature file not found: $FEATURE_FILE"; exit 2; }
[[ -f "$AGENT_PROMPT" ]] || { larch_err "launch-codex-implement.sh: agent prompt not found: $AGENT_PROMPT"; exit 2; }
if [[ -n "$ANSWERS_FILE" && ! -f "$ANSWERS_FILE" ]]; then
    larch_err "launch-codex-implement.sh: --answers-file given but path does not exist: $ANSWERS_FILE"
    exit 2
fi

case "$TIMEOUT" in
    ''|*[!0-9]*|0) larch_err "launch-codex-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"; exit 2 ;;
esac
if (( 10#$TIMEOUT < 1 )); then
    larch_err "launch-codex-implement.sh: --timeout must be a positive integer (seconds), got '$TIMEOUT'"
    exit 2
fi

MANIFEST_DIR=$(dirname "$MANIFEST_PATH")
QA_PENDING_DIR=$(dirname "$QA_PENDING_PATH")
if [[ ! -d "$MANIFEST_DIR" ]]; then
    larch_err "launch-codex-implement.sh: session tmpdir does not exist: $MANIFEST_DIR"
    exit 2
fi
if [[ ! -d "$QA_PENDING_DIR" ]]; then
    larch_err "launch-codex-implement.sh: session tmpdir does not exist: $QA_PENDING_DIR"
    exit 2
fi
SESSION_TMPDIR=$(cd "$MANIFEST_DIR" && pwd -P)
QA_TMPDIR=$(cd "$QA_PENDING_DIR" && pwd -P)
if [[ "$SESSION_TMPDIR" != "$QA_TMPDIR" ]]; then
    larch_err "launch-codex-implement.sh: --manifest-path and --qa-pending-path must share the same parent directory (got: $SESSION_TMPDIR vs $QA_TMPDIR)"
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

# Per-step token budget cap: short-circuit before spawning Codex when the
# combined vendor spend since the last ledger mark already exceeds the cap.
if [[ -n "$TOKEN_BUDGET_CAP" ]]; then
    _budget_out=$("$SCRIPT_DIR/check-step-token-budget.sh" --cap "$TOKEN_BUDGET_CAP" --step "${TIMING_TASK_KIND:-codex-implement}" 2>/dev/null || true)
    _budget_status=$(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^STATUS=/){print substr($i,8);exit}}}')
    if [[ "$_budget_status" == "cap_hit" ]]; then
        larch_err "⚠ launch-codex-implement.sh: step token budget cap of $TOKEN_BUDGET_CAP tokens exceeded ($(printf '%s' "$_budget_out" | awk '{for(i=1;i<=NF;i++){if($i~/^TOTAL=/){print substr($i,7);exit}}}') combined vendor tokens); external implementer fan-out skipped"
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
# cap_hit before Codex spawns.
"$PLUGIN_ROOT/scripts/token-ledger.sh" mark "Step 2 — implementation" || true

# Defensive: env-derived LARCH_TIMING_TASK_KIND may be empty or flag-shaped
# (e.g. "--prompt") if a caller mis-parses argv. The CLI form was
# already validated above (#1480); apply the same predicate to the env path
# and fall back silently. Whitespace-only and other invalid-but-non-flag
# shapes rely on timing-ledger.sh's regex backstop (do not extend here).
if [[ -z "$TIMING_TASK_KIND" || "$TIMING_TASK_KIND" == --* ]]; then
    TIMING_TASK_KIND="codex-implement"
fi
: "${TIMING_TASK_KIND:=codex-implement}"
TIMING_START_S=$(date +%s)

emit_timing_record() {
    local rc="$1"
    local end_s status
    end_s=$(date +%s)
    (( rc == 0 )) && status=complete || status=signal
    "$PLUGIN_ROOT/scripts/timing-ledger.sh" record-vendor-task \
        --vendor codex \
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

# Compose the dynamic Codex prompt with inline references to the plan,
# feature, manifest path, qa-pending path, and (optionally) the answers
# file. The static implementer preamble is delivered through
# CODEX_HOME/config.toml as the Codex `instructions` field so it stays out
# of retry sidecars and can benefit from vendor prefix caching.
RESUME_BLOCK=""
if [[ -n "$ANSWERS_FILE" ]]; then
    RESUME_BLOCK="$(cat <<EOF

## Resume invocation

This is a RESUME of a prior /implement Step 2 attempt that ended in needs_qa.
Operator answers to your prior questions are in: $ANSWERS_FILE

Per agents/codex-implementer.md "Resume protocol":
1. Inspect git log main..HEAD and git status FIRST.
2. Read the answers file.
3. If the answers are consistent with prior partial work, continue from there.
4. If not, set status=bailed bail_reason=resume-incompatible — DO NOT git reset.

EOF
)"
fi

AGENT_BODY=$(awk 'BEGIN{n=0} /^---[[:space:]]*$/{n++; if(n==2){found=1; next}; next} found{print}' "$AGENT_PROMPT")
if [[ -z "$AGENT_BODY" ]]; then
    larch_err "launch-codex-implement.sh: agent prompt body is empty after frontmatter stripping: $AGENT_PROMPT"
    exit 2
fi
if grep -Fq "'''" <<< "$AGENT_BODY"; then
    larch_err "launch-codex-implement.sh: agent prompt body contains TOML triple-single-quote delimiter"
    exit 2
fi

CODEX_HOME_DIR=$(mktemp -d /tmp/larch-codex-home-XXXXXX)
PROJECT_KEY=${PWD//\\/\\\\}
PROJECT_KEY=${PROJECT_KEY//\"/\\\"}
TRUST_CONFIG_ARG="projects.\"$PROJECT_KEY\".trust_level=\"trusted\""
{
    printf "instructions = '''\n%s\n'''\n\n" "$AGENT_BODY"
    if [[ -f ~/.codex/config.toml ]]; then
        # Strip any existing top-level `instructions` assignment to avoid duplicate
        # keys — TOML parsers treat duplicate top-level keys as an error or silently
        # drop the second value, either of which breaks the launch.
        # Handles: triple-single-quote blocks ('''...'''), triple-double-quote blocks
        # ("""..."""), and single-line string forms ("..." or '...').
        awk "
            /^[[:space:]]*instructions[[:space:]]*=[[:space:]]*'''/ { skip=1; block_end=\"'''\"; next }
            /^[[:space:]]*instructions[[:space:]]*=[[:space:]]*\"\"\"/ { skip=1; block_end=\"\\\"\\\"\\\"\"; next }
            skip && index(\$0, block_end) { skip=0; next }
            skip { next }
            /^[[:space:]]*instructions[[:space:]]*=/ { next }
            { print }
        " ~/.codex/config.toml
        printf '\n'
    fi
} > "$CODEX_HOME_DIR/config.toml"
if [[ -f ~/.codex/auth.json ]]; then
    ln -sf "$(cd ~/.codex && pwd)/auth.json" "$CODEX_HOME_DIR/auth.json"
fi

# intentionally non-stable: plan/feature file paths are per-session; initial task for Codex (not Claude API)
PROMPT="## This invocation's parameters

- Plan to implement: $PLAN_FILE
- Original feature description: $FEATURE_FILE
- Write manifest.json (atomically) at: $SESSION_TMPDIR/$(basename "$MANIFEST_PATH")
- Write qa-pending.json (atomically, only if status=needs_qa) at: $SESSION_TMPDIR/$(basename "$QA_PENDING_PATH")
- Working directory: $PWD (this is the repo root for git operations)
$RESUME_BLOCK

Begin by inspecting the current branch state, then proceed per the system prompt above."

PROMPT_FILE_SIDECAR="${TRANSCRIPT_PATH}.prompt"
printf '%s' "$PROMPT" > "$PROMPT_FILE_SIDECAR"

MODEL_ARGS_TMP=$(mktemp)
trap 'rm -f "$MODEL_ARGS_TMP"; rm -rf "$CODEX_HOME_DIR"' EXIT
MODEL_ARGS_ERR=$(mktemp)
MODEL_ARGS_RC=0
"$SCRIPT_DIR/agent-model-args.sh" --tool codex --with-effort > "$MODEL_ARGS_TMP" 2> "$MODEL_ARGS_ERR" || MODEL_ARGS_RC=$?
if [[ "$MODEL_ARGS_RC" -ne 0 ]]; then
    : > "$SIDECAR_LOG"
    cat "$MODEL_ARGS_ERR" >> "$SIDECAR_LOG" 2>/dev/null || true
    rm -f "$MODEL_ARGS_ERR"
    emit_timing_record "$MODEL_ARGS_RC"
    emit_kv LAUNCHER_EXIT "$MODEL_ARGS_RC"
    emit_kv MANIFEST_WRITTEN false
    emit_kv QA_PENDING_WRITTEN false
    emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
    emit_kv SIDECAR_LOG "$SIDECAR_LOG"
    exit 0
fi
rm -f "$MODEL_ARGS_ERR"
MODEL_ARGS=()
while IFS= read -r arg; do
    MODEL_ARGS+=("$arg")
done < "$MODEL_ARGS_TMP"

# Run the wrapper, redirecting stderr to the sidecar log so Claude (the
# dispatcher's caller) never sees the wrapper's progress lines. Codex JSONL
# usage stays on stdout in ${TRANSCRIPT_PATH}.events.jsonl for per-bucket
# accounting. The wrapper's own exit code is captured into LAUNCHER_EXIT.
LAUNCHER_EXIT=0
MAX_AUTH_RETRIES=${LARCH_EXTERNAL_AUTH_RETRIES:-5}
case "$MAX_AUTH_RETRIES" in ''|*[!0-9]*|0) MAX_AUTH_RETRIES=5 ;; esac
HOLD=${LARCH_EXTERNAL_SERIAL_LOCK_DELAY:-0.5}
AUTH_ATTEMPT=1
CODEX_EVENTS="${TRANSCRIPT_PATH}.events.jsonl"
while (( AUTH_ATTEMPT <= MAX_AUTH_RETRIES )); do
    _SERIAL_LOCK=""
    external_serial_lock_acquire _SERIAL_LOCK "codex"
    external_serial_lock_release_after "$_SERIAL_LOCK" "$HOLD"
    LAUNCHER_EXIT=0
    rm -f "$CODEX_EVENTS"
    CODEX_HOME="$CODEX_HOME_DIR" "$SCRIPT_DIR/run-external-agent.sh" \
        --tool codex \
        --output "$TRANSCRIPT_PATH" \
        --timeout "$TIMEOUT" \
        -- \
        codex exec --full-auto -C "$PWD" \
        --add-dir "$SESSION_TMPDIR" \
        --add-dir "$PWD" \
        ${MODEL_ARGS[@]+"${MODEL_ARGS[@]}"} \
        -c "$TRUST_CONFIG_ARG" \
        --output-last-message "$TRANSCRIPT_PATH" \
        --json \
        -- \
        "$PROMPT" \
        >"$CODEX_EVENTS" 2>"$SIDECAR_LOG" || LAUNCHER_EXIT=$?
    if (( LAUNCHER_EXIT != 0 && AUTH_ATTEMPT < MAX_AUTH_RETRIES )) && external_is_auth_failure "codex" "$SIDECAR_LOG"; then
        AUTH_ATTEMPT=$((AUTH_ATTEMPT + 1))
        : > "$SIDECAR_LOG" 2>/dev/null || true
        continue
    fi
    break
done

if (( LAUNCHER_EXIT != 0 )); then
    _AUTH_VERDICT=$(external_auth_verdict "codex" "$SIDECAR_LOG")
    [[ "$_AUTH_VERDICT" == "auth" ]] && _VERDICT="auth-retries-exhausted" || _VERDICT="$_AUTH_VERDICT"
    append_launch_failure "2" "codex-implement" "$LAUNCHER_EXIT" "$SIDECAR_LOG" "$_VERDICT" "$AUTH_ATTEMPT"
fi

MANIFEST_WRITTEN=false
QA_PENDING_WRITTEN=false
[[ -s "$MANIFEST_PATH" ]]   && MANIFEST_WRITTEN=true
[[ -s "$QA_PENDING_PATH" ]] && QA_PENDING_WRITTEN=true

codex_launcher_record_usage_from_events "$PLUGIN_ROOT" "$CODEX_EVENTS" "$SIDECAR_LOG" "codex_implement"
emit_timing_record "$LAUNCHER_EXIT"

emit_kv LAUNCHER_EXIT "$LAUNCHER_EXIT"
emit_kv MANIFEST_WRITTEN "$MANIFEST_WRITTEN"
emit_kv QA_PENDING_WRITTEN "$QA_PENDING_WRITTEN"
emit_kv TRANSCRIPT "$TRANSCRIPT_PATH"
emit_kv SIDECAR_LOG "$SIDECAR_LOG"
exit 0
