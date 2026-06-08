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
    larch_err 'Usage: run-step3-review.sh --design-tmpdir PATH [--preview-only | --no-preview]'
}

DESIGN_TMPDIR_ARG=""
_preview_only=false
_no_preview=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --design-tmpdir)
            [[ $# -ge 2 ]] || fail '--design-tmpdir requires a value'
            DESIGN_TMPDIR_ARG="$2"
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
    # Preview mode: render plan-candidate preview live.
    # Does not cd/canonicalize the tmpdir — pass raw path so allowlist warnings work.
    SESSION_ENV_PATH="$DESIGN_TMPDIR_ARG/session-env.sh"
    PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
    [[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
    export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

    # shellcheck source=scripts/lib-design-tmpdir.sh
    source "$PLUGIN_ROOT/scripts/lib-design-tmpdir.sh"

    _preview_sh="${RUN_STEP3_EMIT_PREVIEW_SH:-$PLUGIN_ROOT/skills/design/scripts/emit-design-plan-preview.sh}"

    # Sentinel re-entry suppression: skip renderer when sentinel exists AND tmpdir validates.
    # Canonicalize only for sentinel read/write/touch; renderer keeps raw path for allowlist warnings.
    _sentinel_ok=false
    _canonical_tmpdir=""
    if [[ -d "$DESIGN_TMPDIR_ARG" ]] && larch_design_tmpdir_validate "$DESIGN_TMPDIR_ARG"; then
        _sentinel_ok=true
        _canonical_tmpdir="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
        if [[ -e "$_canonical_tmpdir/.step3-entry-plan-printed" ]]; then
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

    # Touch sentinel only when tmpdir validates AND renderer output contains the expected header.
    # Missing/empty plan.txt re-warns until repaired, so the first real plan render owns the sentinel.
    if [[ "$_sentinel_ok" == true ]]; then
        _has_header=false
        case "${_preview_out:-}" in
            *'## Plan Candidate for Review'*) _has_header=true ;;
        esac
        if [[ "$_has_header" == true ]]; then
            touch "$_canonical_tmpdir/.step3-entry-plan-printed" || true
        fi
    fi

    exit 0
fi

# --no-preview path: canonicalizes tmpdir.

DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"
export DESIGN_TMPDIR

SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"
PLUGIN_ROOT="$(phase_driver_resolve_plugin_root "$SCRIPT_DIR" "$SESSION_ENV_PATH")"
[[ -d "$PLUGIN_ROOT" ]] || fail "plugin root not a directory: $PLUGIN_ROOT"
if [[ ! -f "$PLUGIN_ROOT/scripts/lib-scope-anchor-handoff.sh" ]]; then
    PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
fi
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
# shellcheck source=scripts/lib-scope-anchor-handoff.sh
source "$PLUGIN_ROOT/scripts/lib-scope-anchor-handoff.sh"

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
PANEL_PRUNED_EMPTY="false"
STEP3_REVIEW_CAP_REACHED=false
STEP3_REVIEW_ROUND_NUM=""
REVIEW_ROUND_COUNT="0"
SCOPE_ANCHOR_FILE=""

validate_scope_anchor_handoff() {
    local path="${SCOPE_ANCHOR_FILE:-}" canon design_canon
    [[ -z "$path" ]] && return 0
    design_canon="$(cd "$DESIGN_TMPDIR" && pwd -P)"
    if canon="$(larch_scope_anchor_validate_design "$path" "$design_canon" 2>/dev/null)"; then
        SCOPE_ANCHOR_FILE="$canon"
        return 0
    fi
    emit_kv WARN "Step 3: SCOPE_ANCHOR_FILE invalid; clearing"
    SCOPE_ANCHOR_FILE=""
}

recover_main_agent_scope_anchor() {
    local staged canon design_canon
    [[ "${LOOP_STATUS:-}" == "main-agent-vote-required" ]] || return 0
    [[ -z "${SCOPE_ANCHOR_FILE:-}" ]] || return 0
    staged="$DESIGN_TMPDIR/plan-review-scope-anchor.txt"
    design_canon="$(cd "$DESIGN_TMPDIR" && pwd -P)"
    if canon="$(larch_scope_anchor_validate_design "$staged" "$design_canon" 2>/dev/null)"; then
        SCOPE_ANCHOR_FILE="$canon"
        emit_kv WARN "Step 3: recovered SCOPE_ANCHOR_FILE from canonical staged anchor"
        return 0
    fi
    emit_kv WARN "Step 3: main-agent-vote-required without valid SCOPE_ANCHOR_FILE"
    LOOP_STATUS=panel-failed
    TALLY_PLAN_REVIEW_STATUS=panel-failed
    return 0
}

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
_round_cap=5

if ((_round_count >= _round_cap)); then
    emit "**⚠ Step 3: review-round cap (${_round_cap}) reached for ${_tier}; skipping panel and continuing to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C.**"
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

if [[ "$STEP3_REVIEW_CAP_REACHED" == true ]]; then
    for _stale_review_artifact in accepted-plan-findings.md rejected-findings.md oos.md voting-tally.md findings-classification.tsv ballot.txt; do
        rm -f "$DESIGN_TMPDIR/$_stale_review_artifact"
    done
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
                        "PANEL_PRUNED_EMPTY=${PANEL_PRUNED_EMPTY:-false}" \
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
        if [[ -d "$DESIGN_TMPDIR/plan-review" && ! -L "$DESIGN_TMPDIR/plan-review" ]]; then
            _pr_phys=$(cd "$DESIGN_TMPDIR/plan-review" && pwd -P) || _pr_phys=""
            if [[ -n "$_pr_phys" && "${ROUND_NUM:-}" =~ ^[0-9]+$ ]]; then
                _active_round="$_pr_phys/round-${ROUND_NUM}"
                if [[ -e "$_active_round" ]]; then
                    if [[ -L "$_active_round" ]]; then
                        emit_kv WARN "Step 3: refusing to remove symlinked round artifact round-${ROUND_NUM}"
                    elif [[ -d "$_active_round" ]]; then
                        rm -rf "$_active_round"
                    fi
                fi
            else
                emit_kv WARN 'Step 3: plan-review directory could not be resolved; skipping round cleanup'
            fi
        elif [[ -L "$DESIGN_TMPDIR/plan-review" ]]; then
            emit_kv WARN 'Step 3: refusing to clean symlinked plan-review directory'
        fi
        if [[ "${STEP3_REVIEW_ROUND_NUM:-}" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$STEP3_REVIEW_ROUND_NUM" >"$ROUND_COUNT_FILE"
            REVIEW_ROUND_COUNT="$STEP3_REVIEW_ROUND_NUM"
        fi
        _feature_file="$DESIGN_TMPDIR/feature-description.txt"
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
            --round-num "$ROUND_NUM")
        _plan_review_rc=$?
        set -e

        ACCEPTED_COUNT=""
        DEGRADED_PANEL=""
        ROUNDS_COMPLETED=""
        TALLY_PLAN_REVIEW_STATUS=""
        AGGREGATOR_STATUS=""
        VOTING_TALLY_FILE=""
        PANEL_PRUNED_EMPTY="false"
        IMPORTANT_ACCEPTED_COUNT=""
        while IFS= read -r _line || [[ -n "$_line" ]]; do
            _key="${_line%%=*}"
            _value="${_line#*=}"
            case "$_key" in
                LOOP_STATUS | ACCEPTED_COUNT | IMPORTANT_ACCEPTED_COUNT | DEGRADED_PANEL | ROUNDS_COMPLETED | REASON | REVISE_STATUS | COLLECT_OK_COUNT | COLLECT_FAILURE_COUNT | TALLY_PLAN_REVIEW_STATUS | AGGREGATOR_STATUS | VOTING_TALLY_FILE | VOTER_1_PARSE_RATE_STATUS | SCOPE_ANCHOR_FILE | PANEL_PRUNED_EMPTY)
                    printf -v "$_key" '%s' "$_value"
                    ;;
                WARN) emit_kv WARN "$_value" ;;
            esac
        done <<<"${_plan_review_out:-}"
        if [[ -f "$INNER_RESULT_ENV" ]]; then
            if [[ -L "$INNER_RESULT_ENV" ]]; then
                emit '**⚠ Step 3: result env is a symlink; ignoring it and using stdout fallback only**'
            else
                while IFS= read -r _line || [[ -n "$_line" ]]; do
                    _key="${_line%%=*}"
                    _value="${_line#*=}"
                    case "$_key" in
                        LOOP_STATUS | ACCEPTED_COUNT | IMPORTANT_ACCEPTED_COUNT | DEGRADED_PANEL | ROUNDS_COMPLETED | REASON | REVISE_STATUS | COLLECT_OK_COUNT | COLLECT_FAILURE_COUNT | TALLY_PLAN_REVIEW_STATUS | AGGREGATOR_STATUS | VOTING_TALLY_FILE | VOTER_1_PARSE_RATE_STATUS | SCOPE_ANCHOR_FILE | PANEL_PRUNED_EMPTY)
                            printf -v "$_key" '%s' "$_value"
                            ;;
                    esac
                done < <(phase_driver_read_result_env "$INNER_RESULT_ENV" \
                    LOOP_STATUS ACCEPTED_COUNT IMPORTANT_ACCEPTED_COUNT DEGRADED_PANEL ROUNDS_COMPLETED \
                    REASON REVISE_STATUS COLLECT_OK_COUNT COLLECT_FAILURE_COUNT \
                    TALLY_PLAN_REVIEW_STATUS AGGREGATOR_STATUS VOTING_TALLY_FILE VOTER_1_PARSE_RATE_STATUS SCOPE_ANCHOR_FILE PANEL_PRUNED_EMPTY)
                while IFS= read -r _line || [[ -n "$_line" ]]; do
                    _key="${_line%%=*}"
                    _value="${_line#*=}"
                    [[ "$_key" == WARN ]] && emit_kv WARN "$_value"
                done <"$INNER_RESULT_ENV"
            fi
        fi

        if [[ -z "${LOOP_STATUS:-}" || ! "${LOOP_STATUS}" =~ ^(complete|zero-findings-degraded-panel|tally-error|degraded-empty-collector|panel-failed|main-agent-vote-required)$ ]]; then
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

validate_scope_anchor_handoff
recover_main_agent_scope_anchor
larch_scope_anchor_relay_allowed || SCOPE_ANCHOR_FILE=""

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
emit_kv PANEL_PRUNED_EMPTY "${PANEL_PRUNED_EMPTY:-false}"
[[ -z "${SCOPE_ANCHOR_FILE:-}" ]] || emit_kv SCOPE_ANCHOR_FILE "${SCOPE_ANCHOR_FILE:-}"
emit_kv REVIEW_ROUND_COUNT "${REVIEW_ROUND_COUNT:-0}"

result_env_kvs=(
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
    "PANEL_PRUNED_EMPTY=${PANEL_PRUNED_EMPTY:-false}" \
    "REVIEW_ROUND_COUNT=${REVIEW_ROUND_COUNT:-0}"
)
[[ -z "${SCOPE_ANCHOR_FILE:-}" ]] || result_env_kvs+=("SCOPE_ANCHOR_FILE=${SCOPE_ANCHOR_FILE:-}")
if ! phase_driver_write_result_env "$RESULT_ENV" "${result_env_kvs[@]}"; then
    emit_kv WARN "Step 3: refusing to write symlinked result env $(basename "$RESULT_ENV")"
    exit 1
fi

exit 0
