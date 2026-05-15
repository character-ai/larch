#!/usr/bin/env bash
# show.sh — resolve a skill name to its SKILL.md.
# Usage: show.sh <skill-name>
# Stdout: STATUS=found + SKILL_PATH=<path>  or  STATUS=not-found
# Exit: always 0

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

NAME="${1:-}"
if [[ -z "$NAME" ]]; then
  emit_kv STATUS "not-found"
  exit 0
fi

# Strip larch: prefix and leading /
NAME="${NAME#larch:}"
NAME="${NAME#/}"

# Reject path traversal
if [[ "$NAME" == *"/"* || "$NAME" == *".."* ]]; then
  emit_kv STATUS "not-found"
  exit 0
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"

for candidate in \
    "${PLUGIN_ROOT}/skills/${NAME}/SKILL.md" \
    ${REPO_ROOT:+"${REPO_ROOT}/.claude/skills/${NAME}/SKILL.md"} \
    "${PLUGIN_ROOT}/.claude/skills/${NAME}/SKILL.md"
do
  if [[ -f "$candidate" ]]; then
    emit_kv STATUS "found"
    emit_kv SKILL_PATH "$candidate"
    # Route SKILL.md content to the original stdout (FD3 when quiet-active).
    if [ "${LARCH_QUIET_PID:-}" = "$$" ]; then
      cat "$candidate" >&3
    else
      cat "$candidate"
    fi
    exit 0
  fi
done

emit_kv STATUS "not-found"
exit 0
