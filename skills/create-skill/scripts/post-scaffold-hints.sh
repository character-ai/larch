#!/usr/bin/env bash
# post-scaffold-hints.sh — Print human-readable reminders after a scaffold.
#
# Required flags:
#   --target-dir <path>  Absolute path of the new skill directory.
#   --plugin true|false  Whether this was a plugin-dev-mode scaffold.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd -P)}"
# shellcheck source=scripts/lib-quiet.sh
source "$PLUGIN_ROOT/scripts/lib-quiet.sh"
larch_quiet_init

# Restore original stdout so human-readable hints reach the operator.
[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3

TARGET_DIR=""
PLUGIN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target-dir) TARGET_DIR="$2"; shift 2 ;;
    --plugin)     PLUGIN="$2";     shift 2 ;;
    *)
      echo "ERROR=Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TARGET_DIR" ]]; then
  echo "ERROR=Missing --target-dir" >&2
  exit 1
fi

NAME="$(basename "$TARGET_DIR")"

emit_breadcrumb "Scaffolded: $TARGET_DIR/SKILL.md"
emit_breadcrumb ""
emit_breadcrumb "Next steps:"
emit_breadcrumb "  - Open $TARGET_DIR/SKILL.md and fill in the TODO body."
emit_breadcrumb "  - Every operational step must live in a .sh under $TARGET_DIR/scripts/."
emit_breadcrumb "    Do NOT place raw bash commands in SKILL.md."
emit_breadcrumb "  - If a script is needed by two or more skills, promote it to the shared scripts/ directory instead."
emit_breadcrumb "  - If this skill invokes another skill via the Skill tool, read"
emit_breadcrumb "    \${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md for the canonical"
emit_breadcrumb "    sub-skill invocation conventions (patterns, allowed-tools narrowing, session-env handoff)."

if [[ "$PLUGIN" == "true" ]]; then
  emit_breadcrumb ""
  emit_breadcrumb "Plugin-dev reminders:"
  emit_breadcrumb "  - Add a row for /$NAME to README.md (Skills catalog + feature matrix)."
  emit_breadcrumb "  - Add the following entries to .claude/settings.json permissions.allow,"
  emit_breadcrumb "    then re-sort the whole permissions.allow block by strict ASCII"
  emit_breadcrumb "    code-point order (e.g. via sort -u):"
  emit_breadcrumb "      \"Bash(\$PWD/skills/$NAME/scripts/*)\""
  emit_breadcrumb "      \"Skill($NAME)\""
  emit_breadcrumb "      \"Skill(larch:$NAME)\""
  emit_breadcrumb "  - Both Skill forms are required for strict-permissions consumers; see"
  emit_breadcrumb "    docs/configuration-and-permissions.md subsection \"Strict-permissions consumers — Skill permission entries\" for rationale."
  emit_breadcrumb "  - Update docs/workflow-lifecycle.md — if /$NAME is a stateful orchestrator,"
  emit_breadcrumb "    add it to the Skill Orchestration Hierarchy mermaid; if /$NAME is a pure"
  emit_breadcrumb "    forwarder/delegator, add it to the Delegation Topology subsection. Also"
  emit_breadcrumb "    add a Standalone Usage bullet."
  emit_breadcrumb "  - Update docs/agents.md when applicable (your skill spawns subagents via the Agent tool)."
  emit_breadcrumb "  - Update docs/review-agents.md when applicable (your skill alters reviewer composition or archetypes)."
  emit_breadcrumb "  - Update AGENTS.md Canonical sources list when applicable (your skill introduces a shared script used by multiple skills, or is itself a canonical source)."
fi

if [[ -d "$PWD/.claude/skills/relevant-checks" ]]; then
  emit_breadcrumb ""
  emit_breadcrumb "  - Run /relevant-checks after editing the scaffold."
fi
