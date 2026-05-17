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
      2>/dev/null | sed 's/^v//'
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
    done | sort -V
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
    mapfile -t STABLE_RELEASES < <(get_stable_releases || true)
    if [ "${#STABLE_RELEASES[@]}" -gt 0 ]; then
        if is_safe_version "${STABLE_RELEASES[0]}"; then
            LATEST_STABLE="${STABLE_RELEASES[0]}"
        else
            larch_err "Warning: ignoring unexpected latest stable tag '${STABLE_RELEASES[0]}'."
        fi
    fi
    if [ "${#STABLE_RELEASES[@]}" -gt 1 ] && is_safe_version "${STABLE_RELEASES[1]}"; then
        PREVIOUS_STABLE="${STABLE_RELEASES[1]}"
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
if [ -n "$LATEST_STABLE" ]; then
    if [ -d "$LARCH_CACHE_DIR/$LATEST_STABLE" ]; then
        VERIFIED_TARGET=true
        emit_breadcrumb "Verified: larch ${LATEST_STABLE} installed successfully."
    else
        ACTUAL_VERSION=$(list_cached_versions | tail -1 || true)
        larch_err ""
        larch_err "Warning: expected version ${LATEST_STABLE} but found ${ACTUAL_VERSION:-unknown} in the plugin cache."
        larch_err "A pre-release or unexpected version may have been installed."
        larch_err "Re-run /upgrade-larch or install manually:"
        larch_err "  claude plugin marketplace add character-ai/larch"
        larch_err "  claude plugin install larch@larch-local"
    fi
fi

# Prune old versions only after a verified stable install. Keep that stable version and its predecessor.
if [ "$VERIFIED_TARGET" = true ]; then
    emit_breadcrumb "Pruning old larch versions (keeping verified stable release and predecessor)..."
    mapfile -t CACHED_VERSIONS < <(list_cached_versions)
    VERSION_COUNT="${#CACHED_VERSIONS[@]}"
    declare -A KEEP_VERSIONS=()
    KEEP_VERSIONS["$LATEST_STABLE"]=1
    if [ -n "$PREVIOUS_STABLE" ]; then
        KEEP_VERSIONS["$PREVIOUS_STABLE"]=1
    fi

    if [ "$VERSION_COUNT" -gt "${#KEEP_VERSIONS[@]}" ]; then
        for version in "${CACHED_VERSIONS[@]}"; do
            if [ -n "${KEEP_VERSIONS[$version]:-}" ]; then
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
emit_breadcrumb "Upgrade complete. Restart Claude Code to apply the new version."
