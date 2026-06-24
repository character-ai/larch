#!/usr/bin/env bash
# design-step3-mav.sh — /design Step 3 MainAgent vote/re-tally wrapper.
# shellcheck disable=SC1091,SC2034

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
SESSION_ENV_PATH=""
CLAUDE_PID=""
PHASE=""

DESIGN_TMPDIR="${DESIGN_TMPDIR:-}"
ISSUE_NUMBER="${ISSUE_NUMBER:-}"
REPO="${REPO:-}"
STEP3_REVIEW_LOOP_STATUS="${STEP3_REVIEW_LOOP_STATUS:-}"
LOOP_STATUS="${LOOP_STATUS:-}"
TALLY_PLAN_REVIEW_STATUS="${TALLY_PLAN_REVIEW_STATUS:-}"
SCOPE_ANCHOR_FILE="${SCOPE_ANCHOR_FILE:-}"
STEP3_REVIEW_ROUND_NUM="${STEP3_REVIEW_ROUND_NUM:-}"
ROUND_NUM="${ROUND_NUM:-}"
ROUNDS_COMPLETED="${ROUNDS_COMPLETED:-}"
REVIEW_ROUND_COUNT="${REVIEW_ROUND_COUNT:-}"
FINAL_ROUND_NUM="${FINAL_ROUND_NUM:-}"
ACCEPTED_COUNT="${ACCEPTED_COUNT:-}"
IMPORTANT_ACCEPTED_COUNT="${IMPORTANT_ACCEPTED_COUNT:-}"

usage() {
    printf '%s\n' 'usage: design-step3-mav.sh --phase pre|post --session-env-path PATH --claude-pid PID --plugin-root PATH' >&2
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --session-env-path)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            SESSION_ENV_PATH="$2"
            shift 2
            ;;
        --claude-pid)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            CLAUDE_PID="$2"
            shift 2
            ;;
        --plugin-root)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            CLAUDE_PLUGIN_ROOT="$2"
            shift 2
            ;;
        --phase)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            PHASE="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            printf '%s\n' "design-step3-mav.sh: unknown argument: $1" >&2
            usage
            exit 2
            ;;
    esac
done

case "$PHASE" in
    pre|post) ;;
    *) usage; exit 2 ;;
esac

_cpr_literal='$''{CLAUDE_PLUGIN_ROOT}'
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ] || [ "${CLAUDE_PLUGIN_ROOT:-}" = "$_cpr_literal" ]; then
    printf '%s\n' '/design Step 3 MAV: CLAUDE_PLUGIN_ROOT required' >&2
    exit 1
fi
export CLAUDE_PLUGIN_ROOT

if [ -n "${SESSION_ENV_PATH:-}" ] && [ -f "$SESSION_ENV_PATH" ]; then
    # shellcheck source=/dev/null
    . "$SESSION_ENV_PATH"
fi

emit() { printf '%s\n' "$*"; }
emit_kv() {
    local key=$1 value=${2-}
    case "$value" in *$'\n'*|*$'\r'*) larch_err "emit_kv: value for key ${key} must not contain newline or carriage return"; return 2 ;; esac
    printf '%s=%s\n' "$key" "$value"
}
larch_err() { printf '%s\n' "$*" >&2; }
sanitize_diagnostic_line() { LC_ALL=C tr -d '[:cntrl:]'; }
larch_quiet_init() { :; }

if [ -z "${DESIGN_TMPDIR:-}" ] || [ ! -d "$DESIGN_TMPDIR" ]; then
    larch_err '/design Step 3 MAV: DESIGN_TMPDIR required'
    exit 1
fi
DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR" && pwd -P)"
python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" session validate-design-tmpdir "$DESIGN_TMPDIR" || exit 2
larch_quiet_init

if [ -f "$DESIGN_TMPDIR/.pause-requested" ]; then
    exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design pause-save \
        --design-tmpdir "$DESIGN_TMPDIR" \
        --issue "$ISSUE_NUMBER" \
        ${REPO:+--repo "$REPO"}
fi

safe_env_tmp=""
cleanup_safe_env() {
    [ -z "${safe_env_tmp:-}" ] || rm -f "$safe_env_tmp" 2>/dev/null || true
}
trap cleanup_safe_env EXIT HUP INT TERM

read_one_result_env() {
    local path="$1"
    local optional="$2"
    if [ -L "$path" ]; then
        :
    elif [ ! -e "$path" ]; then
        [ "$optional" = true ] && return 0
        return 1
    fi
    safe_env_tmp="$(mktemp "${TMPDIR:-/tmp}/larch-step3-mav-env.XXXXXX")" || return 1
    "$CLAUDE_PLUGIN_ROOT/scripts/read-result-env.sh" \
        --input "$path" \
        --allow LOOP_STATUS \
        --allow STEP3_REVIEW_LOOP_STATUS \
        --allow TALLY_PLAN_REVIEW_STATUS \
        --allow ACCEPTED_COUNT \
        --allow IMPORTANT_ACCEPTED_COUNT \
        --allow SCOPE_ANCHOR_FILE \
        --allow STEP3_REVIEW_ROUND_NUM \
        --allow ROUND_NUM \
        --allow ROUNDS_COMPLETED \
        --allow REVIEW_ROUND_COUNT \
        --allow FINAL_ROUND_NUM \
        --output "$safe_env_tmp" || return 1
    # shellcheck source=/dev/null
    . "$safe_env_tmp"
    rm -f "$safe_env_tmp"
    safe_env_tmp=""
}

read_step3_result_state() {
    read_one_result_env "$DESIGN_TMPDIR/.step3-plan-review-result.env" true || return 1
    read_one_result_env "$DESIGN_TMPDIR/.step3-review-result.env" true || return 1
}

is_positive_int() {
    case "$1" in
        ''|*[!0-9]*) return 1 ;;
    esac
    [ "$((10#$1))" -gt 0 ]
}

resolve_artifact_round() {
    if is_positive_int "${ROUND_NUM:-}"; then
        printf '%s\n' "$((10#$ROUND_NUM))"
    elif is_positive_int "${ROUNDS_COMPLETED:-}"; then
        printf '%s\n' "$((10#$ROUNDS_COMPLETED))"
    elif is_positive_int "${STEP3_REVIEW_ROUND_NUM:-}"; then
        printf '%s\n' "$((10#$STEP3_REVIEW_ROUND_NUM))"
    elif is_positive_int "${REVIEW_ROUND_COUNT:-}"; then
        printf '%s\n' "$((10#$REVIEW_ROUND_COUNT))"
    else
        printf '%s\n' '1'
    fi
}

resolve_resume_round() {
    if is_positive_int "${FINAL_ROUND_NUM:-}"; then
        printf '%s\n' "$((10#$FINAL_ROUND_NUM))"
    elif is_positive_int "${STEP3_REVIEW_ROUND_NUM:-}"; then
        printf '%s\n' "$((10#$STEP3_REVIEW_ROUND_NUM))"
    elif is_positive_int "${ROUND_NUM:-}"; then
        printf '%s\n' "$((10#$ROUND_NUM))"
    elif is_positive_int "${ROUNDS_COMPLETED:-}"; then
        printf '%s\n' "$((10#$ROUNDS_COMPLETED))"
    elif is_positive_int "${REVIEW_ROUND_COUNT:-}"; then
        printf '%s\n' "$((10#$REVIEW_ROUND_COUNT))"
    else
        printf '%s\n' ''
    fi
}

emit_kv_section_begin() {
    emit 'DESIGN_STEP3_MAV_KV_BEGIN'
}

emit_kv_section_end() {
    emit 'DESIGN_STEP3_MAV_KV_END'
}

count_accepted_findings() {
    local accepted_file="$DESIGN_TMPDIR/accepted-plan-findings.md"
    if [ ! -s "$accepted_file" ]; then
        printf '%s\n' '0'
        return 0
    fi
    grep -cE '^### FINDING_[0-9]+:' "$accepted_file" 2>/dev/null || true
}

append_mav_warning_once() {
    local artifact_round="$1"
    local warning_file="$DESIGN_TMPDIR/step3-main-agent-adjudication-r${artifact_round}.warning.log"
    local sentinel="$DESIGN_TMPDIR/.step3-main-agent-adjudication-warning-appended-r${artifact_round}"
    [ ! -f "$sentinel" ] || return 0
    printf '%s\n' 'Step 3 — 0-judge plan-review panel: main-agent adjudication performed' >"$warning_file"
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" run-log append-failure \
        --log "$DESIGN_TMPDIR/execution-issues.md" \
        --site 'design Step 3' \
        --tool 'MainAgent plan-review adjudication' \
        --exit-code 0 \
        --category Warnings \
        --output-file "$warning_file" \
        --redact >/dev/null 2>&1 || true
    : >"$sentinel"
}

run_pre_phase() {
    read_step3_result_state || {
        larch_err '**⚠ Step 3 MAV: could not read Step 3 result env**'
        exit 1
    }
    local ballot_path="$DESIGN_TMPDIR/ballot.txt"
    local resume_round
    resume_round="$(resolve_resume_round)"
    if [ -n "${SCOPE_ANCHOR_FILE:-}" ]; then
        emit '## MainAgent scope anchor evidence'
        set +e
        _scope_render_out="$(python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" render scope-anchor \
            --scope-anchor-file "$SCOPE_ANCHOR_FILE" \
            --design-tmpdir "$DESIGN_TMPDIR" 2>"$DESIGN_TMPDIR/step3-mav-scope-anchor.err")"
        _scope_render_rc=$?
        set -e
        if [ "${_scope_render_rc:-0}" -ne 0 ]; then
            while IFS= read -r _err_line || [ -n "$_err_line" ]; do larch_err "$(printf '%s' "$_err_line" | sanitize_diagnostic_line)"; done < "$DESIGN_TMPDIR/step3-mav-scope-anchor.err" 2>/dev/null || true
            exit "$_scope_render_rc"
        fi
        while IFS= read -r _scope_line || [ -n "$_scope_line" ]; do
            emit "SCOPE_ANCHOR_EVIDENCE: $_scope_line"
        done <<<"${_scope_render_out:-}"
    fi
    emit_kv_section_begin
    emit_kv BALLOT_PATH "$ballot_path"
    [ -z "${SCOPE_ANCHOR_FILE:-}" ] || emit_kv SCOPE_ANCHOR_FILE "$SCOPE_ANCHOR_FILE"
    [ -z "${TALLY_PLAN_REVIEW_STATUS:-}" ] || emit_kv TALLY_PLAN_REVIEW_STATUS "$TALLY_PLAN_REVIEW_STATUS"
    [ -z "${STEP3_REVIEW_LOOP_STATUS:-}" ] || emit_kv STEP3_REVIEW_LOOP_STATUS "$STEP3_REVIEW_LOOP_STATUS"
    [ -z "$resume_round" ] || emit_kv STEP3_RESUME_ROUND "$resume_round"
    emit_kv_section_end
}

run_post_phase() {
    read_step3_result_state || {
        larch_err '**⚠ Step 3 MAV: could not read Step 3 result env**'
        exit 1
    }
    local loop_mode=false artifact_round resume_round retally_input_anchor phase_file phase="unchanged"
    local retally_stdout retally_rc retally_status accepted_count round_start_s end_s
    if [ -n "${STEP3_REVIEW_LOOP_STATUS:-}" ]; then
        loop_mode=true
    fi
    artifact_round="$(resolve_artifact_round)"
    resume_round="$(resolve_resume_round)"
    if [ "$loop_mode" = true ] && ! is_positive_int "$resume_round"; then
        larch_err '**⚠ Step 3 MAV: STEP3_RESUME_ROUND missing or invalid**'
        exit 1
    fi
    retally_input_anchor="${SCOPE_ANCHOR_FILE:-}"
    mkdir -p "$DESIGN_TMPDIR/plan-review/round-${artifact_round}"
    retally_stdout="$(mktemp "${TMPDIR:-/tmp}/larch-step3-mav-retally.XXXXXX")" || exit 1
    if [ ! -r "$DESIGN_TMPDIR/voter-main-agent.txt" ]; then
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" voting findings-classification-header \
            >"$DESIGN_TMPDIR/plan-review/round-${artifact_round}/findings-classification.tsv"
        {
            printf '%s\n' 'TALLY_PLAN_REVIEW_STATUS=tally-error'
            printf 'VOTING_TALLY_FILE=%s/voting-tally.md\n' "$DESIGN_TMPDIR"
        } >"$retally_stdout"
        {
            printf '# Plan Review Voting Tally\n\n'
            printf '**⚠ Tally aborted: MainAgent voter file unreadable; no votes tallied.**\n'
        } >"$DESIGN_TMPDIR/voting-tally.md"
        retally_rc=0
    else
        set +e
        retally_args=(
            plan-review tally
            --ballot-file "$DESIGN_TMPDIR/ballot.txt"
            --design-tmpdir "$DESIGN_TMPDIR"
            --voter "MainAgent:$DESIGN_TMPDIR/voter-main-agent.txt"
            --findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${artifact_round}/findings-classification.tsv"
        )
        if [ -r "$DESIGN_TMPDIR/proposer-map.tsv" ]; then
            retally_args+=(--proposer-map-file "$DESIGN_TMPDIR/proposer-map.tsv")
        fi
        python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" "${retally_args[@]}" >"$retally_stdout"
        retally_rc=$?
        set -e
    fi
    retally_status="$(awk -F= '$1 == "TALLY_PLAN_REVIEW_STATUS" { value=$2 } END { print value }' "$retally_stdout")"
    case "$retally_status" in
        ok) ;;
        *) retally_status=tally-error ;;
    esac
    persist_args=(
        --design-tmpdir "$DESIGN_TMPDIR"
        --retally-stdout-file "$retally_stdout"
    )
    if [ -n "${retally_input_anchor:-}" ]; then
        persist_args+=(--retally-input-anchor "$retally_input_anchor")
    fi
    persist_args+=(
        --tally-plan-review-status "$retally_status"
        --loop-status complete
    )
    python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review persist-retally-env "${persist_args[@]}"
    append_mav_warning_once "$artifact_round"
    accepted_count="$(count_accepted_findings)"
    if [ "$retally_status" = ok ]; then
        round_start_s=""
        if [ -s "$DESIGN_TMPDIR/plan-review/round-${artifact_round}/round-start-s" ]; then
            round_start_s="$(tr -d '[:space:]' <"$DESIGN_TMPDIR/plan-review/round-${artifact_round}/round-start-s" 2>/dev/null || true)"
        fi
        if is_positive_int "$round_start_s"; then
            end_s="$(date +%s)"
            python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" plan-review record-round-timing \
                --design-tmpdir "$DESIGN_TMPDIR" \
                --round "$artifact_round" \
                --start-s "$round_start_s" \
                --end-s "$end_s" || true
        fi
        if [ "$loop_mode" = true ]; then
            if [ "$accepted_count" -eq 0 ]; then
                phase="awaiting-continuation"
            else
                phase="awaiting-apply"
            fi
            phase_file="$DESIGN_TMPDIR/.step3-round-${resume_round}.phase"
            printf '%s\n' "$phase" >"${phase_file}.tmp.$$"
            mv "${phase_file}.tmp.$$" "$phase_file"
        fi
    fi
    emit_kv_section_begin
    if [ "$retally_status" = tally-error ]; then
        emit_kv NEXT_ACTION step3b-bypass
    fi
    emit_kv TALLY_PLAN_REVIEW_STATUS "$retally_status"
    emit_kv LOOP_STATUS complete
    emit_kv ACCEPTED_COUNT "$accepted_count"
    emit_kv PHASE "$phase"
    [ -z "$resume_round" ] || emit_kv STEP3_RESUME_ROUND "$resume_round"
    [ -z "${STEP3_REVIEW_LOOP_STATUS:-}" ] || emit_kv STEP3_REVIEW_LOOP_STATUS "$STEP3_REVIEW_LOOP_STATUS"
    emit_kv_section_end
    while IFS= read -r _retally_line || [ -n "$_retally_line" ]; do
        emit "$_retally_line"
    done <"$retally_stdout"
    rm -f "$retally_stdout"
    if [ "$retally_rc" -eq 2 ] && [ "$retally_status" != tally-error ]; then
        exit 2
    fi
    exit 0
}

case "$PHASE" in
    pre) run_pre_phase ;;
    post) run_post_phase ;;
esac
