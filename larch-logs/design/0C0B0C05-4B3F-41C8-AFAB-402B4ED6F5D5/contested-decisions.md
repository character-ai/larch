### DECISION_1: Implicit vs explicit "init-state-from-argv" mode flag
- **Chosen**: Implicit — the presence of any `--branch-name` / `--issue-number` / etc. flag is enough to know the orchestrator wants argv-init mode. No separate `--init-state-from-argv` toggle is required.
- **Alternative**: Explicit `--init-state-from-argv` mode flag must be passed alongside the per-key flags, otherwise they are rejected.
- **Tension**: Cursor sketch mentions argv-init "mode" but doesn't insist on an explicit toggle. Codex sketch explicitly proposes `--init-state-from-argv` flag. The issue body uses `--init-state-from-argv` as the verb but the example shows individual flags only.
- **Impact**: Low — implicit means one less flag at every callsite; explicit means clearer intent.
- **Affected files**: scripts/ship-pr.sh (argv parser), scripts/ship-pr.md (interface)

### DECISION_2: Order of key-list source-of-truth
- **Chosen**: Single ordered key-list constant in `scripts/ship-pr.sh` (consumed by both `write_initial_state()` and `require_key` validation). The SKILL.md key list at L1550-1559 becomes a documentation echo, not the source.
- **Alternative**: Extract the 38-key list into `scripts/lib-ship-pr-state-keys.sh` (mirroring the existing `scripts/lib-finalize-state-keys.sh` pattern), then ship-pr.sh sources it. Other consumers (audit-scan-run.sh, restore-finalize-state.sh) could reuse it.
- **Tension**: Cursor implies single ordered list; Codex doesn't directly address. Existing pattern (lib-finalize-state-keys.sh) argues for the dedicated lib. But the immediate scope only has one consumer.
- **Impact**: Medium — affects future maintainability if more consumers need the key list.
- **Affected files**: scripts/ship-pr.sh, possibly new scripts/lib-ship-pr-state-keys.sh

### DECISION_3: Argv-init key-set granularity (which flags to add)
- **Chosen**: Only flags for varying values the orchestrator currently passes — BRANCH_NAME, ISSUE_NUMBER, RUN_ID, MANIFEST_PATH, TOOL_LABEL, EXPECTED_SESSION_ID, EXPECTED_TMPDIR_BASENAME_PREFIX. The constants (PHASE=checks, HAS_BUMP=true, all =false defaults, counters=0, empty strings) are emitted by `write_initial_state()` without needing a flag. Existing flags (--merge, --draft, --forked, --repo, --implement-tmpdir, --no-logs-commit) cover the remaining variables.
- **Alternative**: Add a flag for every one of the 38 keys for forward compatibility (e.g. `--ci-passed`, `--oos-pending`). Would let callers override constants but no current need.
- **Tension**: Codex sketch implies "state-key flags" generically; Cursor doesn't specify the set. Minimum-viable scope argues for only varying values.
- **Impact**: Medium — adding all 38 would be ~30 extra `case` arms; future-proofing for unknown callers.
- **Affected files**: scripts/ship-pr.sh
