#!/usr/bin/env bash
# run-step3-review.sh - /design Step 3 plan-review phase driver.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$SCRIPT_DIR/lib-phase-driver.sh"
larch_quiet_init

fail() {
    larch_err "run-step3-review.sh: $*"
    exit 2
}

usage() {
    larch_err 'Usage: run-step3-review.sh --design-tmpdir PATH --round-cap N --convergence-threshold N'
}

DESIGN_TMPDIR_ARG=""
ROUND_CAP=""
CONVERGENCE_THRESHOLD=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
            shift 2
            ;;
        --round-cap)
            [[ $# -ge 2 ]] || fail '--round-cap requires a value'
            ROUND_CAP="$2"
            shift 2
            ;;
        --convergence-threshold)
            [[ $# -ge 2 ]] || fail '--convergence-threshold requires a value'
            CONVERGENCE_THRESHOLD="$2"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage
            fail "unknown option: $1"
            ;;
    esac
done

[[ -n "$DESIGN_TMPDIR_ARG" ]] || { usage; fail '--design-tmpdir is required'; }
[[ -n "$ROUND_CAP" ]] || { usage; fail '--round-cap is required'; }
[[ -n "$CONVERGENCE_THRESHOLD" ]] || { usage; fail '--convergence-threshold is required'; }

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR

SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

RESULT_ENV="$DESIGN_TMPDIR/.step3-review-result.env"
CAP_ENV="$DESIGN_TMPDIR/.step3-review-cap.env"
ROUND_COUNT_FILE="$DESIGN_TMPDIR/review-round-count.txt"
INNER_RESULT_ENV="$DESIGN_TMPDIR/.step3-plan-review-result.env"

LOOP_STATUS=""
TALLY_PLAN_REVIEW_STATUS=""
ACCEPTED_COUNT=""
IMPORTANT_ACCEPTED_COUNT=""
DEGRADED_PANEL=""
ROUNDS_COMPLETED=""
AGGREGATOR_STATUS=""
VOTING_TALLY_FILE=""
STEP3_REVIEW_CAP_REACHED=false
STEP3_REVIEW_ROUND_NUM=""
REVIEW_ROUND_COUNT="0"

_round_count=0
if [[ -s "$ROUND_COUNT_FILE" ]]; then
    _raw_count="$(tr -d '[:space:]' <"$ROUND_COUNT_FILE" 2>/dev/null || true)"
    case "$_raw_count" in
        '' | *[!0-9]*)
            emit '**⚠ Step 3: review-round-count.txt non-numeric; treating as 0**'
            _round_count=0
            ;;
        *) _round_count=$((10#$_raw_count)) ;;
    esac
fi

_tier="$("$PLUGIN_ROOT/scripts/read-design-classification.sh" "$DESIGN_TMPDIR/run-params.json")"
case "$_tier" in
    SIMPLE) _round_cap=3 ;;
    *) _round_cap=5 ;;
esac

if ((_round_count >= _round_cap)); then
    emit "**⚠ Step 3: review-round cap (${_round_cap}) reached for ${_tier}; skipping panel and continuing to Step 3b, Step 4, then Gate C.**"
    emit '⏩ 3: plan review — cap reached; skipping'
    STEP3_REVIEW_CAP_REACHED=true
    STEP3_REVIEW_ROUND_NUM=""
    cat >"$CAP_ENV" <<'EOF'
STEP3_REVIEW_CAP_REACHED=true
STEP3_REVIEW_ROUND_NUM=
EOF
else
    _next_round=$((_round_count + 1))
    STEP3_REVIEW_CAP_REACHED=false
    STEP3_REVIEW_ROUND_NUM="$_next_round"
    cat >"$CAP_ENV" <<EOF
STEP3_REVIEW_CAP_REACHED=false
STEP3_REVIEW_ROUND_NUM=$_next_round
EOF
fi

REVIEW_ROUND_COUNT="$_round_count"

if [[ "$STEP3_REVIEW_CAP_REACHED" == true ]]; then
    LOOP_STATUS=cap-reached
    TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached
else
    if [[ -d "$DESIGN_TMPDIR/plan-review" && ! -L "$DESIGN_TMPDIR/plan-review" ]]; then
        _pr_phys=$(cd "$DESIGN_TMPDIR/plan-review" && pwd -P) || _pr_phys=""
        if [[ -n "$_pr_phys" ]]; then
            for _child in "$_pr_phys"/round-[0-9]*; do
                [[ -d "$_child" ]] || continue
                if [[ -L "$_child" ]]; then
                    emit_kv WARN "Step 3: refusing to remove symlinked round artifact $(basename "$_child")"
                    continue
                fi
                rm -rf "$_child"
            done
        else
            emit_kv WARN 'Step 3: plan-review directory could not be resolved; skipping round cleanup'
        fi
    elif [[ -L "$DESIGN_TMPDIR/plan-review" ]]; then
        emit_kv WARN 'Step 3: refusing to clean symlinked plan-review directory'
    fi

    if [[ -f "$CAP_ENV" ]]; then
        # shellcheck source=/dev/null
        source "$CAP_ENV"
    fi

    if [[ "${STEP3_REVIEW_CAP_REACHED:-false}" == true ]]; then
        emit '⏩ 3: plan review — cap reached; skipping'
        LOOP_STATUS=cap-reached
        TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached
    else
        _step3_prior_round_count=0
        if [[ "${STEP3_REVIEW_ROUND_NUM:-}" =~ ^[0-9]+$ ]]; then
            _step3_prior_round_count=$((STEP3_REVIEW_ROUND_NUM - 1))
            printf '%s\n' "$STEP3_REVIEW_ROUND_NUM" >"$ROUND_COUNT_FILE"
            REVIEW_ROUND_COUNT="$STEP3_REVIEW_ROUND_NUM"
        fi
        ROUND_NUM=1
        _wp_round=$(jq -r '.workflow_path // ""' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo "")
        if [[ -z "$_wp_round" ]]; then
            _wp_round=$(sed -n 's/.*"workflow_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null | head -1)
        fi
        if [[ "$_wp_round" == HARD ]]; then
            _cursor_out=$("$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh" read-cursor --design-tmpdir "$DESIGN_TMPDIR")
            while IFS= read -r _cline || [[ -n "$_cline" ]]; do
                case "$_cline" in
                    ROUND_CURSOR=*) ROUND_NUM="${_cline#ROUND_CURSOR=}" ;;
                esac
            done <<<"$_cursor_out"
            if [[ -f "$DESIGN_TMPDIR/plan-after-round-${ROUND_NUM}.txt" ]]; then
                _next_cursor=$((10#${ROUND_NUM} + 1))
                if ! "$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh" \
                    write-cursor --design-tmpdir "$DESIGN_TMPDIR" --value "$_next_cursor"; then
                    emit '**⚠ Step 3: failed to advance plan-review round cursor; aborting before review launch.**'
                    LOOP_STATUS=panel-failed
                    TALLY_PLAN_REVIEW_STATUS=panel-failed
                    phase_driver_write_result_env "$RESULT_ENV" \
                        "LOOP_STATUS=${LOOP_STATUS:-}" \
                        "TALLY_PLAN_REVIEW_STATUS=${TALLY_PLAN_REVIEW_STATUS:-}" \
                        "STEP3_REVIEW_CAP_REACHED=${STEP3_REVIEW_CAP_REACHED:-false}" \
                        "STEP3_REVIEW_ROUND_NUM=${STEP3_REVIEW_ROUND_NUM:-}" \
                        "ACCEPTED_COUNT=${ACCEPTED_COUNT:-}" \
                        "IMPORTANT_ACCEPTED_COUNT=${IMPORTANT_ACCEPTED_COUNT:-}" \
                        "DEGRADED_PANEL=${DEGRADED_PANEL:-}" \
                        "ROUNDS_COMPLETED=${ROUNDS_COMPLETED:-}" \
                        "AGGREGATOR_STATUS=${AGGREGATOR_STATUS:-}" \
                        "VOTING_TALLY_FILE=${VOTING_TALLY_FILE:-}" \
                        "REVIEW_ROUND_COUNT=${REVIEW_ROUND_COUNT:-0}"
                    exit 1
                fi
                ROUND_NUM=$_next_cursor
            fi
        fi
        _feature_file="${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt"
        _plan_loop_sh="${RUN_STEP3_PLAN_REVIEW_LOOP_SH:-$PLUGIN_ROOT/skills/design/scripts/plan-review-loop.sh}"
        [[ -x "$_plan_loop_sh" ]] || fail "plan-review-loop.sh not executable: $_plan_loop_sh"
        if [[ -e "$INNER_RESULT_ENV" && ! -L "$INNER_RESULT_ENV" ]]; then
            rm -f "$INNER_RESULT_ENV"
        fi
        set +e
        # Subprocess stdout must reach command substitution; quiet init redirects FD 1.
        _plan_review_out=$(LARCH_QUIET_DISABLE=1 "$_plan_loop_sh" \
            --design-tmpdir "$DESIGN_TMPDIR" \
            --plan-file "$DESIGN_TMPDIR/plan.txt" \
            --feature-file "$_feature_file" \
            --codex-present "${CODEX_PRESENT:-false}" \
            --cursor-present "${CURSOR_PRESENT:-false}" \
            --round-num "$ROUND_NUM" \
            --round-cap "$ROUND_CAP" \
            --convergence-threshold "$CONVERGENCE_THRESHOLD")
        _plan_review_rc=$?
        set -e

        ACCEPTED_COUNT=""
        DEGRADED_PANEL=""
        ROUNDS_COMPLETED=""
        TALLY_PLAN_REVIEW_STATUS=""
        AGGREGATOR_STATUS=""
        VOTING_TALLY_FILE=""
        IMPORTANT_ACCEPTED_COUNT=""
        _allow=(
            LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED
            REASON REVISE_STATUS CONVERGENCE_STREAK COLLECT_OK_COUNT COLLECT_FAILURE_COUNT
            TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE VOTER_1_PARSE_RATE_STATUS
        )
        if [[ -f "$INNER_RESULT_ENV" ]]; then
            if [[ -L "$INNER_RESULT_ENV" ]]; then
                emit '**⚠ Step 3: result env is a symlink; ignoring it and using stdout fallback only**'
            else
                while IFS= read -r _line || [[ -n "$_line" ]]; do
                    _key="${_line%%=*}"
                    _value="${_line#*=}"
                    case "$_key" in
                        LOOP_STATUS | ACCEPTED_COUNT | IMPORTANT_ACCEPTED_COUNT | DEGRADED_PANEL | ROUNDS_COMPLETED | REASON | REVISE_STATUS | CONVERGENCE_STREAK | COLLECT_OK_COUNT | COLLECT_FAILURE_COUNT | TALLY_PLAN_REVIEW_STATUS | AGGREGATOR_STATUS | VOTING_TALLY_FILE | VOTER_1_PARSE_RATE_STATUS)
                            printf -v "$_key" '%s' "$_value"
                            ;;
                        WARN) emit_kv WARN "$_value" ;;
                    esac
                done <"$INNER_RESULT_ENV"
            fi
        fi
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            _key="${_line%%=*}"
            _value="${_line#*=}"
            case "$_key" in
                LOOP_STATUS | ACCEPTED_COUNT | IMPORTANT_ACCEPTED_COUNT | DEGRADED_PANEL | ROUNDS_COMPLETED | REASON | REVISE_STATUS | CONVERGENCE_STREAK | COLLECT_OK_COUNT | COLLECT_FAILURE_COUNT | TALLY_PLAN_REVIEW_STATUS | AGGREGATOR_STATUS | VOTING_TALLY_FILE | VOTER_1_PARSE_RATE_STATUS)
                    [[ -n "${!_key:-}" ]] || printf -v "$_key" '%s' "$_value"
                    ;;
                WARN) emit_kv WARN "$_value" ;;
            esac
        done <<<"${_plan_review_out:-}"

        if [[ -z "${LOOP_STATUS:-}" || ! "${LOOP_STATUS}" =~ ^(complete|converged|cap-hit|zero-findings-degraded-panel|revision-failed|tally-error|degraded-empty-collector|plan-size-trigger|plan-validator-defects|emit-plan-failed|optional-trailer-dedup-loss|panel-failed|main-agent-vote-required)$ ]]; then
            LOOP_STATUS=panel-failed
            emit '**⚠ Step 3: missing or invalid LOOP_STATUS after plan-review-loop.sh; treating as panel-failed**'
        fi
        if [[ "${_plan_review_rc:-0}" -ne 0 && "$LOOP_STATUS" != panel-failed && "$LOOP_STATUS" != main-agent-vote-required ]]; then
            emit "**⚠ plan-review-loop.sh exited with rc=$_plan_review_rc and unexpected LOOP_STATUS=$LOOP_STATUS**"
            LOOP_STATUS=panel-failed
        fi
        if [[ "${STEP3_REVIEW_ROUND_NUM:-}" =~ ^[0-9]+$ ]]; then
            _persist_round=true
            if [[ "${TALLY_PLAN_REVIEW_STATUS:-}" == tally-error || "${LOOP_STATUS:-}" == tally-error || "${LOOP_STATUS:-}" == degraded-empty-collector ]]; then
                _persist_round=false
                printf '%s\n' "${_step3_prior_round_count:-0}" >"$ROUND_COUNT_FILE"
                REVIEW_ROUND_COUNT="${_step3_prior_round_count:-0}"
            fi
            if [[ "$_persist_round" == true ]]; then
                printf '%s\n' "$STEP3_REVIEW_ROUND_NUM" >"$ROUND_COUNT_FILE"
                REVIEW_ROUND_COUNT="$STEP3_REVIEW_ROUND_NUM"
            fi
        fi
    fi
fi

phase_driver_write_result_env "$RESULT_ENV" \
    "LOOP_STATUS=${LOOP_STATUS:-}" \
    "TALLY_PLAN_REVIEW_STATUS=${TALLY_PLAN_REVIEW_STATUS:-}" \
    "STEP3_REVIEW_CAP_REACHED=${STEP3_REVIEW_CAP_REACHED:-false}" \
    "STEP3_REVIEW_ROUND_NUM=${STEP3_REVIEW_ROUND_NUM:-}" \
    "ACCEPTED_COUNT=${ACCEPTED_COUNT:-}" \
    "IMPORTANT_ACCEPTED_COUNT=${IMPORTANT_ACCEPTED_COUNT:-}" \
    "DEGRADED_PANEL=${DEGRADED_PANEL:-}" \
    "ROUNDS_COMPLETED=${ROUNDS_COMPLETED:-}" \
    "AGGREGATOR_STATUS=${AGGREGATOR_STATUS:-}" \
    "VOTING_TALLY_FILE=${VOTING_TALLY_FILE:-}" \
    "REVIEW_ROUND_COUNT=${REVIEW_ROUND_COUNT:-0}"

emit_kv LOOP_STATUS "${LOOP_STATUS:-}"
emit_kv STEP3_REVIEW_CAP_REACHED "${STEP3_REVIEW_CAP_REACHED:-false}"
emit_kv ACCEPTED_COUNT "${ACCEPTED_COUNT:-}"
emit_kv IMPORTANT_ACCEPTED_COUNT "${IMPORTANT_ACCEPTED_COUNT:-}"
emit_kv DEGRADED_PANEL "${DEGRADED_PANEL:-}"
emit_kv ROUNDS_COMPLETED "${ROUNDS_COMPLETED:-}"
emit_kv TALLY_PLAN_REVIEW_STATUS "${TALLY_PLAN_REVIEW_STATUS:-}"
emit_kv AGGREGATOR_STATUS "${AGGREGATOR_STATUS:-}"
emit_kv VOTING_TALLY_FILE "${VOTING_TALLY_FILE:-}"
emit_kv REVIEW_ROUND_COUNT "${REVIEW_ROUND_COUNT:-0}"

exit 0
