#!/usr/bin/env bash
# dispatch-plan-voters.sh - Launch /design plan-review external voters.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"

usage() {
    echo "Usage: dispatch-plan-voters.sh --ballot-file FILE --design-tmpdir DIR --codex-available true|false --cursor-available true|false [--session-env-path FILE]" >&2
}

BALLOT_FILE=""
DESIGN_TMPDIR=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --design-tmpdir) DESIGN_TMPDIR="${2:?--design-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --session-env-path)
            [[ $# -ge 2 ]] || { echo "dispatch-plan-voters.sh: --session-env-path requires a value" >&2; exit 2; }
            SESSION_ENV_PATH="$2"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) echo "dispatch-plan-voters.sh: unknown option: $1" >&2; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" ]] || { echo "dispatch-plan-voters.sh: --ballot-file is required" >&2; exit 2; }
[[ -f "$BALLOT_FILE" ]] || { echo "dispatch-plan-voters.sh: ballot file not found: $BALLOT_FILE" >&2; exit 2; }
[[ -n "$DESIGN_TMPDIR" ]] || { echo "dispatch-plan-voters.sh: --design-tmpdir is required" >&2; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { echo "dispatch-plan-voters.sh: --codex-available must be true or false" >&2; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { echo "dispatch-plan-voters.sh: --cursor-available must be true or false" >&2; exit 2; }
mkdir -p "$DESIGN_TMPDIR"

RUN_EXTERNAL_AGENT="$PLUGIN_ROOT/scripts/run-external-agent.sh"
WAIT_FOR_REVIEWERS="$PLUGIN_ROOT/scripts/wait-for-reviewers.sh"
APPEND_TOOL_FAILURE="$PLUGIN_ROOT/scripts/append-tool-failure.sh"
AGENT_MODEL_ARGS="$PLUGIN_ROOT/scripts/agent-model-args.sh"
CURSOR_AUTH_FLAGS="$PLUGIN_ROOT/scripts/cursor-auth-flags.sh"
CURSOR_WRAP_PROMPT="$PLUGIN_ROOT/scripts/cursor-wrap-prompt.sh"

if [[ ! -x "$RUN_EXTERNAL_AGENT" ]]; then
    echo "dispatch-plan-voters.sh: required wrapper missing or not executable: $RUN_EXTERNAL_AGENT" >&2
    echo "VOTER_2_PATH=''"
    echo "VOTER_3_PATH=''"
    echo "VOTER_2_STATUS=fallback"
    echo "VOTER_3_STATUS=fallback"
    echo "DISPATCH_OK=false"
    exit 2
fi
[[ -x "$WAIT_FOR_REVIEWERS" ]] || { echo "dispatch-plan-voters.sh: required wait helper missing or not executable: $WAIT_FOR_REVIEWERS" >&2; exit 2; }
[[ -x "$AGENT_MODEL_ARGS" ]] || { echo "dispatch-plan-voters.sh: required model helper missing or not executable: $AGENT_MODEL_ARGS" >&2; exit 2; }
[[ -x "$CURSOR_AUTH_FLAGS" ]] || { echo "dispatch-plan-voters.sh: required cursor auth helper missing or not executable: $CURSOR_AUTH_FLAGS" >&2; exit 2; }
[[ -x "$CURSOR_WRAP_PROMPT" ]] || { echo "dispatch-plan-voters.sh: required cursor prompt helper missing or not executable: $CURSOR_WRAP_PROMPT" >&2; exit 2; }

TEMP_PROMPTS=()
PIDS=()
DISPATCH_OK=true
PROMPT_FILE_RESULT=""

cleanup() {
    local pid
    for pid in "${PIDS[@]+"${PIDS[@]}"}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    rm -f "${TEMP_PROMPTS[@]+"${TEMP_PROMPTS[@]}"}"
}
trap cleanup EXIT

execution_issue_log() {
    if [[ -n "${LARCH_EXECUTION_ISSUES_LOG:-}" ]]; then
        printf '%s' "$LARCH_EXECUTION_ISSUES_LOG"
        return
    fi
    if [[ -n "$SESSION_ENV_PATH" ]]; then
        printf '%s/execution-issues.md' "$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        printf '%s/execution-issues.md' "$IMPLEMENT_TMPDIR"
    else
        printf '%s/execution-issues.md' "$DESIGN_TMPDIR"
    fi
}

append_launch_failure() {
    local site="$1" tool="$2" rc="$3" output_file="$4"
    [[ -x "$APPEND_TOOL_FAILURE" ]] || return 0
    "$APPEND_TOOL_FAILURE" \
        --log "$(execution_issue_log)" \
        --site "$site" \
        --tool "$tool" \
        --exit-code "$rc" \
        --category "External Reviewer Issues" \
        --output-file "$output_file" \
        --redact >/dev/null 2>&1 || true
}

make_prompt_file() {
    local tool="$1" prompt_file
    prompt_file=$(mktemp "$DESIGN_TMPDIR/${tool}-plan-voter-prompt.XXXXXX") || {
        echo "dispatch-plan-voters.sh: failed to create prompt file" >&2
        exit 2
    }
    TEMP_PROMPTS+=("$prompt_file")
    {
        printf 'You are a senior engineer on a voting panel deciding which proposed plan modifications should be accepted.\n'
        printf 'Vote EXONERATE, not YES, if the concern is legitimate but the proposed change would introduce more complexity than the issue warrants.\n'
        printf 'Do NOT modify files. Do NOT commit. Do NOT push.\n'
        printf 'Read the ballot from this path: %s\n' "$BALLOT_FILE"
        printf '\nFor each ballot item output exactly one line using the same ID from the ballot:\n'
        printf '  FINDING_N: YES\n'
        printf '  FINDING_N: NO -- one-line reason\n'
        printf '  FINDING_N: EXONERATE -- one-line reason\n'
        printf 'For OOS_N items: YES means file a GitHub issue; NO or EXONERATE means skip.\n'
    } > "$prompt_file"
    PROMPT_FILE_RESULT="$prompt_file"
}

read_model_args() {
    local tool="$1" out_file="$2" log_file="$3"
    "$AGENT_MODEL_ARGS" --tool "$tool" --with-effort > "$out_file" 2>> "$log_file"
}

launch_codex_voter() {
    local out="$1" prompt_file="$2" launch_log="$DESIGN_TMPDIR/dispatch-codex-plan-voter.log"
    local model_args_tmp prompt_text rc
    local codex_model_args=()
    : > "$launch_log"
    model_args_tmp=$(mktemp "$DESIGN_TMPDIR/codex-model-args.XXXXXX") || exit 2

    set +e
    read_model_args codex "$model_args_tmp" "$launch_log"
    rc=$?
    if [[ "$rc" -eq 0 ]]; then
        while IFS= read -r arg; do codex_model_args+=("$arg"); done < "$model_args_tmp"
        prompt_text=$(cat "$prompt_file")
        "$RUN_EXTERNAL_AGENT" --tool codex --output "$out" --timeout 1200 -- \
            codex exec --full-auto -C "$PWD" --add-dir "$DESIGN_TMPDIR" "${codex_model_args[@]+"${codex_model_args[@]}"}" \
                --output-last-message "$out" \
                "$prompt_text" >> "$launch_log" 2>&1
        rc=$?
    fi
    set -e

    rm -f "$model_args_tmp"
    if [[ "$rc" -ne 0 ]]; then
        [[ -f "$out.done" ]] || printf '%s\n' "$rc" > "$out.done"
        append_launch_failure "design Step 3" "run-external-agent.sh codex plan voter" "$rc" "$launch_log"
    fi
    exit "$rc"
}

launch_cursor_voter() {
    local out="$1" prompt_file="$2" launch_log="$DESIGN_TMPDIR/dispatch-cursor-plan-voter.log"
    local model_args_tmp auth_args_tmp prompt_text wrapped_prompt rc
    local cursor_model_args=()
    local cursor_auth_args=()
    : > "$launch_log"
    model_args_tmp=$(mktemp "$DESIGN_TMPDIR/cursor-model-args.XXXXXX") || exit 2
    auth_args_tmp=$(mktemp "$DESIGN_TMPDIR/cursor-auth-args.XXXXXX") || exit 2

    set +e
    read_model_args cursor "$model_args_tmp" "$launch_log"
    rc=$?
    if [[ "$rc" -eq 0 ]]; then
        "$CURSOR_AUTH_FLAGS" > "$auth_args_tmp" 2>> "$launch_log"
        rc=$?
    fi
    if [[ "$rc" -eq 0 ]]; then
        while IFS= read -r arg; do cursor_model_args+=("$arg"); done < "$model_args_tmp"
        while IFS= read -r arg; do cursor_auth_args+=("$arg"); done < "$auth_args_tmp"
        prompt_text=$(cat "$prompt_file")
        wrapped_prompt=$("$CURSOR_WRAP_PROMPT" "$prompt_text")
        rc=$?
    fi
    if [[ "$rc" -eq 0 ]]; then
        "$RUN_EXTERNAL_AGENT" --tool cursor --output "$out" --timeout 1200 --capture-stdout -- \
            cursor agent -p --trust --mode plan "${cursor_model_args[@]+"${cursor_model_args[@]}"}" "${cursor_auth_args[@]+"${cursor_auth_args[@]}"}" --workspace "$PWD" \
                "$wrapped_prompt" >> "$launch_log" 2>&1
        rc=$?
    fi
    set -e

    rm -f "$model_args_tmp" "$auth_args_tmp"
    if [[ "$rc" -ne 0 ]]; then
        [[ -f "$out.done" ]] || printf '%s\n' "$rc" > "$out.done"
        append_launch_failure "design Step 3" "run-external-agent.sh cursor plan voter" "$rc" "$launch_log"
    fi
    exit "$rc"
}

wait_for_launched_voters() {
    local wait_stdout="$DESIGN_TMPDIR/dispatch-plan-voters-wait.stdout"
    local wait_stderr="$DESIGN_TMPDIR/dispatch-plan-voters-wait.stderr"
    local wait_log="$DESIGN_TMPDIR/dispatch-plan-voters-wait.log"
    local rc line timed_out=false exit_code pid

    [[ $# -gt 0 ]] || return 0

    set +e
    "$WAIT_FOR_REVIEWERS" --timeout 1260 "$@" > "$wait_stdout" 2> "$wait_stderr"
    rc=$?
    set -e
    {
        printf '%s\n' '--- stdout ---'
        cat "$wait_stdout"
        printf '%s\n' '--- stderr ---'
        cat "$wait_stderr"
    } > "$wait_log"

    if [[ "$rc" -ne 0 ]]; then
        DISPATCH_OK=false
        append_launch_failure "design Step 3" "wait-for-reviewers.sh plan voters" "$rc" "$wait_log"
    fi

    while IFS= read -r line; do
        case "$line" in
            TIMEOUT\ *)
                DISPATCH_OK=false
                timed_out=true
                append_launch_failure "design Step 3" "wait-for-reviewers.sh plan voters" 124 "$wait_log"
                ;;
            DONE\ *exit=*)
                exit_code="${line##*exit=}"
                case "$exit_code" in
                    0) ;;
                    ''|*[!0-9]*) DISPATCH_OK=false ;;
                    *) DISPATCH_OK=false ;;
                esac
                ;;
        esac
    done < "$wait_stdout"

    if [[ "$timed_out" == "true" ]]; then
        for pid in "${PIDS[@]+"${PIDS[@]}"}"; do
            kill "$pid" 2>/dev/null || true
        done
    fi

    for pid in "${PIDS[@]+"${PIDS[@]}"}"; do
        wait "$pid" || true
    done
    PIDS=()
}

VOTER_2_PATH=""
VOTER_3_PATH=""
VOTER_2_STATUS="fallback"
VOTER_3_STATUS="fallback"
VOTER_2_SENTINEL_IDX=0
VOTER_3_SENTINEL_IDX=0
SENTINELS=()

if [[ "$CODEX_AVAILABLE" == "true" ]]; then
    VOTER_2_PATH="$DESIGN_TMPDIR/codex-vote-output.txt"
    VOTER_2_STATUS="launched"
    make_prompt_file codex
    codex_prompt_file="$PROMPT_FILE_RESULT"
    ( trap - EXIT; launch_codex_voter "$VOTER_2_PATH" "$codex_prompt_file" ) &
    PIDS+=("$!")
    SENTINELS+=("$VOTER_2_PATH.done")
    VOTER_2_SENTINEL_IDX=${#SENTINELS[@]}
fi

if [[ "$CURSOR_AVAILABLE" == "true" ]]; then
    VOTER_3_PATH="$DESIGN_TMPDIR/cursor-vote-output.txt"
    VOTER_3_STATUS="launched"
    make_prompt_file cursor
    cursor_prompt_file="$PROMPT_FILE_RESULT"
    ( trap - EXIT; launch_cursor_voter "$VOTER_3_PATH" "$cursor_prompt_file" ) &
    PIDS+=("$!")
    SENTINELS+=("$VOTER_3_PATH.done")
    VOTER_3_SENTINEL_IDX=${#SENTINELS[@]}
fi

wait_for_launched_voters "${SENTINELS[@]+"${SENTINELS[@]}"}"

# Update per-voter status based on wait outcomes (timeout or non-zero exit).
WAIT_STDOUT="$DESIGN_TMPDIR/dispatch-plan-voters-wait.stdout"
if [[ -f "$WAIT_STDOUT" ]]; then
    while IFS= read -r _wline; do
        _wid="${_wline#* }" ; _wid="${_wid%% *}"
        case "$_wline" in
            TIMEOUT\ *)
                [[ "$VOTER_2_SENTINEL_IDX" -gt 0 && "$_wid" == "$VOTER_2_SENTINEL_IDX" ]] && VOTER_2_STATUS="failed"
                [[ "$VOTER_3_SENTINEL_IDX" -gt 0 && "$_wid" == "$VOTER_3_SENTINEL_IDX" ]] && VOTER_3_STATUS="failed"
                ;;
            DONE\ *exit=*)
                _wec="${_wline##*exit=}"
                if [[ "$_wec" != "0" && -n "$_wec" ]]; then
                    [[ "$VOTER_2_SENTINEL_IDX" -gt 0 && "$_wid" == "$VOTER_2_SENTINEL_IDX" ]] && VOTER_2_STATUS="failed"
                    [[ "$VOTER_3_SENTINEL_IDX" -gt 0 && "$_wid" == "$VOTER_3_SENTINEL_IDX" ]] && VOTER_3_STATUS="failed"
                fi
                ;;
        esac
    done < "$WAIT_STDOUT"
fi

printf 'VOTER_2_PATH=%q\n' "$VOTER_2_PATH"
printf 'VOTER_3_PATH=%q\n' "$VOTER_3_PATH"
printf 'VOTER_2_STATUS=%s\n' "$VOTER_2_STATUS"
printf 'VOTER_3_STATUS=%s\n' "$VOTER_3_STATUS"
printf 'DISPATCH_OK=%s\n' "$DISPATCH_OK"
