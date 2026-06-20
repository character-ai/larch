# shellcheck shell=bash
# shellcheck disable=SC2317
# Sourced-only: phantom untracked probe wrapper.

if [ "${LARCH_LIB_PHANTOM_PROBE_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_PHANTOM_PROBE_LOADED=1

_phantom_probe_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_phantom_plugin_root="$(cd "$_phantom_probe_script_dir/.." && pwd)"

# Usage: phantom_probe_with_warn <step-token>
phantom_probe_with_warn() {
    local step_token="$1"
    local ph_out line saw_status=0

    if [ -z "${IMPLEMENT_TMPDIR:-}" ]; then
        emit_kv PHANTOM_STATUS unknown
        emit_kv PHANTOM_REASON "IMPLEMENT_TMPDIR-unset"
        return 0
    fi

    ph_out=$(LARCH_QUIET_DISABLE=1 python3 "$_phantom_plugin_root/python/cli.py" git phantom-probe --step "$step_token" 2>/dev/null || true)
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            PHANTOM_STATUS=*|PHANTOM_REASON=*|PHANTOM_COUNT=*|PHANTOM_PATHS_FILE=*|PHANTOM_APPEND_WARN_ERROR=*)
                emit_kv "${line%%=*}" "${line#*=}"
                case "$line" in
                    PHANTOM_STATUS=*) saw_status=1 ;;
                esac
                ;;
        esac
    done <<<"$ph_out"
    if [ "$saw_status" -eq 0 ]; then
        emit_kv PHANTOM_STATUS unknown
        emit_kv PHANTOM_REASON probe-invocation-failed
    fi
    return 0
}
