# shellcheck shell=bash
# Sourced /design same-session re-entry guard. Bash 3.2-compatible.
# set -e intentionally omitted: callers control shell options for sourced libs.

DESIGN_REENTRY_MARKER_TTL_DEFAULT=300

_design_reentry_is_uint() {
    local value="${1:-}"
    [[ "$value" =~ ^[0-9]+$ ]]
}

_design_reentry_valid_inputs() {
    local issue_number="${1:-}" ppid="${2:-}" ttl="${3:-$DESIGN_REENTRY_MARKER_TTL_DEFAULT}"
    _design_reentry_is_uint "$issue_number" || return 1
    _design_reentry_is_uint "$ppid" || return 1
    _design_reentry_is_uint "$ttl" || return 1
    [ -n "${HOME:-}" ] || return 1
    return 0
}

design_reentry_marker_path() {
    local issue_number="${1:-}" ppid="${2:-}"
    if ! _design_reentry_valid_inputs "$issue_number" "$ppid" "$DESIGN_REENTRY_MARKER_TTL_DEFAULT"; then
        return 2
    fi
    printf '%s/.cache/larch/sessions/design-completed-%s-%s\n' "$HOME" "$issue_number" "$ppid"
}

_design_reentry_marker_mtime() {
    local marker_path="$1"
    local candidate=""

    if candidate=$(stat -c %Y "$marker_path" 2>/dev/null) && [[ "$candidate" =~ ^[0-9]+$ ]] && [ "$candidate" != "0" ]; then
        printf '%s\n' "$candidate"
        return 0
    fi
    candidate=""
    if candidate=$(stat -f %m "$marker_path" 2>/dev/null) && [[ "$candidate" =~ ^[0-9]+$ ]] && [ "$candidate" != "0" ]; then
        printf '%s\n' "$candidate"
        return 0
    fi
    return 1
}

design_reentry_marker_write() {
    local issue_number="${1:-}" ppid="${2:-}"
    local marker_path marker_dir err

    if ! _design_reentry_valid_inputs "$issue_number" "$ppid" "$DESIGN_REENTRY_MARKER_TTL_DEFAULT"; then
        printf '%s\n' 'MARKER_WRITE_FAILED=true REASON=invalid-input' >&2
        return 2
    fi
    marker_path=$(design_reentry_marker_path "$issue_number" "$ppid") || return $?
    marker_dir="${marker_path%/*}"

    err=""
    if ! err=$(mkdir -p "$marker_dir" 2>&1); then
        printf 'MARKER_WRITE_FAILED=true REASON=%s\n' "${err:-mkdir-failed}" >&2
        return 1
    fi
    err=""
    if ! err=$(touch "$marker_path" 2>&1); then
        printf 'MARKER_WRITE_FAILED=true REASON=%s\n' "${err:-touch-failed}" >&2
        return 1
    fi
    return 0
}

design_reentry_marker_hit() {
    local issue_number="${1:-}" ppid="${2:-}" ttl="${3:-$DESIGN_REENTRY_MARKER_TTL_DEFAULT}"
    local marker_path mtime now age

    if ! _design_reentry_valid_inputs "$issue_number" "$ppid" "$ttl"; then
        printf '%s\n' 'MARKER_HIT=false REASON=invalid-input'
        return 2
    fi
    marker_path=$(design_reentry_marker_path "$issue_number" "$ppid") || {
        printf '%s\n' 'MARKER_HIT=false REASON=invalid-input'
        return 2
    }

    if [ ! -f "$marker_path" ]; then
        printf '%s\n' 'MARKER_HIT=false REASON=absent'
        return 1
    fi

    mtime=$(_design_reentry_marker_mtime "$marker_path" || true)
    if [ -z "$mtime" ]; then
        printf '%s\n' 'MARKER_HIT=false REASON=absent'
        return 1
    fi

    now=$(date +%s)
    if ! _design_reentry_is_uint "$now"; then
        printf '%s\n' 'MARKER_HIT=false REASON=invalid-mtime'
        rm -f "$marker_path" 2>/dev/null || true
        return 1
    fi

    age=$((now - mtime))
    if [ "$age" -lt 0 ]; then
        printf '%s\n' 'MARKER_HIT=false REASON=invalid-mtime'
        rm -f "$marker_path" 2>/dev/null || true
        return 1
    fi
    if [ "$age" -ge "$ttl" ]; then
        printf 'MARKER_HIT=false REASON=stale MARKER_AGE=%s\n' "$age"
        rm -f "$marker_path" 2>/dev/null || true
        return 1
    fi

    printf 'MARKER_HIT=true MARKER_AGE=%s MARKER_TTL=%s\n' "$age" "$ttl"
    return 0
}
