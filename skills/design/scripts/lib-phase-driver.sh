# shellcheck shell=bash
# Shared phase-driver primitives for /design Step 3+ drivers (sourced only; no shebang).

if [[ "${LARCH_LIB_PHASE_DRIVER_LOADED:-}" == "1" ]]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_PHASE_DRIVER_LOADED=1

_LPD_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib-quiet.sh
source "$_LPD_SCRIPT_DIR/../../../scripts/lib-quiet.sh"

phase_driver_session_get() {
    local file="$1" key="$2" default_value="${3-}" value
    value=$(awk -v k="$key" 'BEGIN{kl=length(k)} substr($0,1,kl)==k && substr($0,kl+1,1)=="=" {print substr($0,kl+2); exit}' "$file" 2>/dev/null || true)
    if [[ -z "$value" ]]; then
        printf '%s\n' "$default_value"
    else
        printf '%s\n' "$value"
    fi
}

phase_driver_resolve_plugin_root() {
    local script_dir="$1" session_env="${2:-}" root=""
    if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" ]]; then
        printf '%s\n' "$CLAUDE_PLUGIN_ROOT"
        return 0
    fi
    if [[ -n "$session_env" && -f "$session_env" ]]; then
        root="$(phase_driver_session_get "$session_env" LARCH_CLAUDE_PLUGIN_ROOT "")"
        if [[ -n "$root" ]]; then
            printf '%s\n' "$root"
            return 0
        fi
    fi
    (cd "$script_dir/../../.." && pwd -P)
}

phase_driver_write_result_env() {
    local path="$1"
    shift
    if [[ -L "$path" ]]; then
        larch_err "lib-phase-driver: refusing to write symlink result env: $path"
        return 1
    fi
    local tmp parent
    parent="${path%/*}"
    [[ -n "$parent" && "$parent" != "$path" ]] && mkdir -p "$parent"
    tmp="$(mktemp "${path}.XXXXXX")" || return 1
    : >"$tmp"
    local kv
    for kv in "$@"; do
        printf '%s\n' "$kv" >>"$tmp"
    done
    mv "$tmp" "$path"
}

phase_driver_read_result_env() {
    local path="$1"
    shift
    local -a allowlist=("$@")
    local line key value allowed
    if [[ ! -f "$path" ]] || [[ -L "$path" ]]; then
        return 1
    fi
    while IFS= read -r line || [[ -n "$line" ]]; do
        key="${line%%=*}"
        value="${line#*=}"
        for allowed in "${allowlist[@]}"; do
            if [[ "$key" == "$allowed" ]]; then
                printf '%s=%s\n' "$key" "$value"
                break
            fi
        done
    done <"$path"
    return 0
}
