# shellcheck shell=bash
# shellcheck disable=SC2317
# Shared scope-anchor relay gating and path validation contracts.
if [ "${LARCH_LIB_SCOPE_ANCHOR_HANDOFF_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_SCOPE_ANCHOR_HANDOFF_LOADED=1

larch_scope_anchor_relay_allowed() {
    case "${TALLY_PLAN_REVIEW_STATUS:-}" in
        ok|main-agent-vote-required) ;;
        *) return 1 ;;
    esac
    case "${LOOP_STATUS:-}" in
        complete|main-agent-vote-required) return 0 ;;
        *) return 1 ;;
    esac
}

larch_scope_anchor_common_shape_ok() {
    local file="$1" size
    case "$file" in
        *$'\n'*|*$'\r'*) return 1 ;;
    esac
    [[ -f "$file" && ! -L "$file" && -r "$file" && -s "$file" ]] || return 1
    size=$(wc -c <"$file" 2>/dev/null | awk '{print $1}' || printf '65537')
    case "$size" in ''|*[!0-9]*) size=65537 ;; esac
    [[ "$size" -le 65536 ]] || return 1
    return 0
}

larch_scope_anchor_canonical_path() {
    local file="$1" anchor_dir
    anchor_dir="$(cd "$(dirname "$file")" && pwd -P)" || return 1
    printf '%s/%s' "$anchor_dir" "$(basename "$file")"
}

larch_scope_anchor_under_root() {
    local canon="$1" root="$2"
    [[ -n "$root" ]] || return 1
    case "$canon" in
        "$root"/*|"$root") return 0 ;;
        *) return 1 ;;
    esac
}

larch_scope_anchor_tmp_or_cache_ok() {
    local canon="$1" xdg_cache cache_canon
    case "$canon" in
        /tmp/*|/private/tmp/*|/var/folders/*|/private/var/folders/*) return 0 ;;
    esac
    xdg_cache="${XDG_CACHE_HOME:-$HOME/.cache}"
    if cache_canon="$(cd "$xdg_cache" 2>/dev/null && pwd -P)"; then
        case "$canon" in
            "$cache_canon"/larch/sessions/*) return 0 ;;
        esac
    fi
    return 1
}

# stdout: canonical path; return 0 when allowed and valid, 1 otherwise
larch_scope_anchor_validate_design() {
    local file="$1" design_canon="$2" canon
    larch_scope_anchor_common_shape_ok "$file" || return 1
    canon="$(larch_scope_anchor_canonical_path "$file")" || return 1
    larch_scope_anchor_under_root "$canon" "$design_canon" || return 1
    printf '%s\n' "$canon"
}

# stdout: canonical path; return 0 when allowed and valid, 1 otherwise
larch_scope_anchor_validate_voter() {
    local file="$1" repo_root="$2" canon
    larch_scope_anchor_common_shape_ok "$file" || return 1
    canon="$(larch_scope_anchor_canonical_path "$file")" || return 1
    if larch_scope_anchor_under_root "$canon" "$repo_root"; then
        printf '%s\n' "$canon"
        return 0
    fi
    if larch_scope_anchor_tmp_or_cache_ok "$canon"; then
        printf '%s\n' "$canon"
        return 0
    fi
    return 1
}

# stdout: canonical path; return 0 when allowed and valid, 1 otherwise
larch_scope_anchor_validate_review() {
    local file="$1" review_canon="$2" canon
    larch_scope_anchor_common_shape_ok "$file" || return 1
    canon="$(larch_scope_anchor_canonical_path "$file")" || return 1
    if larch_scope_anchor_under_root "$canon" "$review_canon"; then
        printf '%s\n' "$canon"
        return 0
    fi
    if larch_scope_anchor_tmp_or_cache_ok "$canon"; then
        printf '%s\n' "$canon"
        return 0
    fi
    return 1
}

# stdout: canonical path when re-tally relay gates pass; otherwise prints nothing
larch_scope_anchor_retally_handoff_value() {
    local design_canon="$1" parsed_input="$2" retally_input="$3" canon
    larch_scope_anchor_relay_allowed || return 0
    if [[ -n "$parsed_input" ]]; then
        if canon="$(larch_scope_anchor_validate_design "$parsed_input" "$design_canon" 2>/dev/null)"; then
            printf '%s' "$canon"
            return 0
        fi
    fi
    if [[ -n "$retally_input" ]]; then
        if canon="$(larch_scope_anchor_validate_design "$retally_input" "$design_canon" 2>/dev/null)"; then
            printf '%s' "$canon"
            return 0
        fi
    fi
    return 0
}

# stdout: canonical path when relay gates pass; otherwise prints nothing
larch_scope_anchor_design_handoff_value() {
    local design_canon="$1" candidate canon
    shift
    larch_scope_anchor_relay_allowed || return 0
    for candidate in "$@"; do
        [[ -n "$candidate" ]] || continue
        if canon="$(larch_scope_anchor_validate_design "$candidate" "$design_canon" 2>/dev/null)"; then
            printf '%s' "$canon"
            return 0
        fi
    done
    return 0
}
