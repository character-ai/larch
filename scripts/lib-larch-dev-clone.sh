# shellcheck shell=bash

# shellcheck disable=SC2317 # file is sourced; exit fallback is for direct execution.
if [ "${LARCH_LIB_DEV_CLONE_LOADED:-}" = "1" ]; then
    return 0 2>/dev/null || exit 0
fi
LARCH_LIB_DEV_CLONE_LOADED=1

is_larch_dev_clone() {
    local root=${1:-}

    if [ -z "$root" ]; then
        root=$(git rev-parse --show-toplevel 2>/dev/null || true)
    fi
    [ -n "$root" ] || return 1
    [ -f "$root/skills/implement/SKILL.md" ]
}
