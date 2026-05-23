#!/usr/bin/env bash
# lib-implement-round-cap.sh — shared Step 5 effective round-cap math for /implement.
# Bash 3.2 compatible. Sourced by run-step5-review.sh and review-and-fix.sh (loop mode).

# shellcheck disable=SC2034
if [[ -z "${_LIB_IMPLEMENT_ROUND_CAP_LOADED:-}" ]]; then
    _LIB_IMPLEMENT_ROUND_CAP_LOADED=1
fi

_lib_implement_round_cap_session_get() {
    local file="$1" key="$2" default_value="${3-}" value
    value=$(awk -v k="$key" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$file" 2>/dev/null || true)
    if [[ -z "$value" ]]; then
        printf '%s\n' "$default_value"
    else
        printf '%s\n' "$value"
    fi
}

# count_prior_degraded_rounds IMPLEMENT_TMPDIR CURRENT_ROUND
# Counts rounds r with 1 <= r < CURRENT_ROUND where round-r/review-and-fix.env
# contains DEGRADED_ROUND=true. Missing or unreadable env files contribute 0.
count_prior_degraded_rounds() {
    local implement_tmpdir="$1" current_round="$2"
    local round=0 count=0
    local degraded_file="" degraded_value=""

    for (( round = 1; round < current_round; round++ )); do
        degraded_file="$implement_tmpdir/round-${round}/review-and-fix.env"
        degraded_value=""
        if [[ -r "$degraded_file" ]]; then
            degraded_value="$(_lib_implement_round_cap_session_get "$degraded_file" DEGRADED_ROUND false)"
        fi
        if [[ "$degraded_value" == "true" ]]; then
            count=$((count + 1))
        fi
    done
    printf '%s\n' "$count"
}
