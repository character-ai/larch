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

emit_breadcrumb "Uninstalling larch plugin..."
claude plugin uninstall larch@larch-local 2>&1 || true

emit_breadcrumb "Removing larch-local marketplace..."
claude plugin marketplace remove larch-local 2>&1 || true

emit_breadcrumb "Re-adding larch marketplace from GitHub..."
claude plugin marketplace add character-ai/larch 2>&1

emit_breadcrumb "Installing larch plugin..."
claude plugin install larch@larch-local 2>&1

emit_breadcrumb ""
emit_breadcrumb "Installed larch plugin version:"
claude plugin list 2>&1 | grep -A2 'larch@larch-local' || true

emit_breadcrumb ""
emit_breadcrumb "Upgrade complete. Restart Claude Code to apply the new version."
