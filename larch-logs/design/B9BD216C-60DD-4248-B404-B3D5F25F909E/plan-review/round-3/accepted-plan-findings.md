### FINDING_1: Depth-2 activity scan misses live larch-log writes
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned bounded newest-activity scan is too shallow for existing larch-log session paths, so active long-running sessions can write fresh run-log files below the scanned depth while cleanup still sees stale timestamps and deletes the session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Keep the scan bounded but include the known live larch-log depth, or explicitly stat larch-logs/*/* and larch-logs/*/*/* files; add a harness case with a stale session and a fresh larch-logs/implement/<RUN_ID>/manifest.json or round-1/findings.md
  - From Cursor-Edge, Codex-Edge: Keep the bounded scan but include depth 3, or explicitly include larch-logs/*/* batch files in newest-activity. Add the cleanup harness case for stale parent plus fresh larch-logs/implement/<run-id>/<batch>.
  - From Cursor-Innovation, Codex-Innovation: Keep the age-based design but scan deep enough for known session activity, e.g. maxdepth 4, or explicitly stat larch-logs/*/*/* plus the current depth-2 paths. Add the cleanup harness case for fresh larch-logs/implement/<run>/manifest.json.
  - From Codex-Pragmatic: For session dirs, scan through depth 3 or add a shallow heartbeat that larch-log writes update; add the cleanup harness case for a fresh depth-3 larch-logs/implement/$RUN_ID file


### FINDING_2: Cleanup harness is not fully wired into Makefile
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-dyn-test-wiring, Codex-dyn-test-wiring
- **Severity**: important
- **Concern**: The plan names `test-cleanup` in `.PHONY` or shard wiring without requiring a concrete Makefile recipe, so the cleanup harness may not run through `make lint` or `make test-harnesses`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add a test-cleanup target mirroring existing harness recipes, e.g. bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh, and keep the shard and docs/linting entries in sync
  - From Cursor-dyn-test-wiring, Codex-dyn-test-wiring: Revise the Makefile plan to name one exact shard line for test-cleanup and add the target recipe using the existing harness-timer pattern: bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh.


### FINDING_4: Upgrade idempotency docs conflict with planned cache mutation
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Installation docs still say an already-latest upgrade exits with no changes, but the planned behavior writes an install stamp and prunes the plugin cache.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Update line 38 to state that an already-latest run may still stamp the current version and prune the plugin cache (no reinstall/restart); reserve no changes for the no-op upgrade path only


### FINDING_6: Agent-lint allowlist update is conditional when it is required
- **Reviewer(s)**: Cursor-dyn-test-wiring, Codex-dyn-test-wiring
- **Severity**: important
- **Concern**: The new cleanup harness files will be Makefile-only, but the plan makes the `agent-lint.toml` reachability allowlist update conditional, risking dead-file lint failures after the files land.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-wiring, Codex-dyn-test-wiring: Make the agent-lint step unconditional for both skills/cleanup/scripts/test-cleanup.sh and skills/cleanup/scripts/test-cleanup.md; do not add stale lib-larch-cache-touch allowlist rows, since current agent-lint.toml has no matching rows to remove.


