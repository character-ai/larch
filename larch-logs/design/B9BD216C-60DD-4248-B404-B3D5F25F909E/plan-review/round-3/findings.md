### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh (proposed)
- **Concern**: The proposed depth-2 newest-activity scan is shallower than existing live larch-log paths under session tmpdirs. Scenario: docs/run-logs.md:22-58 shows implement logs under larch-logs/implement/<RUN_ID>/ and round-<N>/; edits to existing files there may not update a depth-2 ancestor on APFS, so /cleanup can delete an active old session despite the live-write retention contract
- **Proposed resolution**: Keep the scan bounded but include the known live larch-log depth, or explicitly stat larch-logs/*/* and larch-logs/*/*/* files; add a harness case with a stale session and a fresh larch-logs/implement/<RUN_ID>/manifest.json or round-1/findings.md

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:709-710
- **Concern**: The plan wires new test-cleanup into .PHONY and a shard but does not say to add the Makefile recipe target. Scenario: A phony test-cleanup prerequisite with no recipe succeeds without running skills/cleanup/scripts/test-cleanup.sh, leaving the new cleanup contract effectively unwired in make lint
- **Proposed resolution**: Add a test-cleanup target mirroring existing harness recipes, e.g. bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh, and keep the shard and docs/linting entries in sync

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:39-47; scripts/larch-log.sh:287-296
- **Concern**: Depth-2 newest-activity scan misses live larch-log run files. Scenario: The plan says live writes under larch-logs refresh retention, but larch-log batches live at $SESSION_TMPDIR/larch-logs/<skill>/<run-id>/<file>, which is depth 3 below the session dir. Appending or replacing those files can leave the parent session dir and depth-2 run dir stale on APFS, so a long-running active session can be deleted after the retention window.
- **Proposed resolution**: Keep the bounded scan but include depth 3, or explicitly include larch-logs/*/* batch files in newest-activity. Add the cleanup harness case for stale parent plus fresh larch-logs/implement/<run-id>/<batch>.

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/run-logs.md:22-45
- **Concern**: Proposed cleanup maxdepth 2 activity scan misses live larch-log writes. Scenario: The plan names larch-logs as activity, but run logs live under larch-logs/implement/<RUN_ID>/..., deeper than two levels from the session root. A long-running active session can write fresh run-log files while cleanup still sees only stale depth-0..2 mtimes and deletes the session.
- **Proposed resolution**: Keep the age-based design but scan deep enough for known session activity, e.g. maxdepth 4, or explicitly stat larch-logs/*/*/* plus the current depth-2 paths. Add the cleanup harness case for fresh larch-logs/implement/<run>/manifest.json.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/session-setup.sh:255-268
- **Concern**: Identity-record slimming is extra churn for a SIMPLE fix. Scenario: Cleanup can stop using .larch-keepalive as a protection sentinel without changing the writer shape. Slimming the record forces extra fixture, doc, and hook-comment edits and creates the exact resolver shape-desync risk the plan lists.
- **Proposed resolution**: For this PR, keep the existing .larch-keepalive fields and only change cleanup behavior plus wording that calls it cleanup protection. Defer field removal to a separate compatibility cleanup if still wanted.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/installation-and-setup.md:38
- **Concern**: Upgrade idempotency prose still says already-latest exits with no changes. Scenario: After the already-latest path gains install-stamp write and keep-8 prune, operators following installation docs will believe no cache mutation occurred and may skip /cleanup or misread side effects
- **Proposed resolution**: Update line 38 to state that an already-latest run may still stamp the current version and prune the plugin cache (no reinstall/restart); reserve no changes for the no-op upgrade path only

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/cleanup/scripts/cleanup.sh:52-85
- **Concern**: Planned depth-2 newest-activity scan does not cover existing larch-log writes it claims to protect. Scenario: An active long-running session older than the retention window can update larch-logs/implement/$RUN_ID files at depth 3 while the depth-2 scan still sees stale timestamps and removes the session
- **Proposed resolution**: For session dirs, scan through depth 3 or add a shallow heartbeat that larch-log writes update; add the cleanup harness case for a fresh depth-3 larch-logs/implement/$RUN_ID file

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:27
- **Concern**: Adds dangling current-design-env symlink reaping despite the stated session-dir-only cleanup constraint. Scenario: This expands /cleanup beyond age-based session directory retention and conflicts with the plan's own "current-design-env-*.sh stays untouched" constraint
- **Proposed resolution**: Drop symlink reaping from the cleanup implementation and test list unless the issue explicitly requires it

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-test-wiring, Codex-dyn-test-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:112-113; Makefile:64-67,192-193,1017-1021
- **Concern**: The new cleanup harness wiring names .PHONY but does not name a concrete test-harnesses-N shard or the required test-cleanup target recipe.. Scenario: Adding test-cleanup as a shard prerequisite without a recipe leaves make test-cleanup or make test-harnesses failing with no rule to make target test-cleanup.
- **Proposed resolution**: Revise the Makefile plan to name one exact shard line for test-cleanup and add the target recipe using the existing harness-timer pattern: bash scripts/harness-timer.sh $@ bash skills/cleanup/scripts/test-cleanup.sh.

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-test-wiring, Codex-dyn-test-wiring
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:115-116; agent-lint.toml:1579-1582,1615-1638
- **Concern**: The agent-lint update for skills/cleanup/scripts/test-cleanup.{sh,md} is conditional even though the new harness is Makefile-only and current cleanup allowlisting only covers cleanup.md.. Scenario: The implementer can skip the allowlist because the plan says if reachability lint cannot discover it, leaving G004/dead-file lint to fail after the new files land.
- **Proposed resolution**: Make the agent-lint step unconditional for both skills/cleanup/scripts/test-cleanup.sh and skills/cleanup/scripts/test-cleanup.md; do not add stale lib-larch-cache-touch allowlist rows, since current agent-lint.toml has no matching rows to remove.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-test-wiring, Codex-dyn-test-wiring
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:151,164,167-172
- **Concern**: The Edge Cases section calls out stamp write failure, and Failure Modes says the exact-cap assertion belongs in a target-outside-top-8/stamp-failure test, but the Testing Strategy bullet only names always-keep-just-installed and target-outside-top-8 exact cap separately.. Scenario: The implemented prune harness could cover normal seeded retention without simulating a failed .larch-installed-at write, leaving the best-effort-stamp failure path untested.
- **Proposed resolution**: Add the explicit stamp-failure case to the first Testing Strategy bullet: simulate stamp write failure with more than 8 dirs, assert ACTUAL_VERSION is retained, and assert exactly 8 dirs remain.
