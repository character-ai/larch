#!/usr/bin/env bash
# Sourced helper for /release Step 7 cache-root resolution. Keep this file
# side-effect light: no traps, fd changes, quiet logging, or upgrade execution.

is_safe_version() {
    [[ "$1" =~ ^[0-9]+(\.[0-9]+)*$ ]]
}

release_step7_cache_parent() {
    [ -n "${HOME:-}" ] || return 1
    printf '%s\n' "$HOME/.claude/plugins/cache/larch-local/larch"
}

get_installed_larch_version() {
    local plugin_record installed_version installed_json

    plugin_record=$(claude plugin list 2>/dev/null | awk '
        /larch@larch-local/ { want=1; next }
        want && /^[[:space:]]*Version:/ {
            sub(/^[[:space:]]*Version:[[:space:]]*/, "", $0)
            print
            exit
        }
    ' || true)
    if is_safe_version "${plugin_record:-}"; then
        printf '%s\n' "$plugin_record"
        return 0
    fi

    [ -n "${HOME:-}" ] || return 1
    installed_json="$HOME/.claude/plugins/installed_plugins.json"
    installed_version=$(grep -A6 '"larch@larch-local"' "$installed_json" 2>/dev/null | awk -F'"' '
        /"version":/ {
            print $4
            exit
        }
    ') || return 1
    if is_safe_version "${installed_version:-}"; then
        printf '%s\n' "$installed_version"
        return 0
    fi

    return 1
}

is_cache_shaped_larch_root() {
    local root="$1" cache_parent version

    [ -n "$root" ] || return 1
    cache_parent=$(release_step7_cache_parent) || return 1
    case "$root" in
        "$cache_parent/"*) ;;
        *) return 1 ;;
    esac
    [ -d "$root" ] || return 1
    version=$(basename "$root")
    is_safe_version "$version"
}

single_larch_cache_version_dir() {
    local cache_parent dir found="" count=0 version

    cache_parent=$(release_step7_cache_parent) || return 1
    shopt -s nullglob
    for dir in "$cache_parent"/*; do
        [ -d "$dir" ] || continue
        version=$(basename "$dir")
        is_safe_version "$version" || continue
        found="$dir"
        count=$((count + 1))
    done
    shopt -u nullglob
    [ "$count" -eq 1 ] || return 1
    printf '%s\n' "$found"
}

resolve_release_step7_root() {
    local current_version="${1:-}"
    local installed_version active_root cache_parent metadata_root current_root sole_root

    active_root="${CLAUDE_PLUGIN_ROOT:-}"
    if is_cache_shaped_larch_root "$active_root"; then
        printf '%s\n' "$active_root"
        return 0
    fi

    cache_parent=$(release_step7_cache_parent) || return 1
    installed_version=$(get_installed_larch_version || true)
    if is_safe_version "${installed_version:-}"; then
        metadata_root="$cache_parent/$installed_version"
        if [ -d "$metadata_root" ]; then
            printf '%s\n' "$metadata_root"
            return 0
        fi
    fi

    if is_safe_version "${current_version:-}"; then
        current_root="$cache_parent/$current_version"
        if [ -d "$current_root" ]; then
            sole_root=$(single_larch_cache_version_dir 2>/dev/null || true)
            if [ "$sole_root" = "$current_root" ]; then
                printf '%s\n' "$current_root"
                return 0
            fi
        fi
    fi

    sole_root=$(single_larch_cache_version_dir 2>/dev/null || true)
    if is_safe_version "${current_version:-}" && [ "$sole_root" = "$cache_parent/$current_version" ]; then
        printf '%s\n' "$sole_root"
        return 0
    fi
    return 1
}
