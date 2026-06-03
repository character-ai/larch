#!/usr/bin/env bash
# hook-post-bump-version.sh — PostToolUse hook (retired Phase 1 #3364).
#
# Per-PR bump is removed from /implement; this hook is a documented no-op until
# hooks/hooks.json registration is removed in Phase 5. Physical deletion deferred.
#
# set -e omitted: fail open per .claude/rules/shell-strict-mode.md.

set -uo pipefail

exit 0
