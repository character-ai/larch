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
    local helper state_file _out _rc
    local _buf="" _lqrd_line
    helper="$LARCH_LIB_QUIET_DIR/redact-secrets.sh"
    # Buffer stdin with bash built-ins (no external cat dependency).
    while IFS= read -r _lqrd_line || [ -n "$_lqrd_line" ]; do
        _buf="$_buf$_lqrd_line"$'\n'
    done
    _buf="${_buf%$'\n'}"
    if [ ! -x "$helper" ]; then
        printf 'WARN larch_err-redaction-unavailable\n'
        printf '%s\n' "$_buf"
        return 0
    fi
    state_file="$(larch_quiet_redaction_state_file)"
    set +e
    _out=$(printf '%s\n' "$_buf" | "$helper" --streaming --state-file "$state_file" 2>/dev/null)
    _rc=$?
    set -e
    if [ "$_rc" -ne 0 ]; then
        # Redactor failed: surface warning and fall back to original content
        # so the message is not silently lost.
        printf 'WARN larch_err-redaction-failed\n'
        printf '%s\n' "$_buf"
    else
        printf '%s\n' "$_out"
    fi
}

larch_quiet_write_diagnostic_stream() {
    local _lqwd_line
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
        while IFS= read -r _lqwd_line || [ -n "$_lqwd_line" ]; do
            printf '%s\n' "$_lqwd_line" >&2
            printf '%s\n' "$_lqwd_line" >&4
        done || true
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
# passed through redact-secrets.sh --streaming before surfacing.
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
