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

is_safe_version() {
    [[ "$1" =~ ^[0-9]+(\.[0-9]+)*$ ]]
}

get_stable_releases() {
    gh api --paginate repos/character-ai/larch/releases \
      --jq '.[] | select(.prerelease == false and .draft == false) | .tag_name' \
      | sed 's/^v//'
}

sort_versions() {
    awk -F. '
        NF {
            key = ""
            for (i = 1; i <= 8; i++) {
                part = (i <= NF && $i ~ /^[0-9]+$/) ? $i : 0
                key = key sprintf("%09d.", part)
            }
            print key "\t" $0
        }
    ' | sort | cut -f2-
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

list_cached_versions() {
    local dirs=()
    local dir
    shopt -s nullglob
    dirs=("$LARCH_CACHE_DIR"/[0-9]*/)
    shopt -u nullglob

    for dir in "${dirs[@]}"; do
        [ -d "$dir" ] || continue
        basename "${dir%/}"
    done | sort_versions
}

# Parent directory that contains one subdirectory per installed larch version.
LARCH_CACHE_DIR="$(dirname "$PLUGIN_ROOT")"
# Version string of the currently running larch installation (basename of PLUGIN_ROOT).
INSTALLED_VERSION="$(basename "$PLUGIN_ROOT")"

# Resolve the latest stable (non-pre-release, non-draft) release from GitHub.
emit_breadcrumb "Checking latest stable larch release..."
LATEST_STABLE=""
PREVIOUS_STABLE=""
if command -v gh >/dev/null 2>&1; then
    STABLE_RELEASES=()
    GH_RELEASES_OUTPUT=""
    if ! GH_RELEASES_OUTPUT=$(get_stable_releases 2>&1); then
        larch_err "Warning: failed to query GitHub stable releases via gh; upgrading without stable verification."
        if [ -n "$GH_RELEASES_OUTPUT" ]; then
            larch_err "gh output: $GH_RELEASES_OUTPUT"
        fi
    else
        while IFS= read -r release; do
            [ -n "$release" ] || continue
            STABLE_RELEASES+=("$release")
        done <<< "$GH_RELEASES_OUTPUT"

        if [ "${#STABLE_RELEASES[@]}" -eq 0 ]; then
            larch_err "Warning: gh returned no stable larch releases; upgrading without stable verification."
        elif is_safe_version "${STABLE_RELEASES[0]}"; then
            LATEST_STABLE="${STABLE_RELEASES[0]}"
        else
            larch_err "Warning: ignoring unexpected latest stable tag '${STABLE_RELEASES[0]}'."
        fi

        if [ "${#STABLE_RELEASES[@]}" -gt 1 ] && is_safe_version "${STABLE_RELEASES[1]}"; then
            PREVIOUS_STABLE="${STABLE_RELEASES[1]}"
        fi
    fi
fi

# Idempotency: skip the upgrade if the installed version already matches the latest stable.
if [ -n "$LATEST_STABLE" ] && [ "$INSTALLED_VERSION" = "$LATEST_STABLE" ]; then
    emit_breadcrumb ""
    emit_breadcrumb "Already at latest stable larch release (${INSTALLED_VERSION}). No upgrade needed."
    exit 0
fi

if [ -n "$LATEST_STABLE" ]; then
    emit_breadcrumb "Upgrading larch from ${INSTALLED_VERSION} to ${LATEST_STABLE}..."
else
    emit_breadcrumb "Latest stable release could not be determined; upgrading unconditionally..."
fi

emit_breadcrumb "Uninstalling larch plugin..."
claude plugin uninstall larch@larch-local 2>&1 || true

emit_breadcrumb "Removing larch-local marketplace..."
claude plugin marketplace remove larch-local 2>&1 || true

emit_breadcrumb "Re-adding larch marketplace from GitHub..."
claude plugin marketplace add character-ai/larch 2>&1

emit_breadcrumb "Installing larch plugin..."
claude plugin install larch@larch-local 2>&1

# Verify the installed version matches the expected stable release.
VERIFIED_TARGET=false
ACTUAL_VERSION=""
if [ -n "$LATEST_STABLE" ]; then
    ACTUAL_VERSION=$(get_installed_larch_version || true)
    if [ "$ACTUAL_VERSION" = "$LATEST_STABLE" ] && [ -d "$LARCH_CACHE_DIR/$LATEST_STABLE" ]; then
        VERIFIED_TARGET=true
        emit_breadcrumb "Verified: larch ${LATEST_STABLE} installed successfully."
    else
        larch_err ""
        larch_err "Warning: expected version ${LATEST_STABLE} but found installed version ${ACTUAL_VERSION:-unknown}."
        larch_err "A pre-release or unexpected version may have been installed."
        larch_err "Re-run /upgrade-larch or install manually:"
        larch_err "  claude plugin marketplace add character-ai/larch"
        larch_err "  claude plugin install larch@larch-local"
    fi
fi

# Prune old versions only after a verified stable install. Keep that stable version and its predecessor.
if [ "$VERIFIED_TARGET" = true ]; then
    emit_breadcrumb "Pruning old larch versions (keeping verified stable release and predecessor)..."
    CACHED_VERSIONS=()
    while IFS= read -r version; do
        [ -n "$version" ] || continue
        CACHED_VERSIONS+=("$version")
    done < <(list_cached_versions)
    VERSION_COUNT="${#CACHED_VERSIONS[@]}"

    KEEP_PREDECESSOR="$PREVIOUS_STABLE"
    if [ -z "$KEEP_PREDECESSOR" ] && [ "$VERSION_COUNT" -gt 1 ]; then
        for ((i=VERSION_COUNT-1; i>=0; i--)); do
            if [ "${CACHED_VERSIONS[$i]}" != "$LATEST_STABLE" ]; then
                KEEP_PREDECESSOR="${CACHED_VERSIONS[$i]}"
                break
            fi
        done
    fi

    KEEP_COUNT=1
    if [ -n "$KEEP_PREDECESSOR" ] && [ "$KEEP_PREDECESSOR" != "$LATEST_STABLE" ]; then
        KEEP_COUNT=2
    fi

    if [ "$VERSION_COUNT" -gt "$KEEP_COUNT" ]; then
        for version in "${CACHED_VERSIONS[@]}"; do
            if [ "$version" = "$LATEST_STABLE" ] || [ "$version" = "$KEEP_PREDECESSOR" ]; then
                continue
            fi
            emit_breadcrumb "  Removing old version: $version"
            rm -rf -- "${LARCH_CACHE_DIR:?}/${version:?}"
        done
    else
        emit_breadcrumb "  No old versions to prune."
    fi
else
    emit_breadcrumb "Skipping prune because the expected stable version was not verified."
fi

emit_breadcrumb ""
emit_breadcrumb "Installed larch plugin version:"
claude plugin list 2>&1 | grep -A2 'larch@larch-local' || true

emit_breadcrumb ""
if [ "$VERIFIED_TARGET" = false ] && [ -n "$LATEST_STABLE" ]; then
    emit_breadcrumb "Upgrade incomplete: expected stable version ${LATEST_STABLE} was not verified."
    exit 1
fi

emit_breadcrumb "Upgrade complete. Restart Claude Code to apply the new version."
