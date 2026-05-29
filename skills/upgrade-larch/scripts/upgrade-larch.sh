#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init
# Restore original stdout so progress and the installed version line reach the operator.
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3

recover() {
    larch_err ""
    larch_err "Recovery: run these commands manually to reinstall:"
    larch_err "  claude plugin marketplace add character-ai/larch"
    larch_err "  claude plugin install larch@larch-local"
}
trap recover ERR

warn_prune_failure() {
    local version="$1"
    larch_err "Warning: failed to prune cached larch version '${version}'."
}

warn_install_stamp_failure() {
    local version="$1"
    larch_err "Warning: failed to write install stamp for cached larch version '${version}'."
}

is_safe_version() {
    [[ "$1" =~ ^[0-9]+(\.[0-9]+)*$ ]]
}

get_stable_releases() {
    gh api --paginate repos/character-ai/larch/releases \
      --jq '.[] | select(.prerelease == false and .draft == false) | .tag_name' \
      | sed 's/^v//'
}

get_installed_larch_version() {
    local plugin_record installed_version
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

    installed_version=$(grep -A6 '"larch@larch-local"' "$HOME/.claude/plugins/installed_plugins.json" 2>/dev/null | awk -F'"' '
        /"version":/ {
            print $4
            exit
        }
    ' || true)
    if is_safe_version "${installed_version:-}"; then
        printf '%s\n' "$installed_version"
        return 0
    fi

    return 1
}

stat_mtime() {
    local file="$1"
    local mt

    if mt=$(stat -c '%Y' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    if mt=$(stat -f '%m' -- "$file" 2>/dev/null) && [[ "$mt" =~ ^[0-9]+$ ]]; then
        printf '%s\n' "$mt"
        return 0
    fi
    printf '0\n'
    return 0
}

read_install_stamp() {
    local version_dir="$1"
    local stamp_file="$version_dir/.larch-installed-at"
    local stamp

    [ -f "$stamp_file" ] || return 1
    stamp=$(tr -d '\r\n' < "$stamp_file" 2>/dev/null || true)
    [[ "$stamp" =~ ^[0-9]+$ ]] || return 1
    printf '%s\n' "$stamp"
}

write_install_stamp() {
    local version="$1"
    local version_dir="$LARCH_CACHE_DIR/$version"
    local now

    [ -d "$version_dir" ] || return 0
    now=$(date +%s 2>/dev/null || true)
    [[ "$now" =~ ^[0-9]+$ ]] || {
        warn_install_stamp_failure "$version"
        return 0
    }
    if ! printf '%s\n' "$now" > "$version_dir/.larch-installed-at"; then
        warn_install_stamp_failure "$version"
    fi
}

list_cached_versions_by_install_stamp() {
    local dirs=()
    local dir version_dir version has_stamp ts

    shopt -s nullglob
    dirs=("$LARCH_CACHE_DIR"/[0-9]*/)
    shopt -u nullglob

    for dir in "${dirs[@]}"; do
        [ -d "$dir" ] || continue
        version_dir="${dir%/}"
        version=$(basename "$version_dir")
        is_safe_version "$version" || continue

        if read_install_stamp "$version_dir" >/dev/null 2>&1; then
            has_stamp=1
            ts=$(read_install_stamp "$version_dir")
        else
            has_stamp=0
            ts=$(stat_mtime "$version_dir")
        fi
        printf '%s\t%s\t%s\n' "$has_stamp" "$ts" "$version"
    done | sort -t $'\t' -k1,1rn -k2,2rn -k3,3rn | cut -f3-
}

version_is_retained() {
    local needle="$1"
    local retained="$2"
    local version

    for version in $retained; do
        [ "$version" = "$needle" ] && return 0
    done
    return 1
}

prune_cached_versions() {
    local target_version="$1"
    local keep_versions=8
    local retained="" version version_dir removed=0

    larch_err "Pruning old larch versions (keeping up to ${keep_versions} most-recently-installed)..."

    if [ -n "$target_version" ] && is_safe_version "$target_version" && [ -d "$LARCH_CACHE_DIR/$target_version" ]; then
        retained="$target_version"
    fi
    if [ -n "$INSTALLED_VERSION" ] && is_safe_version "$INSTALLED_VERSION" \
        && [ -d "$LARCH_CACHE_DIR/$INSTALLED_VERSION" ] \
        && ! version_is_retained "$INSTALLED_VERSION" "$retained"; then
        retained="${retained:+$retained }$INSTALLED_VERSION"
    fi

    while IFS= read -r version; do
        [ -n "$version" ] || continue
        if version_is_retained "$version" "$retained"; then
            continue
        fi
        retained="${retained:+$retained }$version"
        if [ "$(printf '%s\n' "$retained" | wc -w | tr -d ' ')" -ge "$keep_versions" ]; then
            break
        fi
    done < <(list_cached_versions_by_install_stamp)

    if [ -z "$retained" ]; then
        larch_err "  No cached versions to prune."
        return 0
    fi

    shopt -s nullglob
    for version_dir in "$LARCH_CACHE_DIR"/[0-9]*/; do
        [ -d "$version_dir" ] || continue
        version=$(basename "${version_dir%/}")
        is_safe_version "$version" || continue
        if version_is_retained "$version" "$retained"; then
            continue
        fi
        larch_err "  Removing old version: $version"
        if ! rm -rf -- "${LARCH_CACHE_DIR:?}/${version:?}"; then
            warn_prune_failure "$version"
            continue
        fi
        removed=$((removed + 1))
    done
    shopt -u nullglob

    if [ "$removed" -eq 0 ]; then
        larch_err "  No old versions to prune."
    fi
}

# Parent directory that contains one subdirectory per installed larch version.
LARCH_CACHE_DIR="$(dirname "$PLUGIN_ROOT")"
# Version string of the currently running larch installation (basename of PLUGIN_ROOT).
INSTALLED_VERSION="$(basename "$PLUGIN_ROOT")"

# Resolve the latest stable (non-pre-release, non-draft) release from GitHub.
larch_err "Checking latest stable larch release..."
LATEST_STABLE=""
if command -v gh >/dev/null 2>&1; then
    STABLE_RELEASES=()
    GH_RELEASES_OUTPUT=""
    GH_STDERR_LOG=$(mktemp "${TMPDIR:-/tmp}/upgrade-larch-gh-stderr.XXXXXX")
    if GH_RELEASES_OUTPUT=$(get_stable_releases 2>"$GH_STDERR_LOG"); then
        while IFS= read -r release; do
            [ -n "$release" ] || continue
            STABLE_RELEASES+=("$release")
        done <<< "$GH_RELEASES_OUTPUT"

        if [ "${#STABLE_RELEASES[@]}" -eq 0 ]; then
            larch_err "Warning: gh returned no stable larch releases; upgrading without stable verification."
        else
            for release in "${STABLE_RELEASES[@]}"; do
                if ! is_safe_version "$release"; then
                    larch_err "Warning: ignoring unexpected stable tag '${release}'."
                    continue
                fi
                if [ -z "$LATEST_STABLE" ]; then
                    LATEST_STABLE="$release"
                    break
                fi
            done
            if [ -z "$LATEST_STABLE" ]; then
                larch_err "Warning: gh returned no valid stable larch release tags; upgrading without stable verification."
            fi
        fi
    else
        gh_status=$?
        larch_err "Warning: failed to query GitHub stable releases via gh (exit ${gh_status}); upgrading without stable verification."
    fi
    rm -f -- "$GH_STDERR_LOG"
fi

# Idempotency: on already-latest, stamp and prune without reinstalling.
CURRENT_INSTALLED_VERSION=$(get_installed_larch_version || true)
if ! is_safe_version "${CURRENT_INSTALLED_VERSION:-}"; then
    CURRENT_INSTALLED_VERSION="$INSTALLED_VERSION"
fi
if [ -n "$LATEST_STABLE" ] && [ "$CURRENT_INSTALLED_VERSION" = "$LATEST_STABLE" ]; then
    ACTUAL_VERSION="${CURRENT_INSTALLED_VERSION:-$INSTALLED_VERSION}"
    write_install_stamp "$ACTUAL_VERSION"
    prune_cached_versions "$ACTUAL_VERSION"
    larch_err ""
    larch_err "Already at latest stable larch release (${CURRENT_INSTALLED_VERSION}). No upgrade needed."
    exit 0
fi

if [ -n "$LATEST_STABLE" ]; then
    larch_err "Upgrading larch from ${INSTALLED_VERSION} to ${LATEST_STABLE}..."
else
    larch_err "Latest stable release could not be determined; upgrading unconditionally..."
fi

larch_err "Uninstalling larch plugin..."
claude plugin uninstall larch@larch-local 2>&1 || true

larch_err "Removing larch-local marketplace..."
claude plugin marketplace remove larch-local 2>&1 || true

larch_err "Re-adding larch marketplace from GitHub..."
claude plugin marketplace add character-ai/larch 2>&1

larch_err "Installing larch plugin..."
claude plugin install larch@larch-local 2>&1

# Verify the installed version matches the expected stable release.
VERIFIED_TARGET=false
ACTUAL_VERSION=""
if [ -n "$LATEST_STABLE" ]; then
    ACTUAL_VERSION=$(get_installed_larch_version || true)
    if [ "$ACTUAL_VERSION" = "$LATEST_STABLE" ]; then
        VERIFIED_TARGET=true
        larch_err "Verified: larch ${LATEST_STABLE} installed successfully."
    else
        larch_err ""
        larch_err "Warning: expected version ${LATEST_STABLE} but found installed version ${ACTUAL_VERSION:-unknown}."
        larch_err "A pre-release or unexpected version may have been installed."
        larch_err "Re-run /upgrade-larch or install manually:"
        larch_err "  claude plugin marketplace add character-ai/larch"
        larch_err "  claude plugin install larch@larch-local"
    fi
fi

# Prune old versions only after a verified stable install.
if [ "$VERIFIED_TARGET" = true ]; then
    write_install_stamp "$ACTUAL_VERSION"
    prune_cached_versions "$ACTUAL_VERSION"
else
    larch_err "Skipping prune because the expected stable version was not verified."
fi

larch_err ""
larch_err "Installed larch plugin version:"
claude plugin list 2>&1 | grep -A2 'larch@larch-local' || true

larch_err ""
if [ "$VERIFIED_TARGET" = false ] && [ -n "$LATEST_STABLE" ]; then
    larch_err "Upgrade incomplete: expected stable version ${LATEST_STABLE} was not verified."
    exit 1
fi

larch_err "Upgrade complete. Restart Claude Code to apply the new version."
