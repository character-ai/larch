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

# FD-3 visible to harness (tty or pipe) — used with LARCH_BREADCRUMBS_SURFACED_FILE.
larch_quiet_fd3_is_visible() {
    if test -t 3 2>/dev/null; then
        return 0
    fi
    if [ -e /dev/fd/3 ] && [ -p /dev/fd/3 ]; then
        return 0
    fi
    return 1
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

    if [ -n "${LARCH_BREADCRUMBS_SURFACED_FILE:-}" ] && larch_quiet_fd3_is_visible; then
        printf 'surfaced\n' >"$LARCH_BREADCRUMBS_SURFACED_FILE" 2>/dev/null || true
    fi
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

larch_quiet_bc_valid_category() {
    case "$1" in
        progress|warn|stall|retry|escalate|wait-ci|network-flake) return 0 ;;
        *) return 1 ;;
    esac
}

larch_quiet__exit_write_done() {
    local _rc=$1
    if [ "${LARCH_DONE_OWNER_PID:-}" != "$$" ]; then
        return 0
    fi
    if [ -z "${LARCH_STATUS_FILE:-}" ] || [ -z "${LARCH_DONE_SENTINEL:-}" ]; then
        return 0
    fi
    printf 'EXIT_CODE=%s\n' "$_rc" >"${LARCH_STATUS_FILE}.tmp.$$" 2>/dev/null || return 0
    mv -f "${LARCH_STATUS_FILE}.tmp.$$" "${LARCH_STATUS_FILE}" 2>/dev/null || return 0
    printf 'EXIT_CODE=%s\n' "$_rc" >"${LARCH_DONE_SENTINEL}.tmp.$$" 2>/dev/null || return 0
    mv -f "${LARCH_DONE_SENTINEL}.tmp.$$" "${LARCH_DONE_SENTINEL}" 2>/dev/null || true
}

larch_quiet__exit_combo() {
    local _ec=$?
    larch_quiet__exit_write_done "$_ec"
    if [ -n "${LARCH_QUIET_PREV_EXIT_TRAP:-}" ]; then
        eval "$LARCH_QUIET_PREV_EXIT_TRAP" || true
    fi
    return "$_ec"
}

# Append PID-keyed done sentinel + atomic status write to the current EXIT trap.
larch_quiet_append_done_trap() {
    if [ -z "${LARCH_DONE_SENTINEL:-}" ] || [ -z "${LARCH_STATUS_FILE:-}" ]; then
        return 0
    fi
    export LARCH_DONE_OWNER_PID=$$
    local _raw _body
    _raw=$(trap -p EXIT 2>/dev/null || true)
    _body=""
    case "$_raw" in
        trap\'\'EXIT) ;;
        trap'--'*) _body=$(printf '%s\n' "$_raw" | LC_ALL=C sed -n "s/^trap -- '\\(.*\\)' EXIT\$/\\1/p") ;;
        *) _body=$(printf '%s\n' "$_raw" | LC_ALL=C sed -n 's/^trap -- "\(.*\)" EXIT$/\1/p') ;;
    esac
    if [ -n "$_body" ]; then
        export LARCH_QUIET_PREV_EXIT_TRAP="$_body"
    else
        unset LARCH_QUIET_PREV_EXIT_TRAP
    fi
    trap 'larch_quiet__exit_combo' EXIT
}

# emit_breadcrumb [--category=NAME] TEXT
# When LARCH_BREADCRUMB_STREAM is set, --category is required (fixed vocabulary).
# Without stream: legacy behavior (category ignored for stream; still logs text).
emit_breadcrumb() {
    local _bc_cat="" _bc_text=""
    while [ $# -gt 0 ]; do
        case "$1" in
            --category=*)
                _bc_cat="${1#--category=}"
                shift
                ;;
            --category)
                _bc_cat="${2:-}"
                shift 2
                ;;
            *)
                break
                ;;
        esac
    done
    _bc_text="$*"
    _bc_text="${_bc_text//$'\n'/ }"

    if larch_quiet_truthy "${LARCH_QUIET_DISABLE:-}"; then
        if [ -n "${LARCH_BREADCRUMB_STREAM:-}" ]; then
            :
        else
            if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
                local breadcrumb_fd="${LARCH_QUIET_BREADCRUMB_FD:-}"
                if [[ "$breadcrumb_fd" =~ ^[0-9]+$ ]]; then
                    printf '%s\n' "$_bc_text" >&"$breadcrumb_fd"
                else
                    emit "$_bc_text"
                fi
            else
                printf '%s\n' "$_bc_text"
            fi
        fi
        return 0
    fi

    if [ -n "${LARCH_BREADCRUMB_STREAM:-}" ]; then
        if [ -z "$_bc_cat" ]; then
            larch_err "WARN unknown-category=<missing> emit_breadcrumb requires --category when LARCH_BREADCRUMB_STREAM is set"
        elif ! larch_quiet_bc_valid_category "$_bc_cat"; then
            larch_err "WARN unknown-category=${_bc_cat} (dropped from stream)"
        else
            local _rec _ts
            _ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || printf 'na')
            _rec=$(printf 'larch:bc t=%s d=%s p=%s s=%s c=%s text=%s' \
                "$_ts" "${LARCH_BC_DEPTH:-0}" "$$" "${0##*/}" "$_bc_cat" "$_bc_text")
            if [ "${#_rec}" -gt 1024 ]; then
                _rec=$(printf '%s' "$_rec" | cut -c1-1020)
                _rec="${_rec}..."
                larch_err "WARN truncated breadcrumb record (>1KiB cap)"
            fi
            mkdir -p "$(dirname "$LARCH_BREADCRUMB_STREAM")" 2>/dev/null || true
            if ! printf '%s\n' "$_rec" >>"$LARCH_BREADCRUMB_STREAM" 2>/dev/null; then
                larch_err "WARN breadcrumb-stream-write-failed"
            fi
        fi
    fi

    if larch_quiet_truthy "${LARCH_QUIET_BREADCRUMBS:-}"; then
        local breadcrumb_fd="${LARCH_QUIET_BREADCRUMB_FD:-}"
        if [[ "$breadcrumb_fd" =~ ^[0-9]+$ ]]; then
            printf '%s\n' "$_bc_text" >&"$breadcrumb_fd"
        else
            emit "$_bc_text"
        fi
    else
        printf '%s\n' "$_bc_text"
    fi
}
