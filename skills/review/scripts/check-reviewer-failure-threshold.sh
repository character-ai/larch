#!/usr/bin/env bash
# check-reviewer-failure-threshold.sh — Hard-stop review-core if too many specialist slots failed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: check-reviewer-failure-threshold.sh --collector-results-file FILE --panel hard|simple [--launched-slots N] [--round-num N]"
}

COLLECTOR_RESULTS_FILE=""
PANEL=""
LAUNCHED_SLOTS=""
ROUND_NUM="1"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --collector-results-file) COLLECTOR_RESULTS_FILE="${2:?--collector-results-file requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --launched-slots) LAUNCHED_SLOTS="${2:?--launched-slots requires a value}"; shift 2 ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "check-reviewer-failure-threshold.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$PANEL" == "hard" || "$PANEL" == "simple" ]] || { larch_err "check-reviewer-failure-threshold.sh: --panel must be hard or simple"; exit 2; }
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "check-reviewer-failure-threshold.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "check-reviewer-failure-threshold.sh: --round-num must be a positive integer"; exit 2; }

# Intended static panel size is round-aware because Codex reviewer slots are
# intentionally omitted after round 1. Dynamic scout reviewers are excluded
# from the threshold denominator and should not affect the static panel result.
if (( ROUND_NUM == 1 )); then
    case "$PANEL" in
        hard)   STATIC_INTENDED_SLOTS=12 ;;
        simple) STATIC_INTENDED_SLOTS=7  ;;
    esac
else
    STATIC_INTENDED_SLOTS=6
fi
INTENDED_SLOTS=$STATIC_INTENDED_SLOTS

is_dynamic_reviewer_basename() {
    local base="$1"
    [[ "$base" =~ ^dyn-.*-output(-phase[23]|-retry)*\.txt$ ]]
}

# Count slots whose STATUS != OK and STATUS != cap_hit. Slots that never launched
# because the vendor was unhealthy are counted via INTENDED_SLOTS - LAUNCHED_SLOTS
# (the orchestrator passes --launched-slots when known; otherwise we use the
# parse result as the actual count and assume no never-launched slots).
SUCCEEDED_SLOTS=0
FAILED_SLOTS=0
COUNTED_SLOTS=0
NOT_SUBSTANTIVE_SLOTS=0

if [[ -n "$COLLECTOR_RESULTS_FILE" && -f "$COLLECTOR_RESULTS_FILE" ]]; then
    # Parse blank-line-separated records; each has STATUS=<value>.
    current_reviewer_file=""
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            if [[ -n "${current_status:-}" ]]; then
                current_base=$(basename "${current_reviewer_file:-}")
                if is_dynamic_reviewer_basename "$current_base"; then
                    current_status=""
                    current_reviewer_file=""
                    continue
                fi
                COUNTED_SLOTS=$((COUNTED_SLOTS + 1))
                case "$current_status" in
                    OK|cap_hit) SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS + 1)) ;;
                    NOT_SUBSTANTIVE)
                        FAILED_SLOTS=$((FAILED_SLOTS + 1))
                        NOT_SUBSTANTIVE_SLOTS=$((NOT_SUBSTANTIVE_SLOTS + 1))
                        ;;
                    *)          FAILED_SLOTS=$((FAILED_SLOTS + 1)) ;;
                esac
            fi
            current_status=""
            current_reviewer_file=""
            continue
        fi
        case "$line" in
            REVIEWER_FILE=*) current_reviewer_file="${line#REVIEWER_FILE=}" ;;
            STATUS=*) current_status="${line#STATUS=}" ;;
        esac
    done < "$COLLECTOR_RESULTS_FILE"
    # Handle trailing record without final blank line.
    if [[ -n "${current_status:-}" ]]; then
        current_base=$(basename "${current_reviewer_file:-}")
        if ! is_dynamic_reviewer_basename "$current_base"; then
            COUNTED_SLOTS=$((COUNTED_SLOTS + 1))
            case "$current_status" in
                OK|cap_hit) SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS + 1)) ;;
                NOT_SUBSTANTIVE)
                    FAILED_SLOTS=$((FAILED_SLOTS + 1))
                    NOT_SUBSTANTIVE_SLOTS=$((NOT_SUBSTANTIVE_SLOTS + 1))
                    ;;
                *)          FAILED_SLOTS=$((FAILED_SLOTS + 1)) ;;
            esac
        fi
    fi
fi

# Add never-launched slots as failures (vendor unhealthy → slot never dispatched).
if [[ -n "$LAUNCHED_SLOTS" ]]; then
    case "$LAUNCHED_SLOTS" in ''|*[!0-9]*) larch_err "check-reviewer-failure-threshold.sh: --launched-slots must be a non-negative integer"; exit 2 ;; esac
    NEVER_LAUNCHED=$(( INTENDED_SLOTS - LAUNCHED_SLOTS ))
    (( NEVER_LAUNCHED < 0 )) && NEVER_LAUNCHED=0
    FAILED_SLOTS=$(( FAILED_SLOTS + NEVER_LAUNCHED ))
fi

# Threshold: >50% of intended panel size. HARD=12 → fail if >6. SIMPLE=7 → fail if >3.
HALF_PLUS_ONE_MIN=$(( INTENDED_SLOTS / 2 + 1 ))
THRESHOLD_OK=true
THRESHOLD_REASON=""
if (( FAILED_SLOTS >= HALF_PLUS_ONE_MIN )); then
    THRESHOLD_OK=false
    THRESHOLD_REASON="$FAILED_SLOTS of $INTENDED_SLOTS panel slots failed (threshold: >50% = >$(( INTENDED_SLOTS / 2 )))"
fi

emit_kv INTENDED_SLOTS "$INTENDED_SLOTS"
emit_kv SUCCEEDED_SLOTS "$SUCCEEDED_SLOTS"
emit_kv FAILED_SLOTS "$FAILED_SLOTS"
emit_kv COUNTED_SLOTS "$COUNTED_SLOTS"
emit_kv NOT_SUBSTANTIVE_SLOTS "$NOT_SUBSTANTIVE_SLOTS"
emit_kv THRESHOLD_OK "$THRESHOLD_OK"
emit_kv THRESHOLD_REASON "$THRESHOLD_REASON"
