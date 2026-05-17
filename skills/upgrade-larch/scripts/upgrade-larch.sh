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

# Parent directory that contains one subdirectory per installed larch version.
LARCH_CACHE_DIR="$(dirname "$PLUGIN_ROOT")"
# Version string of the currently running larch installation (basename of PLUGIN_ROOT).
INSTALLED_VERSION="$(basename "$PLUGIN_ROOT")"

# Resolve the latest stable (non-pre-release, non-draft) release from GitHub.
emit_breadcrumb "Checking latest stable larch release..."
LATEST_STABLE=""
if command -v gh >/dev/null 2>&1; then
    LATEST_STABLE=$(gh api repos/character-ai/larch/releases \
      --jq '[.[] | select(.prerelease == false and .draft == false)] | first | .tag_name' \
      2>/dev/null | sed 's/^v//') || true
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
if [ -n "$LATEST_STABLE" ]; then
    if [ -d "$LARCH_CACHE_DIR/$LATEST_STABLE" ]; then
        emit_breadcrumb "Verified: larch ${LATEST_STABLE} installed successfully."
    else
        # shellcheck disable=SC2012
        ACTUAL_VERSION=$(ls -d "$LARCH_CACHE_DIR"/[0-9]*/ 2>/dev/null | sort -V | tail -1 | xargs basename 2>/dev/null || true)
        larch_err ""
        larch_err "Warning: expected version ${LATEST_STABLE} but found ${ACTUAL_VERSION:-unknown} in the plugin cache."
        larch_err "A pre-release or unexpected version may have been installed."
        larch_err "Re-run /upgrade-larch or install manually:"
        larch_err "  claude plugin marketplace add character-ai/larch"
        larch_err "  claude plugin install larch@larch-local"
    fi
fi

# Prune old versions: keep the two most recent, remove the rest.
emit_breadcrumb "Pruning old larch versions (keeping latest two)..."
# shellcheck disable=SC2012
VERSION_COUNT=$(ls -d "$LARCH_CACHE_DIR"/[0-9]*/ 2>/dev/null | sort -V | wc -l | tr -d ' ')
KEEP=2
if [ "${VERSION_COUNT:-0}" -gt "$KEEP" ]; then
    PRUNE_COUNT=$((VERSION_COUNT - KEEP))
    # shellcheck disable=SC2012
    ls -d "$LARCH_CACHE_DIR"/[0-9]*/ 2>/dev/null | sort -V | head -n "$PRUNE_COUNT" | while IFS= read -r dir; do
        emit_breadcrumb "  Removing old version: $(basename "$dir")"
        rm -rf "$dir"
    done
else
    emit_breadcrumb "  No old versions to prune."
fi

emit_breadcrumb ""
emit_breadcrumb "Installed larch plugin version:"
claude plugin list 2>&1 | grep -A2 'larch@larch-local' || true

emit_breadcrumb ""
emit_breadcrumb "Upgrade complete. Restart Claude Code to apply the new version."
