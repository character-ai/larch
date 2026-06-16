### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/step5-review-branches.md:11
- **Concern**: skills/implement/references/step5-review-branches.md stall missing-state seed no longer forces MERGE=false and DRAFT=false. Scenario: Current stall seed path overrides MERGE=false and DRAFT=false after copying session values. The plan replaces that prose with step-8-seed-initial.sh stall flags only (--stall-tracking --stall-step --bail-reason) and reads merge/draft from session via read_session_key, so a --merge or --draft run that stalls at Step 5 would seed ship-pr-state.sh with merge/draft still true and change stall recovery semantics.
- **Proposed resolution**: Add explicit stall-only overrides to the seeder contract: --merge false and --draft false (or equivalent Python stall-profile flags) on the Step 5 missing-state wrapper invocation, matching today's forced values.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/references/step5-review-branches.md:11
- **Concern**: Step 5 stall seed must force MERGE=false and DRAFT=false but seeder stall overrides omit them. Scenario: The plan’s stall wrapper only passes --stall-tracking/--stall-step/--bail-reason while step-8-seed-initial.sh reads MERGE/DRAFT from session via read_session_key. Today’s stall seed explicitly overrides DRAFT=false and MERGE=false even when the run was started with --merge/--draft. A /implement --merge run that stalls at Step 5 would seed ship-pr-state.sh with MERGE=true and later Step 8+ could treat merge as enabled during a stall-only path.
- **Proposed resolution**: Add a stall-seed profile to seed-initial-state (or wrapper flags --merge false --draft false) that mirrors the current stall override block; extend python/test_ship.py stall override test to assert MERGE=false and DRAFT=false when session merge/draft are true.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:391-392
- **Concern**: The plan adds source-only `skills/implement/scripts/lib-implement-clone-tag.sh` but does not list an `agent-lint.toml` G004 exclusion for it (same pattern as `lib-resolve-implement-tmpdir.sh`).. Scenario: `make lint` / agent-lint G004 scans SKILL.md literal invocations and does not follow shell `source` edges; the clone-tag helper may be flagged unreachable/dead and block the PR.
- **Proposed resolution**: Add `### UPDATED: agent-lint.toml` (or fold into an existing lint-touch surface): exclude `skills/implement/scripts/lib-implement-clone-tag.sh` and `lib-implement-clone-tag.md` with a sourced-only comment mirroring `lib-resolve-implement-tmpdir.sh`.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:75-117
- **Concern**: Plan adds NO_ADMIN_FALLBACK to _ALLOWED_SHIP_STATE_KEYS but does not require the initial canonical constant to match the write-initial-state-keys marker byte-for-byte in one ordered list. Scenario: ship.py today omits NO_ADMIN_FALLBACK from _ALLOWED_SHIP_STATE_KEYS while the SKILL marker and step-8-ship.sh already read/pass it; if seed-initial-state writes NO_ADMIN_FALLBACK but the first _write_ship_state refresh still drops it until driver emission is wired, merge/admin routing can disagree between seeded state and argv
- **Proposed resolution**: When defining the canonical initial key constant, include NO_ADMIN_FALLBACK with the same default as the marker, assert the full ordered key list (marker keys + OOS_PENDING=false) in python/test_ship.py, and add one test that _write_ship_state preserves NO_ADMIN_FALLBACK after the allowed-keys change

### FINDING_5:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-seed-initial.sh (new); python/bootstrap.py:28-45; python/session_env.py:438-463
- **Concern**: Seeder wrapper lacks durable sources for required dynamic keys. Scenario: The one-line Step 8 fence passes no dynamic argv, larch-run only resolves tmpdir/plugin root, and session-env does not carry all required seed values such as BRANCH_NAME, ISSUE_NUMBER, MANIFEST_PATH, TOOL_LABEL, no-admin, and no-logs. A cold Step 8 seed can write empty or defaulted canonical keys, then ship-pr stalls or loses manifest/no-logs behavior.
- **Proposed resolution**: Define the wrapper source order per key. Read bootstrap-routing.env for Step 0 routing keys, map LARCH_RUN_ID when needed, and pass or persist Step 2/prompt-only values such as MANIFEST_PATH, TOOL_LABEL, merge/draft, no-admin, and no-logs before seeding. Extend the wrapper harness with realistic Step 0 and Step 2 files.

### FINDING_6:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-8-seed-initial.md (new); scripts/test-implement-structure.sh
- **Concern**: The plan requires and forbids the same retired helper reference. Scenario: The new seeder docs are told to explicitly cite scripts/read-session-env-key.sh, while the structure test is told to forbid seeder/wrapper contracts from referencing read-session-env-key.sh. Implementing both makes the planned validation fail.
- **Proposed resolution**: Narrow the forbid assertion to executable call sites, or remove the literal retired-helper path from the new docs. Keep the required behavior as “use python/cli.py session read-key.”

### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/stall_recovery.py:1079-1083
- **Concern**: [SCOPE-REDUCTION] Terminal stall seeder change conflicts with the non-goal. Scenario: The approach says to keep stall-recovery seed-terminal-state unchanged, but also says to make the terminal stall path fail closed on a non-empty ship-pr-state.sh. Current terminal recovery rewrites STALL_TRACKING, STALL_STEP, and PHASE into an existing driver state; removing that rewrite can break existing transient-to-stall recovery.
- **Proposed resolution**: Remove the terminal-stall fail-closed bullet. Limit create-if-absent semantics to the new initial ship-pr-state seeder.
