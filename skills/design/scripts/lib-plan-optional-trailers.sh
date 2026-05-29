#!/usr/bin/env bash
# Shared optional-trailer helpers for plan-size gating and revision preservation.

_LIB_PLAN_OPTIONAL_TRAILERS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
LARCH_PLAN_OPTIONAL_TRAILERS_AWK="$_LIB_PLAN_OPTIONAL_TRAILERS_DIR/lib-plan-optional-trailers.awk"

_plan_optional_trailer_nr() {
    awk 'NF { nr = NR } END { print nr + 0 }' "$1"
}

snapshot_optional_trailer_keys() {
    local plan="$1" out="$2"
    awk -v mode=keys -v trailer_nr="$(_plan_optional_trailer_nr "$plan")" \
        -f "$LARCH_PLAN_OPTIONAL_TRAILERS_AWK" "$plan" >"$out"
}

snapshot_optional_trailer_values() {
    local plan="$1" out="$2"
    awk -v mode=values -v trailer_nr="$(_plan_optional_trailer_nr "$plan")" \
        -f "$LARCH_PLAN_OPTIONAL_TRAILERS_AWK" "$plan" >"$out"
}

plan_has_optional_trailer_key() {
    local plan="$1" key="$2"
    awk -v mode=has_key -v key="$key" -v trailer_nr="$(_plan_optional_trailer_nr "$plan")" \
        -f "$LARCH_PLAN_OPTIONAL_TRAILERS_AWK" "$plan"
}

parse_plan_optional_metadata() {
    local plan="$1"
    awk -v mode=parse -v trailer_nr="$(_plan_optional_trailer_nr "$plan")" \
        -f "$LARCH_PLAN_OPTIONAL_TRAILERS_AWK" "$plan"
}

validate_optional_trailers_preserved() {
    local plan="$1" keys_file="$2" values_file="${3:-}"
    local key expect
    [[ -f "$keys_file" ]] || return 0
    while IFS= read -r key || [[ -n "$key" ]]; do
        [[ -n "$key" ]] || continue
        plan_has_optional_trailer_key "$plan" "$key" || return 1
    done <"$keys_file"
    [[ -f "$values_file" ]] || return 0
    local parsed parsed_added parsed_deleted parsed_mech
    parsed=$(parse_plan_optional_metadata "$plan")
    parsed_added=$(printf '%s\n' "$parsed" | sed -n '2p')
    parsed_deleted=$(printf '%s\n' "$parsed" | sed -n '3p')
    parsed_mech=$(printf '%s\n' "$parsed" | sed -n '4p')
    while IFS= read -r expect || [[ -n "$expect" ]]; do
        [[ -n "$expect" ]] || continue
        key="${expect%%=*}"
        expect="${expect#*=}"
        case "$key" in
            diff_added)
                [[ "$parsed_added" != "-" && "$parsed_added" == "$expect" ]] || return 1
                ;;
            diff_deleted)
                [[ "$parsed_deleted" != "-" && "$parsed_deleted" == "$expect" ]] || return 1
                ;;
            mechanical_churn)
                [[ "$parsed_mech" == "$expect" ]] || return 1
                ;;
            *) return 1 ;;
        esac
    done <"$values_file"
    return 0
}
