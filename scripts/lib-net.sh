# shellcheck shell=bash
# Sourced-only library: no shebang and no `set -e`; callers own exit semantics.
if [[ "${LARCH_LIB_NET_LOADED:-}" == "1" ]]; then
    return 0
fi

is_transient_net_signature() {
    local text="$1"
    case "$text" in
        *"Could not resolve"*|*"unable to access"*|*"Connection refused"*|\
        *"Temporary failure"*|*"timed out"*|*"TLS handshake"*|*"HTTP 5"*|\
        *"network/auth issue"*|*"connection reset"*|*"EOF"*"during"*|\
        *"context deadline exceeded"*|*"no valid output 3 times"*|\
        *"git fetch"*"failed"*) return 0 ;;
        *) return 1 ;;
    esac
}

LARCH_LIB_NET_LOADED=1
