#!/usr/bin/env bash
# git-rebase-abort.sh — Abort an in-progress rebase (idempotent).
#
# Wraps `git rebase --abort`. Safe to call when no rebase is in progress
# (the command will simply report "No rebase in progress" and exit 0).
#
# Usage:
#   git-rebase-abort.sh
#
# Exit codes:
#   0 — always (abort succeeded or no rebase was in progress)

# Intentionally not using set -e — we want to always exit 0.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

git rebase --abort 2>/dev/null || true
exit 0
