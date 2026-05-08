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
REPO=$("$SCRIPT_DIR/resolve-repo.sh" 2>/dev/null) || REPO=""
GH_REPO_ARGS=()
if [[ -n "$REPO" ]]; then
  GH_REPO_ARGS=(--repo "$REPO")
fi

gh pr view "${GH_REPO_ARGS[@]}" --json body --jq '.body' 2>/dev/null \
  | grep -oE 'Closes #[0-9]+' \
  | head -1 \
  | grep -oE '[0-9]+' \
  || true
