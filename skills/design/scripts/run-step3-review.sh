#!/usr/bin/env bash
# run-step3-review.sh - /design Step 3 plan-review phase driver.
# --preview-only: render plan-candidate preview live; driver owns .step3-entry-plan-printed sentinel.
# --no-preview (default): cap guard, round-cursor advance, plan-review-loop launch, result normalization.

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
    larch_err 'Usage: run-step3-review.sh --design-tmpdir PATH [--preview-only | --no-preview] [--round-cap N]'
}

DESIGN_TMPDIR_ARG=""
ROUND_CAP=""
_preview_only=false
_no_preview=false

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
        --preview-only)
            _preview_only=true
            shift
            ;;
        --no-preview)
            _no_preview=true
            shift
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

if [[ "$_preview_only" == true && "$_no_preview" == true ]]; then
    fail 'error: --preview-only and --no-preview are mutually exclusive'
fi

# Default to --no-preview when neither flag given (backward-compatible for direct harness callers).
if [[ "$_preview_only" != true ]]; then
    _no_preview=true
fi

[[ -n "$DESIGN_TMPDIR_ARG" ]] || { usage; fail '--design-tmpdir is required'; }

if [[ "$_preview_only" == true ]]; then
    # Preview mode: render plan-candidate preview live. Does not require --round-cap.
    # Does not cd/canonicalize the tmpdir — pass raw path so allowlist warnings work.
    SESSION_ENV_PATH="$DESIGN_TMPDIR_ARG/session-env.sh"
    PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
    [[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
    export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

    # shellcheck source=scripts/lib-design-tmpdir.sh
    source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

    _preview_sh="${RUN_STEP3_EMIT_PREVIEW_SH:-$PLUGIN_ROOT/skills/design/scripts/emit-design-plan-preview.sh}"

    # Sentinel re-entry suppression: skip renderer when sentinel exists AND tmpdir validates.
    _sentinel_ok=false
    if [[ -d "$DESIGN_TMPDIR_ARG" ]] && larch_design_tmpdir_validate "$DESIGN_TMPDIR_ARG"; then
        _sentinel_ok=true
        if [[ -e "$DESIGN_TMPDIR_ARG/.step3-entry-plan-printed" ]]; then
            exit 0
        fi
    fi

    # Capture renderer stdout with raw tmpdir so allowlist and missing-plan warnings print live.
    _preview_out=""
    set +e
    _preview_out=$("$_preview_sh" --design-tmpdir "$DESIGN_TMPDIR_ARG" --variant step3) || true
    set -e

    if [[ -n "${_preview_out:-}" ]]; then
        emit "$_preview_out"
    fi

    # Touch sentinel only when tmpdir validates AND renderer output contains the expected header
    # or the exact missing-plan warning. Never touch for non-header output or invalid tmpdir.
    if [[ "$_sentinel_ok" == true ]]; then
        _has_header=false
        case "${_preview_out:-}" in
            *'## Plan Candidate for Review'*) _has_header=true ;;
            *'**⚠ 3: plan.txt missing or empty; cannot present plan candidate for review**'*) _has_header=true ;;
        esac
        if [[ "$_has_header" == true ]]; then
            touch "$DESIGN_TMPDIR_ARG/.step3-entry-plan-printed" || true
        fi
    fi

    exit 0
fi

# --no-preview path: requires --round-cap; canonicalizes tmpdir.
[[ -n "$ROUND_CAP" ]] || { usage; fail '--round-cap is required'; }

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
ROUND_NUM=""

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

if [[ "$STEP3_REVIEW_CAP_REACHED" == true ]]; then
    LOOP_STATUS=cap-reached
    TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached
else
        _step3_prior_round_count=0
        if [[ "${STEP3_REVIEW_ROUND_NUM:-}" =~ ^[0-9]+$ ]]; then
            _step3_prior_round_count=$((STEP3_REVIEW_ROUND_NUM - 1))
        fi
        ROUND_NUM=1
        _wp_round=$(jq -r '.workflow_path // ""' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null || echo "")
        if [[ -z "$_wp_round" ]]; then
            _wp_round=$(sed -n 's/.*"workflow_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$DESIGN_TMPDIR/run-params.json" 2>/dev/null | head -1)
        fi
        _snap_sh="${RUN_STEP3_SNAPSHOT_PLAN_ROUND_SH:-$PLUGIN_ROOT/skills/design/scripts/snapshot-plan-round.sh}"
        if [[ "$_wp_round" == HARD ]]; then
            _cursor_out=$("$_snap_sh" read-cursor --design-tmpdir "$DESIGN_TMPDIR")
            while IFS= read -r _cline || [[ -n "$_cline" ]]; do
                case "$_cline" in
                    ROUND_CURSOR=*) ROUND_NUM="${_cline#ROUND_CURSOR=}" ;;
                esac
            done <<<"$_cursor_out"
            if [[ -f "$DESIGN_TMPDIR/plan-after-round-${ROUND_NUM}.txt" ]]; then
                _next_cursor=$((10#${ROUND_NUM} + 1))
                if ! "$_snap_sh" \
                    write-cursor --design-tmpdir "$DESIGN_TMPDIR" --value "$_next_cursor"; then
                    emit '**⚠ Step 3: failed to advance plan-review round cursor; aborting before review launch.**'
                    LOOP_STATUS=panel-failed
                    TALLY_PLAN_REVIEW_STATUS=panel-failed
                    phase_driver_write_result_env "$RESULT_ENV" \
                        "LOOP_STATUS=${LOOP_STATUS:-}" \
                        "TALLY_PLAN_REVIEW_STATUS=${TALLY_PLAN_REVIEW_STATUS:-}" \
                        "STEP3_REVIEW_CAP_REACHED=${STEP3_REVIEW_CAP_REACHED:-false}" \
                        "STEP3_REVIEW_ROUND_NUM=${STEP3_REVIEW_ROUND_NUM:-}" \
                        "ROUND_NUM=${ROUND_NUM:-}" \
                        "ACCEPTED_COUNT=${ACCEPTED_COUNT:-}" \
                        "IMPORTANT_ACCEPTED_COUNT=${IMPORTANT_ACCEPTED_COUNT:-}" \
                        "DEGRADED_PANEL=${DEGRADED_PANEL:-}" \
                        "ROUNDS_COMPLETED=${ROUNDS_COMPLETED:-}" \
                        "AGGREGATOR_STATUS=${AGGREGATOR_STATUS:-}" \
                        "VOTING_TALLY_FILE=${VOTING_TALLY_FILE:-}" \
                        "REVIEW_ROUND_COUNT=${REVIEW_ROUND_COUNT:-0}"
                    emit_kv LOOP_STATUS "${LOOP_STATUS:-}"
                    emit_kv TALLY_PLAN_REVIEW_STATUS "${TALLY_PLAN_REVIEW_STATUS:-}"
                    emit_kv REVIEW_ROUND_COUNT "${REVIEW_ROUND_COUNT:-0}"
                    printf '%s\n' "${_step3_prior_round_count:-0}" >"$ROUND_COUNT_FILE"
                    REVIEW_ROUND_COUNT="${_step3_prior_round_count:-0}"
                    exit 1
                fi
                ROUND_NUM=$_next_cursor
            fi
        fi
        if [[ "${STEP3_REVIEW_ROUND_NUM:-}" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$STEP3_REVIEW_ROUND_NUM" >"$ROUND_COUNT_FILE"
            REVIEW_ROUND_COUNT="$STEP3_REVIEW_ROUND_NUM"
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
            --round-cap "$ROUND_CAP")
        _plan_review_rc=$?
        set -e

        ACCEPTED_COUNT=""
        DEGRADED_PANEL=""
        ROUNDS_COMPLETED=""
        TALLY_PLAN_REVIEW_STATUS=""
        AGGREGATOR_STATUS=""
        VOTING_TALLY_FILE=""
        IMPORTANT_ACCEPTED_COUNT=""
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
                    esac
                done < <(phase_driver_read_result_env "$INNER_RESULT_ENV" \
                    LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED \
                    REASON REVISE_STATUS CONVERGENCE_STREAK COLLECT_OK_COUNT COLLECT_FAILURE_COUNT \
                    TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE VOTER_1_PARSE_RATE_STATUS)
                while IFS= read -r _line || [[ -n "$_line" ]]; do
                    _key="${_line%%=*}"
                    _value="${_line#*=}"
                    [[ "$_key" == WARN ]] && emit_kv WARN "$_value"
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

emit_kv LOOP_STATUS "${LOOP_STATUS:-}"
emit_kv STEP3_REVIEW_CAP_REACHED "${STEP3_REVIEW_CAP_REACHED:-false}"
emit_kv STEP3_REVIEW_ROUND_NUM "${STEP3_REVIEW_ROUND_NUM:-}"
emit_kv ROUND_NUM "${ROUND_NUM:-}"
emit_kv ACCEPTED_COUNT "${ACCEPTED_COUNT:-}"
emit_kv IMPORTANT_ACCEPTED_COUNT "${IMPORTANT_ACCEPTED_COUNT:-}"
emit_kv DEGRADED_PANEL "${DEGRADED_PANEL:-}"
emit_kv ROUNDS_COMPLETED "${ROUNDS_COMPLETED:-}"
emit_kv TALLY_PLAN_REVIEW_STATUS "${TALLY_PLAN_REVIEW_STATUS:-}"
emit_kv AGGREGATOR_STATUS "${AGGREGATOR_STATUS:-}"
emit_kv VOTING_TALLY_FILE "${VOTING_TALLY_FILE:-}"
emit_kv REVIEW_ROUND_COUNT "${REVIEW_ROUND_COUNT:-0}"

if ! phase_driver_write_result_env "$RESULT_ENV" \
    "LOOP_STATUS=${LOOP_STATUS:-}" \
    "TALLY_PLAN_REVIEW_STATUS=${TALLY_PLAN_REVIEW_STATUS:-}" \
    "STEP3_REVIEW_CAP_REACHED=${STEP3_REVIEW_CAP_REACHED:-false}" \
    "STEP3_REVIEW_ROUND_NUM=${STEP3_REVIEW_ROUND_NUM:-}" \
    "ROUND_NUM=${ROUND_NUM:-}" \
    "ACCEPTED_COUNT=${ACCEPTED_COUNT:-}" \
    "IMPORTANT_ACCEPTED_COUNT=${IMPORTANT_ACCEPTED_COUNT:-}" \
    "DEGRADED_PANEL=${DEGRADED_PANEL:-}" \
    "ROUNDS_COMPLETED=${ROUNDS_COMPLETED:-}" \
    "AGGREGATOR_STATUS=${AGGREGATOR_STATUS:-}" \
    "VOTING_TALLY_FILE=${VOTING_TALLY_FILE:-}" \
    "REVIEW_ROUND_COUNT=${REVIEW_ROUND_COUNT:-0}"; then
    emit_kv WARN "Step 3: refusing to write symlinked result env $(basename "$RESULT_ENV")"
    exit 1
fi

exit 0
