#!/usr/bin/env bash
# Extract the first `Closes #<N>` issue number from the current branch's PR
# body. Wraps the inline pipeline previously embedded in skills/implement/
# SKILL.md Step 0.5 Branch 3 (PR-body recovery).
#
# Inputs: none.
# Output: issue number on stdout, or empty when no PR exists on the current
# branch or its body has no `Closes #<N>` line.
# Exit code: always 0 (the empty case is normal, not an error).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib-quiet.sh
source "$SCRIPT_DIR/lib-quiet.sh"
larch_quiet_init
REPO=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null) || REPO=""

# Fail-closed on resolver failure: the contract here is "empty stdout means
# no PR / no Closes line". Calling `gh pr view` without --repo could silently
# match a different default repo's PR and emit its Closes #N (silent mis-
# routing, exactly what threading --repo is supposed to prevent). Exit 0
# with empty stdout — callers (Step 0.5 Branch 3 in /implement) treat that
# as "no PR found" and fall through to Branch 4.
if [[ -z "$REPO" ]]; then
  exit 0
fi

gh pr view --repo "$REPO" --json body --jq '.body' 2>/dev/null \
  | grep -oE 'Closes #[0-9]+' \
  | head -1 \
  | grep -oE '[0-9]+' \
  || true
