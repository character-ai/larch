### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-merge-pr.sh:49-50
- **Concern**: Plan omits the exhausted-transient gh pr checks case even though merge-pr.sh will add special handling for exhausted transient stdout. Scenario: A bad implementation could preserve garbage or stale stdout after all retry attempts fail and let refresh_ci_state parse it as usable check data before an admin merge
- **Proposed resolution**: Add one test where gh pr checks fails with a transient signature on all retry attempts and emits non-empty stdout that looks parseable or misleading; assert MERGE_RESULT=ci_not_ready, no merge command runs, and the checks call count matches the retry budget

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-create-pr.sh:1-10
- **Concern**: Transient-retry harness cases omit instant backoff stub. Scenario: Planned once-fail-then-succeed cases call with_transient_retry which sleeps 2s then 4s via scripts/sleep-seconds.sh when SLEEP_SCRIPT_DIR is unset; new create-pr merge-pr and rebase-push harness cases add multi-second wall time and shard timing risk
- **Proposed resolution**: Reuse the test-clarify-comment.sh pattern: export SLEEP_SCRIPT_DIR to a stub dir with a no-op sleep-seconds.sh in test-create-pr.sh test-merge-pr.sh and the new rebase-push harness before any transient-retry invocation

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: .claude/rules/script-md-siblings.md:7-12
- **Concern**: Plan updates test harness scripts but omits their sibling contract docs. Scenario: Following the plan changes scripts/test-create-pr.sh and scripts/test-merge-pr.sh while leaving scripts/test-create-pr.md and scripts/test-merge-pr.md stale, violating the repo script sibling contract
- **Proposed resolution**: Add UPDATED entries for scripts/test-create-pr.md and scripts/test-merge-pr.md with minimal notes for the new transient retry/fallback coverage

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/merge-pr.sh:133-163
- **Concern**: JSON-path transient exhaustion still runs text gh pr checks fallback. Scenario: After the primary wrapped gh pr checks --json call exhausts on a transient signature, CHECKS_JSON is empty but the existing if/else still enters the text fallback branch; a second wrapped gh pr checks call can succeed and set CI_GOOD=true, breaking the edge-case contract that both captures stay empty and violating test case (3) call-count intent
- **Proposed resolution**: Record a transient-exhausted flag (or equivalent) when the JSON wrapper’s fail file matches is_transient_net_signature after exhaustion, skip the text fallback in that case, and leave CI_GOOD=false; state this explicitly in the refresh_ci_state plan step

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-shell-strictness, Codex-dyn-shell-strictness
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:52-62; scripts/test-rebase-push-keep-on-conflict.sh:61-83
- **Concern**: New standalone rebase-push fetch harness is scope creep for SIMPLE tier. Scenario: The plan says no existing harness owns the --no-push fetch path, but test-rebase-push-keep-on-conflict.sh already drives --no-push through the fetch/rebase flow; adding a new .sh, .md, Makefile target, shard entry, and agent-lint exclusions expands maintenance surface without a correctness need
- **Proposed resolution**: Extend scripts/test-rebase-push-keep-on-conflict.sh with the transient-once and persistent-fetch-failure cases, and drop the NEW harness plus its Makefile and agent-lint additions

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-wiring-fidelity, Codex-dyn-wiring-fidelity
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: Makefile:48-67,95-99; <TMPDIR>/plan.txt:61-62
- **Concern**: Shard assignment is ambiguous even though the related shard lines are already occupied by rebase-push harnesses. Scenario: Shard 14 has test-rebase-push-force-lease, shard 15 has test-rebase-push-fork-mode, and shard 16 has test-rebase-push-keep-on-conflict; the plan's "shard 14 or 16" leaves the post-PR wiring non-deterministic
- **Proposed resolution**: Replace "e.g. shard 14 or 16" with one concrete existing shard assignment for this new harness, preferably test-harnesses-15 unless the implementer has fresh timing data

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-wiring-fidelity, Codex-dyn-wiring-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/rules/script-md-siblings.md:7-11; scripts/test-rebase-push-force-lease.md:3-26; <TMPDIR>/plan.txt:55-56
- **Concern**: The new sibling md contract does not explicitly require the established Scope/Coverage and Edit-in-sync fields. Scenario: The plan asks for purpose, primary target, Makefile wiring, and invariants only; the new harness doc could land without the coverage list and edit-sync rule used by the fuller rebase-push harness contract pattern
- **Proposed resolution**: Revise the NEW md bullet to require Purpose, Coverage or Scope listing the transient-success and persistent-failure cases, Makefile wiring or invocation, and Edit-in-sync rules for scripts/rebase-push.sh and scripts/rebase-push.md
