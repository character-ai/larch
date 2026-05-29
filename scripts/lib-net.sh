# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ "${LARCH_LIB_NET_LOADED:-}" == "1" ]]; then
    return 0
fi

is_transient_net_signature() {
    local text="$1"
    case "$text" in
        *"no such hosted"*) return 1 ;;
        *"Could not resolve"*|*"unable to access"*|*"Connection refused"*|\
        *"Temporary failure"*|*"timed out"*|*"TLS handshake"*|*"HTTP 5"*|\
        *"network/auth issue"*|*"connection reset"*|*"Connection reset by peer"*|\
        *"EOF"*"during"*|*"context deadline exceeded"*|*"no valid output 3 times"*|\
        *"git fetch"*"failed"*|*"lookup"*"no such host"*|*"no such host"*) return 0 ;;
        *) return 1 ;;
    esac
}

transient_envelope_predicate_none() {
    return 1
}

# Retry helper: up to 3 attempts; transient if predicate(content) returns true,
# OR (non-zero rc AND net signature on fail_file content). Returns _WTR_RC on
# exhaustion instead of exiting. Sleeps 2s before attempt 2 and 4s before attempt 3.
# $1=predicate name, $2=fail_file path, $3..$n command+args. Sets _WTR_OUT and _WTR_RC.
with_transient_retry() {
    local pred=$1 ff=$2 attempt=1 transient=0 ff_content
    local _lib_net_dir
    _lib_net_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    shift 2
    _WTR_OUT=""
    _WTR_RC=0
    while [ "$attempt" -le 3 ]; do
        : > "$ff"
        if _WTR_OUT=$("$@" 2>>"$ff"); then
            _WTR_RC=0
        else
            _WTR_RC=$?
        fi
        printf '%s\n' "$_WTR_OUT" >> "$ff"
        ff_content=$(cat "$ff" 2>/dev/null || true)
        transient=0
        if "$pred" "$ff_content"; then
            transient=1
        fi
        if [ "$transient" -eq 0 ] && [ "$_WTR_RC" -ne 0 ] && is_transient_net_signature "$ff_content"; then
            transient=1
        fi
        if [ "$transient" -eq 0 ]; then
            return "$_WTR_RC"
        fi
        if [ "$attempt" -eq 3 ]; then
            return "$_WTR_RC"
        fi
        if [ -x "${SLEEP_SCRIPT_DIR:-$_lib_net_dir}/sleep-seconds.sh" ]; then
            "${SLEEP_SCRIPT_DIR:-$_lib_net_dir}/sleep-seconds.sh" "$((attempt * 2))" >/dev/null 2>&1 || sleep "$((attempt * 2))"
        else
            sleep "$((attempt * 2))"
        fi
        attempt=$((attempt + 1))
    done
    return "$_WTR_RC"
}

LARCH_LIB_NET_LOADED=1
