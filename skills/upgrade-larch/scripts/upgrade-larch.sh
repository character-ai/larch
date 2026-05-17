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

version_gt() {
    local left="$1" right="$2"
    local highest
    highest=$(printf '%s\n%s\n' "$left" "$right" | sort_versions | tail -n1)
    [ "$left" = "$highest" ] && [ "$left" != "$right" ]
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
                    continue
                fi
                if [ -z "$PREVIOUS_STABLE" ] && [ "$release" != "$LATEST_STABLE" ]; then
                    PREVIOUS_STABLE="$release"
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

# Idempotency: skip the upgrade if the installed version already matches the latest stable.
CURRENT_INSTALLED_VERSION=$(get_installed_larch_version || true)
if ! is_safe_version "${CURRENT_INSTALLED_VERSION:-}"; then
    CURRENT_INSTALLED_VERSION="$INSTALLED_VERSION"
fi
if [ -n "$LATEST_STABLE" ] && [ "$CURRENT_INSTALLED_VERSION" = "$LATEST_STABLE" ]; then
    emit_breadcrumb ""
    emit_breadcrumb "Already at latest stable larch release (${CURRENT_INSTALLED_VERSION}). No upgrade needed."
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
    if [ "$ACTUAL_VERSION" = "$LATEST_STABLE" ]; then
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

    KEEP_PREDECESSOR=""
    if [ -n "$PREVIOUS_STABLE" ]; then
        for version in "${CACHED_VERSIONS[@]}"; do
            if [ "$version" = "$PREVIOUS_STABLE" ]; then
                KEEP_PREDECESSOR="$PREVIOUS_STABLE"
                break
            fi
        done
    fi

    if [ -z "$KEEP_PREDECESSOR" ] && [ "$VERSION_COUNT" -gt 1 ]; then
        for ((i=VERSION_COUNT-1; i>=0; i--)); do
            if [ "${CACHED_VERSIONS[$i]}" != "$LATEST_STABLE" ] && ! version_gt "${CACHED_VERSIONS[$i]}" "$LATEST_STABLE"; then
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
            if ! rm -rf -- "${LARCH_CACHE_DIR:?}/${version:?}"; then
                warn_prune_failure "$version"
            fi
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
