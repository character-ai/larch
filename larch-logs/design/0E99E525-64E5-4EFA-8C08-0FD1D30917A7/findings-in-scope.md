### FINDING_1: Missing ledger gate and preserved inline obligations
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The ship-pr-ci-fix prompt/contract drops required live-path safeguards and does not clearly enforce the pre-spawn record-escalation gate, so the fixer loop can run without the ledger handoff or other inline obligations that remain load-bearing elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit preserve bullets for ledger escalation, flaky-defect-unfixed handling, inline enumerate-all-failures repair, run-log refresh, and main-health repair routing to kill-switch and post-bail inline sections; extend the harness preserve list to match or document intentional removal with exit-matrix updates in the same change set

### FINDING_2: Distill log must not tail-truncate failures
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The distill-log path appears to rely on tail-only CI log collection, which can omit failures from multi-job runs and leave the fixer with incomplete evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Implement distill_log_main against gh run view --log-failed with per-job section parsing head/tail caps and shard dedupe; forbid delegating to collect_failed_logs or other repo-wide tail truncation helpers

### FINDING_3: Undefined handoff schema for fixer status and rounds
- **Reviewer(s)**: Cursor-Arch, Codex-Arch
- **Severity**: major
- **Concern**: The fixer handoff files do not have a defined write/read contract, so status reporting and the round ledger remain unverifiable and easy to desynchronize.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Define fixer-status.env rows such as STATUS and OUTCOME using config.py token literals matching ci-fixer-success and sibling bail codes; document required keys in ship-pr-ci-fix.md and add parser tests in test_ci.py or a focused harness
  - From Codex-Arch: Add an explicit writer contract: the fixer or wrapper must update fixer-status.env on every exit path with the consumed status keys and append fixer-rounds.tsv each round before ci wait.

### FINDING_4: Post-bail inline fallback underspecifies the repair tail
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: The post-bail inline path names the counter but not the full repair sequence, so implementers could accidentally ship a counter-only loop instead of the intended fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State post-bail inline reuses the kill-switch repair tail verbatim with fallback-attempts.count substituted for the 30-attempt main-agent counter and fixer-bail.md read before the first attempt

### FINDING_5: Non-pending failure path still does CI I/O
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The non-pending evaluate_failure path still does log collection and transient rerun work before the intended immediate handoff, which can block the main agent on GitHub I/O or rerun the failing CI when it should return early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Move the ci_fix_rebase_pending=false return ahead of collect_failed_logs/rerun_failed, or split a tiny handoff helper that does no CI I/O.
  - From Codex-Innovation: The plan says `ci_fix_rebase_pending=false` should hand off immediately with no log download or classification loop, but the current outline leaves `collect_failed_logs()`, the in-progress wait, and the transient rerun ahead of that branch. The main agent can still block on GitHub I/O or rerun the failing CI before it reaches `first-fixer-non-health`, and `test_evaluate_failure_transient_rerun_only` will be wrong unless it is rewritten. Move all log collection, in-progress waiting, and transient-rerun logic behind the `ci_fix_rebase_pending=true` path, or delete them for the non-pending path, and update or remove `test_evaluate_failure_transient_rerun_only` to match the new no-prefetch contract.

### FINDING_6: Stale CI_AGENTIC_FIX_MAX_CYCLES assertions after config cleanup
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The config cleanup will break existing tests unless the stale CI_AGENTIC_FIX_MAX_CYCLES assertions and monkeypatches are removed or rewritten alongside the symbol deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: The plan removes `CI_AGENTIC_FIX_MAX_CYCLES`, but this test still asserts it, and `python/tests/implement/test_ci_monitor.py:3325-3334` still monkeypatches it. The suite will go red as soon as config.py drops the symbol. Replace those checks with the new `CI_FIXER_*` constants or delete the affected tests in the same change set.
