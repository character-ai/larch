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
LARCH_LIB_QUIET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

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
    elif [ -n "${RESEARCH_TMPDIR:-}" ] && [ -d "$RESEARCH_TMPDIR" ]; then
        tmp="$RESEARCH_TMPDIR"
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

# Strip C0 control bytes and DEL from a single diagnostic line (stdin).
# LC_ALL=C keeps tr byte-oriented on BSD/macOS with malformed input.
# Callers that forward EXTERNAL content into larch_err / larch_errf
# MUST pipe through this helper explicitly before doing so. Multi-line
# callers should pipe per line so LF boundaries survive.
sanitize_diagnostic_line() {
    LC_ALL=C tr -d '[:cntrl:]'
}

larch_quiet_redaction_state_file() {
    if [ -n "${LARCH_QUIET_REDACT_STATE_FILE:-}" ]; then
        printf '%s\n' "$LARCH_QUIET_REDACT_STATE_FILE"
        return 0
    fi
    printf '%s/larch-quiet-redact-%s.state\n' "${TMPDIR:-/tmp}" "$$"
}

larch_quiet_redact_diagnostic_stream() {
    local helper state_file
    helper="$LARCH_LIB_QUIET_DIR/lib-redact-streaming.sh"
    if [ ! -x "$helper" ]; then
        cat
        return 0
    fi
    state_file="$(larch_quiet_redaction_state_file)"
    if ! "$helper" --state-file "$state_file" 2>/dev/null; then
        printf 'WARN larch_err-redaction-failed\n'
    fi
}

larch_quiet_write_diagnostic_stream() {
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        tee >(cat >&4) >&2 || true
    else
        # Use bash built-in read/printf to avoid depending on external cat
        # (some test harnesses run with a PATH that excludes standard utilities).
        while IFS= read -r _lqwd_line || [ -n "$_lqwd_line" ]; do
            printf '%s\n' "$_lqwd_line" >&2
        done || true
    fi
}

# User-visible diagnostics (argv validation, fatals): go to the process's
# original stderr after larch_quiet_init redirects FD 1/2 to the quiet log, and
# are mirrored into the quiet log for failure-tail visibility. The text is
# passed through the streaming secret scrubber first so direct operator output
# keeps the same redaction family as breadcrumb-monitor lines.
larch_err() {
    printf '%s\n' "$*" | larch_quiet_redact_diagnostic_stream | larch_quiet_write_diagnostic_stream
    return 0
}

# shellcheck disable=SC2059 # callers pass fixed format strings (like printf)
larch_errf() {
    printf "$@" | larch_quiet_redact_diagnostic_stream | larch_quiet_write_diagnostic_stream
    return 0
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
    case "$value" in
        *$'\n'*|*$'\r'*)
            larch_err "emit_kv: value for key ${key} must not contain newline or carriage return"
            return 2
            ;;
    esac
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
    # Idempotent: if a parent process already owns the sentinel, skip to avoid
    # a nested subprocess (e.g. collect-agent-results.sh called inside ship-pr)
    # from prematurely signalling the breadcrumb-monitor on its own exit.
    if [ -n "${LARCH_DONE_OWNER_PID:-}" ] && [ "${LARCH_DONE_OWNER_PID}" != "$$" ]; then
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

larch_quiet_source_larch_log_lib() {
    if declare -F larch_log_breadcrumbs_under_session_tmp >/dev/null 2>&1; then
        return 0
    fi
    # shellcheck source=scripts/lib-larch-log.sh
    # shellcheck disable=SC1091
    source "$LARCH_LIB_QUIET_DIR/lib-larch-log.sh" >/dev/null 2>&1 || return 1
}

larch_quiet_warn_paired_pid_invalid() {
    larch_err "WARN paired-pid-file-invalid"
    return 0
}

larch_quiet_write_paired_pid_file() {
    local _path="${LARCH_PAIRED_PID_FILE:-}" _parent _tmp=""
    if [ -z "$_path" ]; then
        return 0
    fi
    case "$_path" in
        /*) ;;
        *) larch_quiet_warn_paired_pid_invalid; return 0 ;;
    esac
    case "$_path" in
        ../*|*/../*|*/..|..|*..*) larch_quiet_warn_paired_pid_invalid; return 0 ;;
    esac
    if [ -L "$_path" ]; then
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    if [ -e "$_path" ] && [ ! -f "$_path" ]; then
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    _parent="$(dirname "$_path")"
    if [ ! -d "$_parent" ] || [ ! -w "$_parent" ] || [ -L "$_parent" ]; then
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    if ! larch_quiet_source_larch_log_lib; then
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    if ! ( LARCH_LOG_ROOT="${LARCH_LOG_ROOT:-/.__larch_no_log_root__/larch-logs}" larch_log_breadcrumbs_under_session_tmp "$_path" >/dev/null 2>&1 ); then
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    _tmp="$(mktemp "${_path}.tmp.XXXXXX" 2>/dev/null)" || {
        larch_quiet_warn_paired_pid_invalid
        return 0
    }
    if ! printf '%s\n' "$$" >"$_tmp" 2>/dev/null; then
        rm -f "$_tmp" 2>/dev/null || true
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    if ! mv -f "$_tmp" "$_path" 2>/dev/null; then
        rm -f "$_tmp" 2>/dev/null || true
        larch_quiet_warn_paired_pid_invalid
        return 0
    fi
    return 0
}
