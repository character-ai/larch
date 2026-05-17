#!/usr/bin/env bash
# dispatch-code-voters.sh — Launch /review code-review judge panel: 3 voters
# (Claude + Codex + Cursor) with Claude replacement when an external voter
# is unhealthy. Mirrors scripts/dispatch-plan-voters.sh's structure but adds
# the always-present Claude voter and the per-vendor Claude replacement path.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: dispatch-code-voters.sh --ballot-file FILE --review-tmpdir DIR --codex-available true|false --cursor-available true|false [--session-env-path FILE] [--diff-file FILE] [--plan-file FILE]"
}

BALLOT_FILE=""
REVIEW_TMPDIR=""
CODEX_AVAILABLE=""
CURSOR_AVAILABLE=""
SESSION_ENV_PATH="${SESSION_ENV_PATH:-}"
DIFF_FILE=""
PLAN_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ballot-file) BALLOT_FILE="${2:?--ballot-file requires a value}"; shift 2 ;;
        --review-tmpdir) REVIEW_TMPDIR="${2:?--review-tmpdir requires a value}"; shift 2 ;;
        --codex-available) CODEX_AVAILABLE="${2:?--codex-available requires a value}"; shift 2 ;;
        --cursor-available) CURSOR_AVAILABLE="${2:?--cursor-available requires a value}"; shift 2 ;;
        --session-env-path) SESSION_ENV_PATH="${2:?--session-env-path requires a value}"; shift 2 ;;
        --diff-file) DIFF_FILE="${2:?--diff-file requires a value}"; shift 2 ;;
        --plan-file) PLAN_FILE="${2:?--plan-file requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "dispatch-code-voters.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ -n "$BALLOT_FILE" && -f "$BALLOT_FILE" ]] || { larch_err "dispatch-code-voters.sh: --ballot-file must name a file"; exit 2; }
[[ -n "$REVIEW_TMPDIR" ]] || { larch_err "dispatch-code-voters.sh: --review-tmpdir is required"; exit 2; }
[[ "$CODEX_AVAILABLE" == "true" || "$CODEX_AVAILABLE" == "false" ]] || { larch_err "dispatch-code-voters.sh: --codex-available must be true or false"; exit 2; }
[[ "$CURSOR_AVAILABLE" == "true" || "$CURSOR_AVAILABLE" == "false" ]] || { larch_err "dispatch-code-voters.sh: --cursor-available must be true or false"; exit 2; }
mkdir -p "$REVIEW_TMPDIR"

RUN_EXTERNAL_AGENT="$PLUGIN_ROOT/scripts/run-external-agent.sh"
LAUNCH_CLAUDE_SUBPROCESS="$PLUGIN_ROOT/scripts/launch-claude-subprocess.sh"
WAIT_FOR_REVIEWERS="$PLUGIN_ROOT/scripts/wait-for-reviewers.sh"
APPEND_TOOL_FAILURE="$PLUGIN_ROOT/scripts/append-tool-failure.sh"
AGENT_MODEL_ARGS="$PLUGIN_ROOT/scripts/agent-model-args.sh"
CURSOR_AUTH_FLAGS="$PLUGIN_ROOT/scripts/cursor-auth-flags.sh"
CURSOR_WRAP_PROMPT="$PLUGIN_ROOT/scripts/cursor-wrap-prompt.sh"

[[ -x "$RUN_EXTERNAL_AGENT" ]] || { larch_err "dispatch-code-voters.sh: missing $RUN_EXTERNAL_AGENT"; exit 2; }
[[ -x "$LAUNCH_CLAUDE_SUBPROCESS" ]] || { larch_err "dispatch-code-voters.sh: missing $LAUNCH_CLAUDE_SUBPROCESS"; exit 2; }
[[ -x "$WAIT_FOR_REVIEWERS" ]] || { larch_err "dispatch-code-voters.sh: missing $WAIT_FOR_REVIEWERS"; exit 2; }
[[ -x "$AGENT_MODEL_ARGS" ]] || { larch_err "dispatch-code-voters.sh: missing $AGENT_MODEL_ARGS"; exit 2; }
[[ -x "$CURSOR_AUTH_FLAGS" ]] || { larch_err "dispatch-code-voters.sh: missing $CURSOR_AUTH_FLAGS"; exit 2; }
[[ -x "$CURSOR_WRAP_PROMPT" ]] || { larch_err "dispatch-code-voters.sh: missing $CURSOR_WRAP_PROMPT"; exit 2; }

TEMP_PROMPTS=()
PIDS=()
DISPATCH_OK=true

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
        printf '%s' "$LARCH_EXECUTION_ISSUES_LOG"; return
    fi
    if [[ -n "$SESSION_ENV_PATH" ]]; then
        printf '%s/execution-issues.md' "$(dirname "$SESSION_ENV_PATH")"
    elif [[ -n "${IMPLEMENT_TMPDIR:-}" ]]; then
        printf '%s/execution-issues.md' "$IMPLEMENT_TMPDIR"
    else
        printf '%s/execution-issues.md' "$REVIEW_TMPDIR"
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

make_voter_prompt_file() {
    local label="$1" prompt_file
    prompt_file=$(mktemp "$REVIEW_TMPDIR/${label}-vote-prompt.XXXXXX") || {
        larch_err "dispatch-code-voters.sh: failed to create prompt file"; exit 2
    }
    TEMP_PROMPTS+=("$prompt_file")
    {
        printf 'You are a scrupulous senior code reviewer on a 3-judge voting panel deciding which proposed code-review findings should be accepted.\n'
        printf 'Vote EXONERATE rather than YES when the concern is legitimate but the proposed change introduces more complexity than it warrants.\n'
        printf 'For items prefixed with [OUT_OF_SCOPE]: YES means file a GitHub issue for future tracking; NO means trivial/incorrect; EXONERATE means legitimate but not issue-worthy.\n'
        printf 'Do NOT modify files. Do NOT commit. Do NOT push.\n'
        printf '\nRead the ballot from this path: %s\n' "$BALLOT_FILE"
        printf '\nFor every ballot item, output exactly one line using the same FINDING_N: id from the ballot heading:\n'
        printf '  FINDING_N: YES\n'
        printf '  FINDING_N: NO -- one-line reason\n'
        printf '  FINDING_N: EXONERATE -- one-line reason\n'
        printf 'You must vote on every item. Do NOT skip any.\n'
    } > "$prompt_file"
    printf '%s' "$prompt_file"
}

launch_codex_voter() {
    local out="$1" prompt_file="$2" launch_log="$REVIEW_TMPDIR/dispatch-codex-vote.log"
    local model_args_tmp prompt_text rc
    local codex_model_args=()
    : > "$launch_log"
    model_args_tmp=$(mktemp "$REVIEW_TMPDIR/codex-vote-model-args.XXXXXX") || exit 2

    set +e
    "$AGENT_MODEL_ARGS" --tool codex --with-effort > "$model_args_tmp" 2>> "$launch_log"
    rc=$?
    if [[ "$rc" -eq 0 ]]; then
        while IFS= read -r arg; do codex_model_args+=("$arg"); done < "$model_args_tmp"
        prompt_text=$(cat "$prompt_file")
        "$RUN_EXTERNAL_AGENT" --tool codex --output "$out" --timeout 1200 -- \
            codex exec --full-auto -C "$PWD" --add-dir "$REVIEW_TMPDIR" "${codex_model_args[@]+"${codex_model_args[@]}"}" \
                --output-last-message "$out" \
                "$prompt_text" >> "$launch_log" 2>&1
        rc=$?
    fi
    set -e

    rm -f "$model_args_tmp"
    if [[ "$rc" -ne 0 ]]; then
        [[ -f "$out.done" ]] || printf '%s\n' "$rc" > "$out.done"
        append_launch_failure "review Step 3 vote" "run-external-agent.sh codex code voter" "$rc" "$launch_log"
    fi
    exit "$rc"
}

launch_cursor_voter() {
    local out="$1" prompt_file="$2" launch_log="$REVIEW_TMPDIR/dispatch-cursor-vote.log"
    local model_args_tmp auth_args_tmp prompt_text wrapped_prompt rc
    local cursor_model_args=()
    local cursor_auth_args=()
    : > "$launch_log"
    model_args_tmp=$(mktemp "$REVIEW_TMPDIR/cursor-vote-model-args.XXXXXX") || exit 2
    auth_args_tmp=$(mktemp "$REVIEW_TMPDIR/cursor-vote-auth-args.XXXXXX") || exit 2

    set +e
    "$AGENT_MODEL_ARGS" --tool cursor --with-effort > "$model_args_tmp" 2>> "$launch_log"
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
        append_launch_failure "review Step 3 vote" "run-external-agent.sh cursor code voter" "$rc" "$launch_log"
    fi
    exit "$rc"
}

launch_claude_voter() {
    local out="$1" prompt_file="$2" launch_log="$REVIEW_TMPDIR/dispatch-claude-vote.log"
    local rc
    : > "$launch_log"
    set +e
    local ctx_args=() allow_root_args=()
    [[ -n "$DIFF_FILE" && -f "$DIFF_FILE" ]] && ctx_args+=(--context-files "$DIFF_FILE") && allow_root_args+=(--allow-root "$(dirname "$DIFF_FILE")")
    [[ -n "$PLAN_FILE" && -f "$PLAN_FILE" ]] && ctx_args+=(--context-files "$PLAN_FILE")
    "$LAUNCH_CLAUDE_SUBPROCESS" \
        --model claude-opus-4-7 \
        --prompt-file "$prompt_file" \
        --output-file "$out" \
        --timeout 1200 \
        --timing-task-kind claude-code-voter \
        ${allow_root_args[@]+"${allow_root_args[@]}"} \
        ${ctx_args[@]+"${ctx_args[@]}"} >> "$launch_log" 2>&1
    rc=$?
    set -e
    # launch-claude-subprocess.sh writes the output file directly; create the
    # sentinel that wait-for-reviewers.sh polls for parity with the external
    # agents.
    if [[ "$rc" -eq 0 && -s "$out" ]]; then
        printf '0\n' > "$out.done"
    else
        printf '%s\n' "$rc" > "$out.done"
        append_launch_failure "review Step 3 vote" "launch-claude-subprocess.sh claude code voter" "$rc" "$launch_log"
    fi
    exit "$rc"
}

wait_for_launched_voters() {
    local wait_stdout="$REVIEW_TMPDIR/dispatch-code-voters-wait.stdout"
    local wait_stderr="$REVIEW_TMPDIR/dispatch-code-voters-wait.stderr"
    local wait_log="$REVIEW_TMPDIR/dispatch-code-voters-wait.log"
    local rc pid

    [[ $# -gt 0 ]] || return 0

    set +e
    "$WAIT_FOR_REVIEWERS" --timeout 1260 "$@" > "$wait_stdout" 2> "$wait_stderr"
    rc=$?
    set -e
    {
        printf '%s\n' '--- stdout ---'; cat "$wait_stdout"
        printf '%s\n' '--- stderr ---'; cat "$wait_stderr"
    } > "$wait_log"

    if [[ "$rc" -ne 0 ]]; then
        DISPATCH_OK=false
        append_launch_failure "review Step 3 vote" "wait-for-reviewers.sh code voters" "$rc" "$wait_log"
    fi

    for pid in "${PIDS[@]+"${PIDS[@]}"}"; do
        wait "$pid" || true
    done
    PIDS=()
}

# Voter slot semantics:
#   VOTER_1 = Claude (always launched; primary judge for the Anthropic side)
#   VOTER_2 = Codex (when codex_available=true) OR Claude replacement
#   VOTER_3 = Cursor (when cursor_available=true) OR Claude replacement
# When an external vendor is unhealthy, a Claude voter is launched in its
# place so the panel always has 3 voters.

VOTER_1_PATH="$REVIEW_TMPDIR/claude-vote-output.txt"
VOTER_1_TOOL="claude"
VOTER_1_STATUS="launched"
VOTER_2_PATH=""
VOTER_2_TOOL=""
VOTER_2_STATUS=""
VOTER_3_PATH=""
VOTER_3_TOOL=""
VOTER_3_STATUS=""
SENTINELS=()

# Voter 1: Claude (always)
claude_prompt_file=$(make_voter_prompt_file claude)
( trap - EXIT; launch_claude_voter "$VOTER_1_PATH" "$claude_prompt_file" ) &
PIDS+=("$!")
SENTINELS+=("$VOTER_1_PATH.done")

# Voter 2: Codex or Claude replacement
if [[ "$CODEX_AVAILABLE" == "true" ]]; then
    VOTER_2_PATH="$REVIEW_TMPDIR/codex-vote-output.txt"
    VOTER_2_TOOL="codex"
    VOTER_2_STATUS="launched"
    codex_prompt_file=$(make_voter_prompt_file codex)
    ( trap - EXIT; launch_codex_voter "$VOTER_2_PATH" "$codex_prompt_file" ) &
    PIDS+=("$!")
    SENTINELS+=("$VOTER_2_PATH.done")
else
    VOTER_2_PATH="$REVIEW_TMPDIR/claude-replacement-codex-vote-output.txt"
    VOTER_2_TOOL="claude"
    VOTER_2_STATUS="fallback"
    rep2_prompt_file=$(make_voter_prompt_file claude-replacement-codex)
    ( trap - EXIT; launch_claude_voter "$VOTER_2_PATH" "$rep2_prompt_file" ) &
    PIDS+=("$!")
    SENTINELS+=("$VOTER_2_PATH.done")
fi

# Voter 3: Cursor or Claude replacement
if [[ "$CURSOR_AVAILABLE" == "true" ]]; then
    VOTER_3_PATH="$REVIEW_TMPDIR/cursor-vote-output.txt"
    VOTER_3_TOOL="cursor"
    VOTER_3_STATUS="launched"
    cursor_prompt_file=$(make_voter_prompt_file cursor)
    ( trap - EXIT; launch_cursor_voter "$VOTER_3_PATH" "$cursor_prompt_file" ) &
    PIDS+=("$!")
    SENTINELS+=("$VOTER_3_PATH.done")
else
    VOTER_3_PATH="$REVIEW_TMPDIR/claude-replacement-cursor-vote-output.txt"
    VOTER_3_TOOL="claude"
    VOTER_3_STATUS="fallback"
    rep3_prompt_file=$(make_voter_prompt_file claude-replacement-cursor)
    ( trap - EXIT; launch_claude_voter "$VOTER_3_PATH" "$rep3_prompt_file" ) &
    PIDS+=("$!")
    SENTINELS+=("$VOTER_3_PATH.done")
fi

wait_for_launched_voters "${SENTINELS[@]+"${SENTINELS[@]}"}"

# Update per-voter status from the wait output: if a sentinel reports a non-zero
# exit code, mark that voter as failed.
mark_failed_if_nonzero_exit() {
    local sentinel="$1" varname="$2" exit_code
    if [[ -f "$sentinel" ]]; then
        exit_code=$(head -n1 "$sentinel" | tr -d '[:space:]')
        if [[ -n "$exit_code" && "$exit_code" != "0" ]]; then
            eval "$varname=failed"
            DISPATCH_OK=false
        fi
    else
        eval "$varname=failed"
        DISPATCH_OK=false
    fi
    # Also fail if the voter output file is missing or empty.
    local out_var="${varname%_STATUS}_PATH"
    local out_path="${!out_var:-}"
    if [[ -n "$out_path" ]] && { [[ ! -f "$out_path" ]] || [[ ! -s "$out_path" ]]; }; then
        eval "$varname=failed"
        DISPATCH_OK=false
    fi
}

mark_failed_if_nonzero_exit "$VOTER_1_PATH.done" VOTER_1_STATUS
mark_failed_if_nonzero_exit "$VOTER_2_PATH.done" VOTER_2_STATUS
mark_failed_if_nonzero_exit "$VOTER_3_PATH.done" VOTER_3_STATUS

effective_judges=0
judge_list=()
missing_reasons=()
for _slot_info in "VOTER_1:$VOTER_1_STATUS:$VOTER_1_PATH:$VOTER_1_TOOL" \
                  "VOTER_2:$VOTER_2_STATUS:$VOTER_2_PATH:$VOTER_2_TOOL" \
                  "VOTER_3:$VOTER_3_STATUS:$VOTER_3_PATH:$VOTER_3_TOOL"; do
    _slot="${_slot_info%%:*}"
    _rest="${_slot_info#*:}"
    _vstatus="${_rest%%:*}"
    _vrest="${_rest#*:}"
    _vpath="${_vrest%%:*}"
    _vtool="${_vrest##*:}"
    if [[ "$_vstatus" != "failed" && -n "$_vpath" && -s "$_vpath" ]]; then
        effective_judges=$((effective_judges + 1))
        judge_list+=("$_vtool")
    else
        missing_reasons+=("$_slot(${_vstatus:-unknown})")
    fi
done

if (( effective_judges < 3 )); then
    case "$effective_judges" in
        2) _tier_label="unanimous-2" ;;
        1) _tier_label="single-judge" ;;
        *) _tier_label="main-agent-required" ;;
    esac
    if [[ "${#judge_list[@]}" -gt 0 ]]; then
        _judge_list_str="${judge_list[*]}"
    else
        _judge_list_str="none"
    fi
    if [[ "${#missing_reasons[@]}" -gt 0 ]]; then
        _missing_str="${missing_reasons[*]}"
    else
        _missing_str="none"
    fi
    _warn_msg="**⚠ Degraded code-review panel: ${effective_judges}/3 effective judges. Judges: ${_judge_list_str// /,}. Missing: ${_missing_str// /,}. Accept rule: ${_tier_label}.**"
    larch_err "$_warn_msg"
    emit_kv DEGRADED_PANEL_WARNING "$_warn_msg"
fi

emit_kv VOTER_1_PATH "$VOTER_1_PATH"
emit_kv VOTER_1_TOOL "$VOTER_1_TOOL"
emit_kv VOTER_1_STATUS "$VOTER_1_STATUS"
emit_kv VOTER_2_PATH "$VOTER_2_PATH"
emit_kv VOTER_2_TOOL "$VOTER_2_TOOL"
emit_kv VOTER_2_STATUS "$VOTER_2_STATUS"
emit_kv VOTER_3_PATH "$VOTER_3_PATH"
emit_kv VOTER_3_TOOL "$VOTER_3_TOOL"
emit_kv VOTER_3_STATUS "$VOTER_3_STATUS"
emit_kv DISPATCH_OK "$DISPATCH_OK"
