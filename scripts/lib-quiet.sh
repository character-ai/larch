# shellcheck shell=bash
# shellcheck disable=SC2317
# Shared stdout/stderr quieting helpers for larch shell scripts.
#
# Source this file, then call larch_quiet_init near the top of an executable
# script. After init, ordinary stdout/stderr goes to a per-process log file;
# machine-readable contract output must use emit or emit_kv.

if [ "${LARCH_LIB_QUIET_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_QUIET_LOADED=1

larch_quiet_truthy() {
    case "${1:-}" in
        1|true|TRUE|True|yes|YES|Yes|on|ON|On) return 0 ;;
        *) return 1 ;;
    esac
}

larch_quiet_default_log() {
    local base script tmp
    base="${0##*/}"
    script=${base:-larch-script}
    if [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -d "$IMPLEMENT_TMPDIR" ]; then
        tmp="$IMPLEMENT_TMPDIR"
    elif [ -n "${REVIEW_TMPDIR:-}" ] && [ -d "$REVIEW_TMPDIR" ]; then
        tmp="$REVIEW_TMPDIR"
    elif [ -n "${DESIGN_TMPDIR:-}" ] && [ -d "$DESIGN_TMPDIR" ]; then
        tmp="$DESIGN_TMPDIR"
    else
        tmp="${TMPDIR:-/tmp}"
    fi
    printf '%s/larch-quiet-%s-%s.log\n' "$tmp" "$script" "$$"
}

larch_quiet_init() {
    local log_file log_dir

    if larch_quiet_truthy "${LARCH_QUIET_DISABLE:-}"; then
        return 0
    fi
    # ACTIVE=1 without LARCH_QUIET_PID is not a bound quiet session (e.g. a
    # stray env export): do not redirect ordinary stdout. A subprocess that
    # inherits a real parent session always has LARCH_QUIET_PID set to the
    # parent's PID (≠ $$), so it still runs full init below.
    if larch_quiet_truthy "${LARCH_QUIET_ACTIVE:-}" && [ -z "${LARCH_QUIET_PID:-}" ]; then
        return 0
    fi
    # Use PID as the idempotency key so subprocess re-initialization is correct.
    # Inheriting LARCH_QUIET_ACTIVE=1 from a parent must NOT skip init in the
    # child: the child's FD1 may differ (command substitution, file redirect),
    # and exec 3>&1 must capture the child's current FD1 so emit/emit_kv route
    # contract output to the child's immediate caller, not the grandparent.
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        return 0
    fi

    log_file="${LARCH_QUIET_LOG_FILE:-${LARCH_QUIET_LOG:-}}"
    if [ -z "$log_file" ]; then
        log_file=$(larch_quiet_default_log)
    fi
    case "$log_file" in
        */*) log_dir="${log_file%/*}"; [ -n "$log_dir" ] || log_dir="/" ;;
        *) log_dir="." ;;
    esac
    mkdir -p "$log_dir" 2>/dev/null || return 0
    : > "$log_file" 2>/dev/null || return 0

    exec 3>&1
    exec 4>&2
    export LARCH_QUIET_ACTIVE=1
    export LARCH_QUIET_PID=$$
    export LARCH_QUIET_LOG_FILE="$log_file"
    exec >>"$log_file" 2>&1
}

# User-visible diagnostics (argv validation, fatals): still go to the process's
# original stderr after larch_quiet_init redirects FD 1/2 to the quiet log.
larch_err() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s\n' "$*" >&4
    else
        printf '%s\n' "$*" >&2
    fi
}

# shellcheck disable=SC2059 # callers pass fixed format strings (like printf)
larch_errf() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf "$@" >&4
    else
        printf "$@" >&2
    fi
}

emit() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s\n' "$*" >&3
    else
        printf '%s\n' "$*"
    fi
}

emit_kv() {
    local key=$1 value=${2-}
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        printf '%s=%s\n' "$key" "$value" >&3
    else
        printf '%s=%s\n' "$key" "$value"
    fi
}

emit_breadcrumb() {
    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        local breadcrumb_fd="${LARCH_QUIET_BREADCRUMB_FD:-}"
        if [[ "$breadcrumb_fd" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$*" >&"$breadcrumb_fd"
        else
            larch_err "$*"
        fi
    else
        printf '%s\n' "$*"
    fi
}
