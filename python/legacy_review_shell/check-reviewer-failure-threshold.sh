#!/usr/bin/env bash
# check-reviewer-failure-threshold.sh — Hard-stop review-core if too many specialist slots failed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

usage() {
    larch_err "Usage: check-reviewer-failure-threshold.sh --collector-results-file FILE --panel hard|simple [--intended-slots N] [--launched-slots N] [--dropped-slots-file FILE] [--reviewer-output-files FILE...] [--round-num N]"
}

COLLECTOR_RESULTS_FILE=""
PANEL=""
INTENDED_SLOTS="3"
LAUNCHED_SLOTS=""
DROPPED_SLOTS_FILE=""
ROUND_NUM="1"
REVIEWER_OUTPUT_FILES=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --collector-results-file) COLLECTOR_RESULTS_FILE="${2:?--collector-results-file requires a value}"; shift 2 ;;
        --panel) PANEL="${2:?--panel requires a value}"; shift 2 ;;
        --intended-slots) INTENDED_SLOTS="${2:?--intended-slots requires a value}"; shift 2 ;;
        --launched-slots) LAUNCHED_SLOTS="${2:?--launched-slots requires a value}"; shift 2 ;;
        --dropped-slots-file) DROPPED_SLOTS_FILE="${2:?--dropped-slots-file requires a value}"; shift 2 ;;
        --reviewer-output-files)
            shift
            while [[ $# -gt 0 && "$1" != --* ]]; do
                REVIEWER_OUTPUT_FILES+=("$1")
                shift
            done
            ;;
        --round-num) ROUND_NUM="${2:?--round-num requires a value}"; shift 2 ;;
        --help) usage; exit 0 ;;
        *) larch_err "check-reviewer-failure-threshold.sh: unknown option: $1"; usage; exit 2 ;;
    esac
done

[[ "$PANEL" == "hard" || "$PANEL" == "simple" ]] || { larch_err "check-reviewer-failure-threshold.sh: --panel must be hard or simple"; exit 2; }
case "$INTENDED_SLOTS" in ''|*[!0-9]*) larch_err "check-reviewer-failure-threshold.sh: --intended-slots must be a non-negative integer"; exit 2 ;; esac
case "$ROUND_NUM" in ''|*[!0-9]*) larch_err "check-reviewer-failure-threshold.sh: --round-num must be a positive integer"; exit 2 ;; esac
ROUND_NUM=$((10#$ROUND_NUM))
(( ROUND_NUM > 0 )) || { larch_err "check-reviewer-failure-threshold.sh: --round-num must be a positive integer"; exit 2; }
[[ -z "$DROPPED_SLOTS_FILE" || -f "$DROPPED_SLOTS_FILE" ]] || { larch_err "check-reviewer-failure-threshold.sh: --dropped-slots-file must name a file"; exit 2; }

# Callers pass the emitted static denominator. Dynamic scout reviewers are
# excluded from the threshold denominator and should not affect the static panel
# result.
INTENDED_SLOTS=$((10#$INTENDED_SLOTS))

is_dynamic_reviewer_basename() {
    local base="$1"
    [[ "$base" =~ ^dyn-.*-output(-phase[23]|-retry)*\.txt$ ]]
}

is_dynamic_slot_name() {
    case "$1" in
        dyn-*) return 0 ;;
        *) return 1 ;;
    esac
}

normalize_reviewer_output_base() {
    local base="$1" stem ext=""
    base="${base##*/}"
    case "$base" in
        *.txt) stem="${base%.txt}"; ext=".txt" ;;
        *) stem="$base" ;;
    esac
    while :; do
        case "$stem" in
            *-phase2) stem="${stem%-phase2}" ;;
            *-phase3) stem="${stem%-phase3}" ;;
            *-retry) stem="${stem%-retry}" ;;
            *) break ;;
        esac
    done
    printf '%s%s' "$stem" "$ext"
}

is_static_reviewer_basename() {
    local base
    base=$(normalize_reviewer_output_base "$1")
    case "$base" in
        cursor-specialist-*-output.txt|codex-specialist-*-output.txt) return 0 ;;
        *) return 1 ;;
    esac
}

output_file_is_success() {
    local file="$1"
    [[ -s "$file" ]] || return 1
    if grep -Eq '(^|[^A-Z_])NOT_SUBSTANTIVE([^A-Z_]|$)' "$file" 2>/dev/null; then
        return 1
    fi
    return 0
}

# Count slots whose STATUS != OK and STATUS != cap_hit. Slots that never launched
# because the vendor was unhealthy are counted via INTENDED_SLOTS - LAUNCHED_SLOTS
# (the orchestrator passes --launched-slots when known; otherwise we use the
# parse result as the actual count and assume no never-launched slots).
SUCCEEDED_SLOTS=0
FAILED_SLOTS=0
COUNTED_SLOTS=0
NOT_SUBSTANTIVE_SLOTS=0
DROPPED_STATIC_SLOTS=0
COUNTED_BASES_FILE=$(mktemp "${TMPDIR:-/tmp}/review-threshold-counted.XXXXXX")
COUNTED_STATUS_FILE=$(mktemp "${TMPDIR:-/tmp}/review-threshold-status.XXXXXX")
trap 'rm -f "$COUNTED_BASES_FILE" "$COUNTED_STATUS_FILE"' EXIT

status_is_success() {
    case "$1" in
        OK|cap_hit) return 0 ;;
        *) return 1 ;;
    esac
}

counted_status_for_base() {
    local base="$1"
    awk -F '\t' -v base="$base" '$1 == base { print $2; exit }' "$COUNTED_STATUS_FILE" 2>/dev/null || true
}

replace_counted_status() {
    local base="$1" status="$2" tmp
    tmp=$(mktemp "${TMPDIR:-/tmp}/review-threshold-status-replace.XXXXXX")
    awk -F '\t' -v base="$base" '$1 != base { print }' "$COUNTED_STATUS_FILE" > "$tmp"
    printf '%s\t%s\n' "$base" "$status" >> "$tmp"
    mv -f "$tmp" "$COUNTED_STATUS_FILE"
}

count_static_status_once() {
    local base="$1" status="$2" old_status
    old_status=$(counted_status_for_base "$base")
    if [[ -z "$old_status" ]]; then
        printf '%s\n' "$base" >> "$COUNTED_BASES_FILE"
        printf '%s\t%s\n' "$base" "$status" >> "$COUNTED_STATUS_FILE"
        COUNTED_SLOTS=$((COUNTED_SLOTS + 1))
        if status_is_success "$status"; then
            SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS + 1))
        else
            FAILED_SLOTS=$((FAILED_SLOTS + 1))
            [[ "$status" == "NOT_SUBSTANTIVE" ]] && NOT_SUBSTANTIVE_SLOTS=$((NOT_SUBSTANTIVE_SLOTS + 1))
        fi
        return 0
    fi
    if ! status_is_success "$old_status" && status_is_success "$status"; then
        FAILED_SLOTS=$((FAILED_SLOTS - 1))
        [[ "$old_status" == "NOT_SUBSTANTIVE" ]] && NOT_SUBSTANTIVE_SLOTS=$((NOT_SUBSTANTIVE_SLOTS - 1))
        SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS + 1))
        replace_counted_status "$base" "$status"
    elif status_is_success "$old_status" && ! status_is_success "$status"; then
        SUCCEEDED_SLOTS=$((SUCCEEDED_SLOTS - 1))
        FAILED_SLOTS=$((FAILED_SLOTS + 1))
        [[ "$status" == "NOT_SUBSTANTIVE" ]] && NOT_SUBSTANTIVE_SLOTS=$((NOT_SUBSTANTIVE_SLOTS + 1))
        replace_counted_status "$base" "$status"
    fi
}

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
                count_static_status_once "$(normalize_reviewer_output_base "$current_base")" "$current_status"
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
            count_static_status_once "$(normalize_reviewer_output_base "$current_base")" "$current_status"
        fi
    fi
fi

if (( ${#REVIEWER_OUTPUT_FILES[@]} > 0 )); then
    for reviewer_output_file in "${REVIEWER_OUTPUT_FILES[@]}"; do
        reviewer_base=$(basename "$reviewer_output_file")
        if ! is_static_reviewer_basename "$reviewer_base"; then
            continue
        fi
        normalized_base=$(normalize_reviewer_output_base "$reviewer_base")
        if output_file_is_success "$reviewer_output_file"; then
            count_static_status_once "$normalized_base" OK
        else
            count_static_status_once "$normalized_base" ERROR
        fi
    done
fi

if [[ -n "$DROPPED_SLOTS_FILE" && -s "$DROPPED_SLOTS_FILE" ]]; then
    while IFS=$'\t' read -r dropped_slot _dropped_tool _dropped_reason _dropped_snippet || [[ -n "$dropped_slot" ]]; do
        [[ -n "$dropped_slot" ]] || continue
        if is_dynamic_slot_name "$dropped_slot"; then
            continue
        fi
        dropped_base=""
        case "$_dropped_tool" in
            codex|cursor) dropped_base="${_dropped_tool}-specialist-${dropped_slot}-output.txt" ;;
        esac
        if [[ -z "$dropped_base" ]]; then
            continue
        fi
        dropped_base=$(normalize_reviewer_output_base "$dropped_base")
        if grep -Fxq "$dropped_base" "$COUNTED_BASES_FILE" 2>/dev/null; then
            continue
        fi
        printf '%s\n' "$dropped_base" >> "$COUNTED_BASES_FILE"
        FAILED_SLOTS=$((FAILED_SLOTS + 1))
        DROPPED_STATIC_SLOTS=$((DROPPED_STATIC_SLOTS + 1))
    done < "$DROPPED_SLOTS_FILE"
fi

# Add never-launched slots as failures (vendor unhealthy → slot never dispatched).
if [[ -n "$LAUNCHED_SLOTS" ]]; then
    case "$LAUNCHED_SLOTS" in ''|*[!0-9]*) larch_err "check-reviewer-failure-threshold.sh: --launched-slots must be a non-negative integer"; exit 2 ;; esac
    NEVER_LAUNCHED=$(( INTENDED_SLOTS - LAUNCHED_SLOTS ))
    (( NEVER_LAUNCHED < 0 )) && NEVER_LAUNCHED=0
    UNACCOUNTED_NEVER_LAUNCHED=$(( NEVER_LAUNCHED - DROPPED_STATIC_SLOTS ))
    (( UNACCOUNTED_NEVER_LAUNCHED < 0 )) && UNACCOUNTED_NEVER_LAUNCHED=0
    FAILED_SLOTS=$(( FAILED_SLOTS + UNACCOUNTED_NEVER_LAUNCHED ))
fi

# Threshold: >50% of intended panel size.
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
emit_kv DROPPED_STATIC_SLOTS "$DROPPED_STATIC_SLOTS"
emit_kv THRESHOLD_OK "$THRESHOLD_OK"
emit_kv THRESHOLD_REASON "$THRESHOLD_REASON"
