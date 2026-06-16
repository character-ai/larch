### FINDING_1: Step 5 stall seed must force MERGE=false and DRAFT=false
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The planned shared seeder (`step-8-seed-initial.sh` / `ship seed-initial-state`) replaces today's stall missing-state prose, which explicitly overrides `DRAFT=false` and `MERGE=false` after copying session values. The plan's stall wrapper only passes `--stall-tracking`, `--stall-step`, and `--bail-reason`, and reads `MERGE`/`DRAFT` from session via `read_session_key`. A `/implement --merge` or `--draft` run that stalls at Step 5 would seed `ship-pr-state.sh` with merge/draft still true, diverging from today's stall contract and changing Step 8+ / final-report / Step 18 stall-recovery semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit stall-only overrides to the seeder contract: --merge false and --draft false (or equivalent Python stall-profile flags) on the Step 5 missing-state wrapper invocation, matching today's forced values.
  - From Cursor-Innovation: Add a stall-seed profile to seed-initial-state (or wrapper flags --merge false --draft false) that mirrors the current stall override block; extend python/test_ship.py stall override test to assert MERGE=false and DRAFT=false when session merge/draft are true.
  - From Cursor-Requirements: Add explicit stall-path overrides in the step5-review-branches.md wrapper example and step-8-seed-initial.sh contract (e.g. --merge false --draft false when --stall-step is set, or a dedicated --stall-seed mode), and extend python/test_ship.py stall-override coverage to assert MERGE=false and DRAFT=false on the Step 5 seed path


### FINDING_2: Missing agent-lint G004 exclusion for planned clone-tag helper
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan adds source-only `skills/implement/scripts/lib-implement-clone-tag.sh` but does not list an `agent-lint.toml` G004 exclusion for it (same pattern as `lib-resolve-implement-tmpdir.sh`). `make lint` / agent-lint G004 scans SKILL.md literal invocations and does not follow shell `source` edges; the clone-tag helper may be flagged unreachable/dead and block the PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add `### UPDATED: agent-lint.toml` (or fold into an existing lint-touch surface): exclude `skills/implement/scripts/lib-implement-clone-tag.sh` and `lib-implement-clone-tag.md` with a sourced-only comment mirroring `lib-resolve-implement-tmpdir.sh`.


### FINDING_4: Seeder wrapper lacks durable sources for required dynamic keys
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The seeder wrapper lacks durable sources for required dynamic keys. The one-line Step 8 fence passes no dynamic argv, `larch-run` only resolves tmpdir/plugin root, and `session-env` does not carry all required seed values such as `BRANCH_NAME`, `ISSUE_NUMBER`, `MANIFEST_PATH`, `TOOL_LABEL`, no-admin, and no-logs. A cold Step 8 seed can write empty or defaulted canonical keys, then ship-pr stalls or loses manifest/no-logs behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Define the wrapper source order per key. Read bootstrap-routing.env for Step 0 routing keys, map LARCH_RUN_ID when needed, and pass or persist Step 2/prompt-only values such as MANIFEST_PATH, TOOL_LABEL, merge/draft, no-admin, and no-logs before seeding. Extend the wrapper harness with realistic Step 0 and Step 2 files.


### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/stall_recovery.py:1079-1083
- **Concern**: [SCOPE-REDUCTION] Terminal stall seeder change conflicts with the non-goal. Scenario: The approach says to keep stall-recovery seed-terminal-state unchanged, but also says to make the terminal stall path fail closed on a non-empty ship-pr-state.sh. Current terminal recovery rewrites STALL_TRACKING, STALL_STEP, and PHASE into an existing driver state; removing that rewrite can break existing transient-to-stall recovery.
- **Proposed resolution**: Remove the terminal-stall fail-closed bullet. Limit create-if-absent semantics to the new initial ship-pr-state seeder.

