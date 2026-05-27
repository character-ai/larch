# shellcheck shell=bash
# shellcheck disable=SC2317

if [ "${LARCH_LIB_CACHE_TOUCH_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_CACHE_TOUCH_LOADED=1

larch_touch_executing_cache_root() {
    local path="${CLAUDE_PLUGIN_ROOT:-}"
    local base

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                [[ $# -ge 2 ]] || return 0
                path="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    [[ -n "$path" ]] || return 0
    [[ -d "$path" ]] || return 0
    base=$(basename -- "$path")
    [[ "$base" =~ ^[0-9]+(\.[0-9]+)*$ ]] || return 0
    touch -c -- "$path" 2>/dev/null || true
    return 0
}
