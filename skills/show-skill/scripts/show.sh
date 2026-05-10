#!/usr/bin/env bash
# show.sh — resolve a skill name to its SKILL.md.
# Usage: show.sh <skill-name>
# Stdout: STATUS=found + SKILL_PATH=<path>  or  STATUS=not-found
# Exit: always 0

set -euo pipefail

NAME="${1:-}"
if [[ -z "$NAME" ]]; then
  echo "STATUS=not-found"
  exit 0
fi

# Strip larch: prefix and leading /
NAME="${NAME#larch:}"
NAME="${NAME#/}"

# Reject path traversal
if [[ "$NAME" == *"/"* || "$NAME" == *".."* ]]; then
  echo "STATUS=not-found"
  exit 0
fi

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
if [[ -z "$PLUGIN_ROOT" ]]; then
  PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

for candidate in \
    "${PLUGIN_ROOT}/skills/${NAME}/SKILL.md" \
    "${REPO_ROOT}/.claude/skills/${NAME}/SKILL.md" \
    "${PLUGIN_ROOT}/.claude/skills/${NAME}/SKILL.md"
do
  if [[ -f "$candidate" ]]; then
    echo "STATUS=found"
    echo "SKILL_PATH=${candidate}"
    exit 0
  fi
done

echo "STATUS=not-found"
exit 0
