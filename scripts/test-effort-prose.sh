#!/usr/bin/env bash
# Regression check that prompt source files do not hardcode max-effort prose.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$REPO_ROOT"

PATTERN='Work at (your )?maximum reasoning effort level[.]'
FILES=(
  python/larch/rendering/rendering.py
  skills/design/SKILL.md
  skills/design/references/plan-review.md
  skills/implement/SKILL.md
  skills/review/SKILL.md
  skills/shared/voting-protocol.md
)

if LC_ALL=C grep -nE "$PATTERN" "${FILES[@]}"; then
  echo "test-effort-prose.sh: hardcoded max-effort prose found in prompt sources" >&2
  exit 1
fi

echo "PASS: test-effort-prose.sh"
