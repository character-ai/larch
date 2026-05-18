#!/usr/bin/env bash
# check-reviewer-failure-threshold.sh — Hard-stop review-core if too many specialist slots failed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: check-reviewer-failure-threshold.sh --collector-results-file FILE --panel hard|simple [--launched-slots N]"
}

COLLECTOR_RESULTS_FILE=""
PANEL=""
LAUNCHED_SLOTS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --collector-results-file) COLLECTOR_RESULTS_FILE="${2:?--collector-results-file requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --launched-slots) LAUNCHED_SLOTS="${2:?--launched-slots requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "check-reviewer-failure-threshold.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$PANEL" == "hard" || "$PANEL" == "simple" ]] || { larch_err "check-reviewer-failure-threshold.sh: --panel must be hard or simple"; exit 2; }

# Intended static panel size: HARD=12 (6 Cursor + 6 Codex specialists),
# SIMPLE=7 (6 Cursor + 1 Codex generalist). Dynamic scout reviewers widen the
# counted population; when --launched-slots is present we treat the larger of
# the static shape and launched slot count as the intended denominator.
case "$PANEL" in
    hard)   STATIC_INTENDED_SLOTS=12 ;;
    simple) STATIC_INTENDED_SLOTS=7  ;;
esac
INTENDED_SLOTS=$STATIC_INTENDED_SLOTS

# Count slots whose STATUS != OK and STATUS != cap_hit. Slots that never launched
# because the vendor was unhealthy are counted via INTENDED_SLOTS - LAUNCHED_SLOTS
# (the orchestrator passes --launched-slots when known; otherwise we use the
# parse result as the actual count and assume no never-launched slots).
SUCCEEDED_SLOTS=0
FAILED_SLOTS=0
COUNTED_SLOTS=0

if [[ -n "$COLLECTOR_RESULTS_FILE" && -f "$COLLECTOR_RESULTS_FILE" ]]; then
    # Parse blank-line-separated records; each has STATUS=<value>.
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" ]]; then
            if [[ -n "${current_status:-}" ]]; then
                COUNTED_SLOTS=$((COUNTED_SLOTS + 1))
                case "$current_status" in
                    OK|cap_hit) SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS + 1)) ;;
                    *)          FAILED_SLOTS=$((FAILED_SLOTS + 1)) ;;
                esac
            fi
            current_status=""
            continue
        fi
        case "$line" in
            STATUS=*) current_status="${line#STATUS=}" ;;
        esac
    done < "$COLLECTOR_RESULTS_FILE"
    # Handle trailing record without final blank line.
    if [[ -n "${current_status:-}" ]]; then
        COUNTED_SLOTS=$((COUNTED_SLOTS + 1))
        case "$current_status" in
            OK|cap_hit) SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS + 1)) ;;
            *)          FAILED_SLOTS=$((FAILED_SLOTS + 1)) ;;
        esac
    fi
fi

# Add never-launched slots as failures (vendor unhealthy → slot never dispatched).
if [[ -n "$LAUNCHED_SLOTS" ]]; then
    case "$LAUNCHED_SLOTS" in ''|*[!0-9]*) larch_err "check-reviewer-failure-threshold.sh: --launched-slots must be a non-negative integer"; exit 2 ;; esac
    if (( LAUNCHED_SLOTS > INTENDED_SLOTS )); then
        INTENDED_SLOTS=$LAUNCHED_SLOTS
    fi
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
emit_kv THRESHOLD_OK "$THRESHOLD_OK"
emit_kv THRESHOLD_REASON "$THRESHOLD_REASON"
