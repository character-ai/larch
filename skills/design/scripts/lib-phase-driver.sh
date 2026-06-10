# shellcheck shell=bash
# Shared phase-driver primitives for /design Step 3+ drivers (sourced only; no shebang).

if [[ "${LARCH_LIB_PHASE_DRIVER_LOADED:-}" == "1" ]]; then
    # shellcheck disable=SC2317 # Guard is reachable on repeated sourcing.
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

phase_driver_json_boolean_or_sed() {
    local file="$1" key="$2" default_value="${3:-false}" value=""
    if command -v jq >/dev/null 2>&1 && [[ -f "$file" ]]; then
        value=$(jq -r --arg key "$key" '
            if (.[$key] | type) == "boolean" then
                (.[$key] | tostring)
            elif (.[$key] | type) == "string" and (.[$key] == "true" or .[$key] == "false") then
                .[$key]
            else
                ""
            end
        ' "$file" 2>/dev/null || echo "")
    fi
    if [[ -z "$value" && -f "$file" ]]; then
        value=$(sed -n 's/.*"'"$key"'"[[:space:]]*:[[:space:]]*"\{0,1\}\(true\|false\)"\{0,1\}.*/\1/p' "$file" 2>/dev/null | head -1)
    fi
    case "$value" in
        true|false) printf '%s\n' "$value" ;;
        *) printf '%s\n' "$default_value" ;;
    esac
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
        case "$kv" in
            *$'\n'* | *$'\r'*)
                larch_err "lib-phase-driver: refusing to write result env value containing newline or carriage return"
                rm -f "$tmp"
                return 1
                ;;
        esac
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
        case "$line" in
            *=*) ;;
            *) continue ;;
        esac
        key="${line%%=*}"
        value="${line#*=}"
        for allowed in "${allowlist[@]}"; do
            if [[ "$key" == "$allowed" ]]; then
                case "$value" in
                    *$'\n'* | *$'\r'*)
                        larch_err "phase_driver_read_result_env: value for key ${key} must not contain newline or carriage return"
                        if [[ "$key" == "SCOPE_ANCHOR_FILE" ]]; then
                            larch_err "phase_driver_read_result_env: WARN: skipped durable handoff key ${key} due to CR/LF"
                        else
                            larch_err "phase_driver_read_result_env: WARN: skipped allowlisted key ${key} due to CR/LF"
                        fi
                        continue 2
                        ;;
                esac
                printf '%s=%s\n' "$key" "$value"
                break
            fi
        done
    done <"$path"
    return 0
}
