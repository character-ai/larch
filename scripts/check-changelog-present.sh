#!/usr/bin/env bash
# check-changelog-present.sh — Test for CHANGELOG.md at the repo root.
#
# Usage:
#   check-changelog-present.sh
#
# Output (stdout, KEY=VALUE):
#   CHANGELOG_PRESENT=true|false
#
# Always exits 0 — presence is informational, not an error condition.
# Resolves the repo root via `git rev-parse --show-toplevel`; falls back to
# $PWD when not inside a git work tree (defensive: /implement Step 8a always
# runs inside a git repo, but keep the script standalone-callable).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

if root=$(git rev-parse --show-toplevel 2>/dev/null); then
    :
else
    root=$PWD
fi

if [[ -f "$root/CHANGELOG.md" ]]; then
    emit_kv CHANGELOG_PRESENT true
else
    emit_kv CHANGELOG_PRESENT false
fi
