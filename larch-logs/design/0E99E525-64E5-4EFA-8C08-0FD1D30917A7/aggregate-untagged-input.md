### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: Rewrite contract omits live inline-path obligations still enforced elsewhere. Scenario: The plan's ship-pr-ci-fix.md required sections and harness preserve list drop ledger_ready record-escalation, enumerate-all-failures/flaky-defect doctrine, run-log refresh before push, and the main-health repair carve-out, while ship-pr-exit-matrix.md line 36 and scripts/test-implement-step8-exit3-first-fixer.sh still pin those needles today
- **Proposed resolution**: Add explicit preserve bullets for ledger escalation, flaky-defect-unfixed handling, inline enumerate-all-failures repair, run-log refresh, and main-health repair routing to kill-switch and post-bail inline sections; extend the harness preserve list to match or document intentional removal with exit-matrix updates in the same change set

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: Ledger escalation missing from fixer pre-spawn sequence. Scenario: ship-pr-exit-matrix.md requires stall-recovery record-escalation before any ci-fix edits; the default fixer path spawns an Agent that mutates the checkout but the pre-spawn distill fence never gates on ledger_ready Insert When ledger_ready=true call stall-recovery record-escalation immediately after preconditions and before ci distill-log or fixer-spawned.sentinel on every path that may edit the repo including default fixer spawn
- **Proposed resolution**:

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci.py
- **Concern**: distill-log must not reuse tail-only collect_failed_logs. Scenario: Approach requires every failing job in the digest but ci.py says call existing gh log reader; collect_failed_logs keeps only the last CI_MONITOR_LOG_TAIL_LINES of combined output so multi-job failures lose evidence in one fixer round
- **Proposed resolution**: Implement distill_log_main against gh run view --log-failed with per-job section parsing head/tail caps and shard dedupe; forbid delegating to collect_failed_logs or other repo-wide tail truncation helpers

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: fixer-status.env machine handoff grammar is undefined. Scenario: Success routing reads fixer-status.env only yet the plan lists filenames and exit-matrix prose labels without a KV write contract for the fixer or a parser contract for the main agent
- **Proposed resolution**: Define fixer-status.env rows such as STATUS and OUTCOME using config.py token literals matching ci-fixer-success and sibling bail codes; document required keys in ship-pr-ci-fix.md and add parser tests in test_ci.py or a focused harness

### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-ci-fix.md
- **Concern**: Post-bail inline fallback underspecifies the repair tail. Scenario: Kill-switch path binds to the existing inline procedure with checks commit run-log refresh push and step-8-ship relaunch; post-bail only names fallback-attempts.count so implementers may ship a counter-only loop without the full repair sequence
- **Proposed resolution**: State post-bail inline reuses the kill-switch repair tail verbatim with fallback-attempts.count substituted for the 30-attempt main-agent counter and fixer-bail.md read before the first attempt

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:23-27
- **Concern**: evaluate_failure() still does log collection and transient rerun work before the supposed immediate handoff. Scenario: The non-rebase path is meant to mirror first-fixer-non-health and avoid log download, but the preamble would still fetch CI logs and may spend time on rerun logic before returning.
- **Proposed resolution**: Move the ci_fix_rebase_pending=false return ahead of collect_failed_logs/rerun_failed, or split a tiny handoff helper that does no CI I/O.

### FINDING_7:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:49-61
- **Concern**: The plan names fixer-status.env and fixer-rounds.tsv as durable handoff files but never assigns a write contract or schema. Scenario: The success path depends on reading fixer-status.env, and the round ledger is supposed to make the loop auditable, but nothing says who writes these files or what keys/columns they must contain. That leaves the handoff unverifiable.
- **Proposed resolution**: Add an explicit writer contract: the fixer or wrapper must update fixer-status.env on every exit path with the consumed status keys and append fixer-rounds.tsv each round before ci wait.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ci_monitor.py:1816-1865
- **Concern**: Non-pending evaluate_failure still prefetched logs and can rerun. Scenario: 
- **Proposed resolution**: The plan says `ci_fix_rebase_pending=false` should hand off immediately with no log download or classification loop, but the current outline leaves `collect_failed_logs()`, the in-progress wait, and the transient rerun ahead of that branch. The main agent can still block on GitHub I/O or rerun the failing CI before it reaches `first-fixer-non-health`, and `test_evaluate_failure_transient_rerun_only` will be wrong unless it is rewritten. Move all log collection, in-progress waiting, and transient-rerun logic behind the `ci_fix_rebase_pending=true` path, or delete them for the non-pending path, and update or remove `test_evaluate_failure_transient_rerun_only` to match the new no-prefetch contract.

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/core/test_config.py:7-12
- **Concern**: Remove stale CI_AGENTIC_FIX_MAX_CYCLES assertions alongside config cleanup. Scenario: 
- **Proposed resolution**: The plan removes `CI_AGENTIC_FIX_MAX_CYCLES`, but this test still asserts it, and `python/tests/implement/test_ci_monitor.py:3325-3334` still monkeypatches it. The suite will go red as soon as config.py drops the symbol. Replace those checks with the new `CI_FIXER_*` constants or delete the affected tests in the same change set.
