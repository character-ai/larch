#!/usr/bin/env bash
# git-stage.sh — Stage one or more files without committing.
#
# Wraps `git add -- <files>` so callers don't invoke `git` directly. Used by
# /implement's Conflict Resolution Procedure to stage resolved files before
# continuing the rebase. Distinct from scripts/git-commit.sh (which also
# commits) and scripts/git-amend-add.sh (which also amends).
#
# Usage:
#   git-stage.sh <file> [<file> ...]
#
# Exit codes: passthrough from `git add`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

if [[ $# -eq 0 ]]; then
    larch_err "git-stage.sh: at least one file argument is required"
    larch_err "usage: git-stage.sh <file> [<file> ...]"
    exit 1
fi

exec git add -- "$@"
