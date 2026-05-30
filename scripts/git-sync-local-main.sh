#!/usr/bin/env bash
# git-sync-local-main.sh — Fast-forward local `main` ref to a remote base ref.
#
# Silent no-op when the local `main` ref does not exist. Used by the
# Rebase + Re-bump Sub-procedure step 3
# (skills/implement/references/rebase-rebump-subprocedure.md) so that
# `classify-bump.sh`'s merge-base computation resolves against the latest
# remote base.
#
# Never run on `main` itself — `git branch -f` of the current branch fails.
# /implement's Step 10 and Step 12 rebase loops always run on a feature branch.
#
# Usage:
#   git-sync-local-main.sh [--base-remote NAME] [--base-ref BRANCH]
#
# Output (stdout):
#   RESULT=updated|absent|already_current
#
# Exit codes:
#   0 — success (including the silent no-op case)
#   1 — invoked while on `main` (guard against accidental self-update)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init

BASE_REMOTE=origin
BASE_REF=main
while [ "$#" -gt 0 ]; do
    case "$1" in
        --base-remote)
            [ "$#" -ge 2 ] || { larch_err "git-sync-local-main.sh: --base-remote requires a value"; exit 1; }
            BASE_REMOTE=$2
            shift 2
            ;;
        --base-ref)
            [ "$#" -ge 2 ] || { larch_err "git-sync-local-main.sh: --base-ref requires a value"; exit 1; }
            BASE_REF=$2
            shift 2
            ;;
        *)
            larch_err "git-sync-local-main.sh: unknown argument: $1"
            exit 1
            ;;
    esac
done

BASE_TARGET="${BASE_REMOTE}/${BASE_REF}"

CURRENT=$(git symbolic-ref --short HEAD 2>/dev/null || echo "")
if [[ "$CURRENT" == "main" ]]; then
    larch_err "git-sync-local-main.sh: refusing to update local 'main' while checked out on main"
    exit 1
fi

if ! git rev-parse --verify main >/dev/null 2>&1; then
    emit_kv RESULT absent
    exit 0
fi

# Check if local main already matches the remote base ref.
LOCAL_MAIN=$(git rev-parse main 2>/dev/null || echo "")
REMOTE_MAIN=$(git rev-parse "$BASE_TARGET" 2>/dev/null || echo "")
if [[ -n "$LOCAL_MAIN" && "$LOCAL_MAIN" == "$REMOTE_MAIN" ]]; then
    emit_kv RESULT already_current
    exit 0
fi

git branch -f main "$BASE_TARGET"
emit_kv RESULT updated
