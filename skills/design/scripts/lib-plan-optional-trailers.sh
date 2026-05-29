#!/usr/bin/env bash
# Shared optional-trailer helpers for plan-size gating and revision preservation.

_LIB_PLAN_OPTIONAL_TRAILERS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
LARCH_PLAN_OPTIONAL_TRAILERS_AWK="$_LIB_PLAN_OPTIONAL_TRAILERS_DIR/lib-plan-optional-trailers.awk"

_plan_optional_trailer_nr() {
    awk 'NF { nr = NR } END { print nr + 0 }' "$1"
}

_optional_trailer_values_file() {
    printf '%s.values' "$1"
}

snapshot_optional_trailer_keys() {
    local plan="$1" out="$2"
    awk -v mode=keys -v trailer_nr="$(_plan_optional_trailer_nr "$plan")" \
        -f "$LARCH_PLAN_OPTIONAL_TRAILERS_AWK" "$plan" >"$out"
    snapshot_optional_trailer_values "$plan" "$(_optional_trailer_values_file "$out")"
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

plan_has_any_optional_trailer() {
    local plan="$1"
    plan_has_optional_trailer_key "$plan" diff_added && return 0
    plan_has_optional_trailer_key "$plan" diff_deleted && return 0
    plan_has_optional_trailer_key "$plan" mechanical_churn && return 0
    return 1
}

parse_plan_optional_metadata() {
    local plan="$1"
    awk -v mode=parse -v trailer_nr="$(_plan_optional_trailer_nr "$plan")" \
        -f "$LARCH_PLAN_OPTIONAL_TRAILERS_AWK" "$plan"
}

validate_optional_trailer_keys_preserved() {
    local plan="$1" keys_file="$2"
    local key
    [[ -f "$keys_file" ]] || return 0

    if [[ ! -s "$keys_file" ]]; then
        if plan_has_any_optional_trailer "$plan"; then
            return 1
        fi
        return 0
    fi

    while IFS= read -r key || [[ -n "$key" ]]; do
        [[ -n "$key" ]] || continue
        plan_has_optional_trailer_key "$plan" "$key" || return 1
    done <"$keys_file"
    return 0
}

validate_optional_trailers_preserved() {
    local plan="$1" keys_file="$2"
    local values_file probe
    validate_optional_trailer_keys_preserved "$plan" "$keys_file" || return 1

    values_file=$(_optional_trailer_values_file "$keys_file")
    if [[ -f "$values_file" ]]; then
        probe=$(mktemp "$(dirname "$values_file")/.optional-trailer-values-current.XXXXXX")
        snapshot_optional_trailer_values "$plan" "$probe"
        if ! cmp -s "$values_file" "$probe"; then
            rm -f "$probe"
            return 1
        fi
        rm -f "$probe"
    fi
    return 0
}

# Mechanical dedup with optional-trailer snapshot validation.
# keys_file must exist (may be empty); companion .values written by snapshot_optional_trailer_keys.
# Exit 0: success (prints dedup breadcrumb to stdout)
# Exit 1: optional trailer keys/values lost during dedup (plan restored when trailers were snapshotted)
# Exit 2: dedup-plan-lines.py failure (plan restored when pre-dedup snapshot existed)
dedup_plan_preserve_optional_trailers() {
    local plan_path="$1" keys_file="$2" design_tmpdir="$3" dedup_py="$4"
    local pre_dedup_snapshot dedup_tmp dedup_removed

    pre_dedup_snapshot=""
    if [[ -s "$keys_file" ]]; then
        pre_dedup_snapshot=$(mktemp "$design_tmpdir/.plan-pre-dedup.XXXXXX")
        cp -f "$plan_path" "$pre_dedup_snapshot"
    fi

    dedup_tmp=$(mktemp "$design_tmpdir/.plan-dedup.XXXXXX")
    if ! dedup_removed=$(python3 "$dedup_py" "$plan_path" "$dedup_tmp"); then
        rm -f "$dedup_tmp"
        if [[ -n "$pre_dedup_snapshot" ]]; then
            cp -f "$pre_dedup_snapshot" "$plan_path"
        fi
        rm -f "$pre_dedup_snapshot"
        return 2
    fi
    if [[ ! "$dedup_removed" =~ ^[0-9]+$ ]]; then
        rm -f "$dedup_tmp"
        if [[ -n "$pre_dedup_snapshot" ]]; then
            cp -f "$pre_dedup_snapshot" "$plan_path"
        fi
        rm -f "$pre_dedup_snapshot"
        return 2
    fi
    mv -f "$dedup_tmp" "$plan_path"
    printf 'dedup-sweep: removed %s duplicate line(s) from plan.txt\n' "${dedup_removed:-0}"

    if ! validate_optional_trailers_preserved "$plan_path" "$keys_file"; then
        if [[ -n "$pre_dedup_snapshot" ]]; then
            cp -f "$pre_dedup_snapshot" "$plan_path"
        fi
        rm -f "$pre_dedup_snapshot"
        return 1
    fi

    rm -f "$pre_dedup_snapshot"
    return 0
}
