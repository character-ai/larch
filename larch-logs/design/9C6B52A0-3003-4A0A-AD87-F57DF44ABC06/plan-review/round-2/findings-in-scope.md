### FINDING_1: Missing exhausted transient checks test
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: important
- **Concern**: The plan does not cover the case where `gh pr checks` exhausts all transient retry attempts while emitting misleading non-empty stdout, which could allow stale or parseable garbage to influence CI state before an admin merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add one test where gh pr checks fails with a transient signature on all retry attempts and emits non-empty stdout that looks parseable or misleading; assert MERGE_RESULT=ci_not_ready, no merge command runs, and the checks call count matches the retry budget

### FINDING_2: Retry tests need no-op sleep stub
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Planned transient retry harness cases can incur real multi-second sleeps when `SLEEP_SCRIPT_DIR` is unset, adding wall time and timing risk across create-pr, merge-pr, and rebase-push tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reuse the test-clarify-comment.sh pattern: export SLEEP_SCRIPT_DIR to a stub dir with a no-op sleep-seconds.sh in test-create-pr.sh test-merge-pr.sh and the new rebase-push harness before any transient-retry invocation

### FINDING_3: Existing test script docs left stale
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The plan updates existing test harness scripts without updating their sibling `.md` contract files, violating the repository’s script sibling documentation contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add UPDATED entries for scripts/test-create-pr.md and scripts/test-merge-pr.md with minimal notes for the new transient retry/fallback coverage

### FINDING_4: Exhausted JSON retry can fall through to text checks
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: If the wrapped JSON `gh pr checks --json` call exhausts due to a transient signature, the existing flow can still enter the text fallback branch, allowing a later checks call to succeed and incorrectly mark CI as good.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Record a transient-exhausted flag (or equivalent) when the JSON wrapper’s fail file matches is_transient_net_signature after exhaustion, skip the text fallback in that case, and leave CI_GOOD=false; state this explicitly in the refresh_ci_state plan step

### FINDING_5: New rebase-push harness is unnecessary scope
- **Reviewer(s)**: Cursor-dyn-shell-strictness, Codex-dyn-shell-strictness
- **Severity**: nit
- **Concern**: The proposed standalone rebase-push fetch harness adds new files and wiring even though an existing keep-on-conflict harness already exercises the `--no-push` fetch/rebase path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-shell-strictness, Codex-dyn-shell-strictness: Extend scripts/test-rebase-push-keep-on-conflict.sh with the transient-once and persistent-fetch-failure cases, and drop the NEW harness plus its Makefile and agent-lint additions

### FINDING_6: Rebase-push shard assignment is ambiguous
- **Reviewer(s)**: Cursor-dyn-wiring-fidelity, Codex-dyn-wiring-fidelity
- **Severity**: nit
- **Concern**: The plan leaves the new rebase-push harness shard assignment open-ended even though nearby shard slots are already occupied, making post-PR wiring non-deterministic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wiring-fidelity, Codex-dyn-wiring-fidelity: Replace "e.g. shard 14 or 16" with one concrete existing shard assignment for this new harness, preferably test-harnesses-15 unless the implementer has fresh timing data

### FINDING_7: New rebase-push sibling doc requirements are incomplete
- **Reviewer(s)**: Cursor-dyn-wiring-fidelity, Codex-dyn-wiring-fidelity
- **Severity**: important
- **Concern**: The proposed new harness documentation requirements omit established sibling-doc fields such as explicit coverage/scope and edit-in-sync rules, so the new contract doc could land below the pattern used by existing rebase-push harness docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-wiring-fidelity, Codex-dyn-wiring-fidelity: Revise the NEW md bullet to require Purpose, Coverage or Scope listing the transient-success and persistent-failure cases, Makefile wiring or invocation, and Edit-in-sync rules for scripts/rebase-push.sh and scripts/rebase-push.md
