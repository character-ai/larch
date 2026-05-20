## Goal
Add version-skew warning to session-setup.sh when installed larch plugin is behind working-tree version

## Implementation Plan
Add version-skew warning when larch installed plugin is behind working-tree version.


### Goal
When an operator runs /implement (or any skill that goes through session-setup.sh) from a larch
dev clone where the working-tree version is newer than the installed cached plugin version,
emit a prominent warning so they know to run /larch:upgrade-larch before the next run.

### Approach (Option A from issue #2430 — warn-only)
- New helper `scripts/check-stale-plugin.sh`: detects larch dev clone + compares versions
- Wired into `scripts/session-setup.sh` (called from both /implement Step 0 and /fix-issue Step 1)
- Regression harness `scripts/test-check-stale-plugin.sh`
- Docs note in `docs/installation-and-setup.md`

### Files to create:
1. scripts/check-stale-plugin.sh — standalone helper
   - Args: [--installed-plugin-json <path>] [--working-tree-root <path>] (for testability; auto-detect otherwise)
   - Dev-clone detection: presence of skills/implement/SKILL.md under working-tree root
   - Installed version: ${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json
   - WT version: <working-tree-root>/.claude-plugin/plugin.json
   - Output (stdout, KEY=value):
     - STALE_PLUGIN_CHECK=skip (CLAUDE_PLUGIN_ROOT unset or plugin.json missing)
     - STALE_PLUGIN_CHECK=not-a-dev-clone (no skills/implement/SKILL.md)
     - STALE_PLUGIN_CHECK=versions-match (installed == WT)
     - STALE_PLUGIN_CHECK=working-tree-ahead + STALE_PLUGIN_INSTALLED_VERSION + STALE_PLUGIN_WORKING_TREE_VERSION
     - STALE_PLUGIN_CHECK=installed-ahead (no warning; installed > WT)
   - Always exits 0

2. scripts/check-stale-plugin.md — sibling doc
3. scripts/test-check-stale-plugin.sh — regression harness covering:
   (i) installed < WT → STALE_PLUGIN_CHECK=working-tree-ahead
   (ii) installed == WT → STALE_PLUGIN_CHECK=versions-match
   (iii) not dev clone (no skills/implement/SKILL.md) → STALE_PLUGIN_CHECK=not-a-dev-clone
4. scripts/test-check-stale-plugin.md — sibling doc stub

### Files to modify:
5. scripts/session-setup.sh — after the preflight block (SKIP_PREFLIGHT=false guard),
   call check-stale-plugin.sh and emit warning when STALE_PLUGIN_CHECK=working-tree-ahead.
   Uses session-setup.sh's `emit` so the warning appears in the Bash tool output visible
   to the orchestrator.

6. scripts/session-setup.md — document the new version-skew check step.

7. Makefile — add test-check-stale-plugin to .PHONY, add target near test-check-clean-tree,
   add to test-harnesses-3 shard.

8. docs/installation-and-setup.md — add note under "Install for local development" section
   explaining plugin cache vs. working-tree relationship and how to refresh with
   /larch:upgrade-larch.

### Testing strategy:
- Harness creates temp directories with fake plugin.json files, fake working-tree structure
- Three core cases + edge cases (missing CLAUDE_PLUGIN_ROOT, missing plugin.json)
- Run via: make test-check-stale-plugin

## Test plan
(no test plan section in plan-file)
