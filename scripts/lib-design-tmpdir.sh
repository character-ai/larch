# shellcheck shell=bash
# lib-design-tmpdir.sh - source-only validator for --design-tmpdir paths.

if [[ -n "${LARCH_LIB_DESIGN_TMPDIR_LOADED:-}" ]]; then
    return 0
fi
LARCH_LIB_DESIGN_TMPDIR_LOADED=1

_larch_design_tmpdir_allowlist=()

_larch_design_tmpdir_err() {
    if declare -F larch_err >/dev/null 2>&1; then
        larch_err "$@"
    else
        printf '%s\n' "$*" >&2
    fi
}

_larch_design_tmpdir_canonical_prefix() {
    local prefix="$1"
    local resolved=""

    if [[ -d "$prefix" ]]; then
        resolved=$(cd "$prefix" 2>/dev/null && pwd -P) || resolved=""
    fi
    if [[ -z "$resolved" ]]; then
        resolved="$prefix"
    fi
    printf '%s' "${resolved%/}/"
}

_larch_design_tmpdir_init_allowlist() {
    local xdg_cache tmpdir_prefix sessions_prefix

    if ((${#_larch_design_tmpdir_allowlist[@]} > 0)); then
        return 0
    fi

    xdg_cache="${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}"
    sessions_prefix="${xdg_cache%/}/larch/sessions/"
    _larch_design_tmpdir_allowlist+=("$(_larch_design_tmpdir_canonical_prefix "$sessions_prefix")")

    if [[ -n "${TMPDIR:-}" ]]; then
        tmpdir_prefix="${TMPDIR%/}/"
        _larch_design_tmpdir_allowlist+=("$(_larch_design_tmpdir_canonical_prefix "$tmpdir_prefix")")
    fi

    _larch_design_tmpdir_allowlist+=("$(_larch_design_tmpdir_canonical_prefix /tmp)")
}

_larch_design_tmpdir_split_ancestor_tail() {
    local candidate="$1"
    local path="$candidate"
    local tail=""

    while [[ "$path" != "/" && "${path: -1}" == "/" ]]; do
        path="${path%/}"
    done

    while [[ ! -e "$path" && "$path" != "/" ]]; do
        local base="${path##*/}"
        if [[ "$path" == "$base" ]]; then
            break
        fi
        if [[ -n "$base" ]]; then
            if [[ -n "$tail" ]]; then
                tail="${base}/${tail}"
            else
                tail="$base"
            fi
        fi
        path="${path%/*}"
        [[ -z "$path" ]] && path="/"
    done

    printf '%s\n%s' "$path" "$tail"
}

_larch_design_tmpdir_reject_controls() {
    local candidate="$1"

    if [[ "$candidate" == *$'\n'* || "$candidate" == *$'\r'* ]]; then
        _larch_design_tmpdir_err "design-tmpdir: path must not contain newline or carriage return"
        return 2
    fi
    return 0
}

_larch_design_tmpdir_reject_dot_segments() {
    local candidate="$1"
    local segment

    [[ -n "$candidate" ]] || return 0

    IFS='/' read -r -a _larch_design_tmpdir_segments <<< "$candidate"
    for segment in "${_larch_design_tmpdir_segments[@]}"; do
        case "$segment" in
            .|..)
                _larch_design_tmpdir_err "design-tmpdir: path must not contain '.' or '..' segments"
                return 2
                ;;
        esac
    done
    return 0
}

larch_design_tmpdir_validate() {
    local candidate="${1-}"
    local ancestor tail resolved_ancestor resolved_candidate resolved prefix matched split_output

    if [[ -z "$candidate" ]]; then
        _larch_design_tmpdir_err "design-tmpdir: path is required"
        return 2
    fi

    _larch_design_tmpdir_reject_controls "$candidate" || return $?

    _larch_design_tmpdir_init_allowlist

    split_output="$(_larch_design_tmpdir_split_ancestor_tail "$candidate")"
    ancestor="${split_output%%$'\n'*}"
    if [[ "$split_output" == *$'\n'* ]]; then
        tail="${split_output#*$'\n'}"
    else
        tail=""
    fi
    _larch_design_tmpdir_reject_dot_segments "$candidate" || return $?

    if ! resolved_ancestor=$(cd "$ancestor" 2>/dev/null && pwd -P); then
        _larch_design_tmpdir_err "design-tmpdir: parent resolution failed"
        return 2
    fi

    if [[ -n "$tail" ]]; then
        resolved_candidate="${resolved_ancestor%/}/${tail}"
    else
        resolved_candidate="$resolved_ancestor"
    fi

    resolved="$resolved_candidate"

    if [[ -e "$candidate" ]]; then
        if [[ -L "$candidate" && ! -d "$candidate" ]]; then
            _larch_design_tmpdir_err "design-tmpdir: leaf symlink must resolve to a directory"
            return 2
        fi
        if [[ ! -d "$candidate" ]]; then
            _larch_design_tmpdir_err "design-tmpdir: path must name a directory"
            return 2
        fi
        if resolved=$(cd "$resolved_candidate" 2>/dev/null && pwd -P); then
            :
        elif [[ -L "$candidate" ]]; then
            _larch_design_tmpdir_err "design-tmpdir: leaf symlink must resolve to a directory"
            return 2
        fi
    fi

    matched=false
    resolved_cmp="${resolved%/}/"
    for prefix in "${_larch_design_tmpdir_allowlist[@]}"; do
        case "$resolved_cmp" in
            "$prefix"*)
                matched=true
                break
                ;;
        esac
    done

    if [[ "$matched" != true ]]; then
        _larch_design_tmpdir_err "design-tmpdir: path not under allowlist after resolution: $resolved (allowed: ${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions/, \${TMPDIR}, /tmp)"
        return 2
    fi

    return 0
}
