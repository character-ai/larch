### FINDING_4: [OUT_OF_SCOPE] stale complexity-baseline rows for deleted ci_monitor symbols
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-ci-fixer-flow
- **Severity**: minor
- **Concern**: The complexity baseline still contains orphaned rows for symbols removed from ci_monitor.py, so the baseline drifts even though this branch does not introduce a runtime bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove stale rows in a hygiene follow-up
  - From cursor-specialist-edge-cases: Regenerate or prune baseline rows in a follow-up cleanup.
  - From cursor-specialist-testing: Regenerate or delete orphaned rows when touching complexity baseline.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_5: [OUT_OF_SCOPE] empty failed_jobs count on API parse failure
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: When GitHub log parsing fails, the job-count path can still emit FAILED_JOBS_COUNT=0 even though the failed-log digest has content, so the output understates what failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Treat parse failure as health error or derive count from parsed blocks
  - From cursor-specialist-edge-cases: Log API failure or emit a warning KV when cross-check cannot run.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: [OUT_OF_SCOPE] unreachable log prefetch on the default evaluate_failure path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The prefetch path under evaluate_failure is dead on the default ci_fix_rebase_pending=false route, so it does work that never affects the main handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Refactor prefetch behind ci_fix_rebase_pending=true only


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_15: [OUT_OF_SCOPE] skipped evaluate_failure coverage still uses an obsolete skip reason
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The skipped evaluate_failure cases still carry an obsolete skip reason, so the coverage gap is hidden behind a stale label rather than the current contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Unskip or rewrite against current evaluate_failure contract in a follow-up.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] progress-report rendering lacks a CI-fixer label assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Progress-report rendering is not asserting the CI-fixer label path, so a label-to-rendering gap could slip through if that code path diverges from token reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a progress-report assertion only if that code path renders step names independently.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_18: the default fixer path misses the required escalation gate before Agent dispatch
- **Reviewer(s)**: dyn-dyn-ci-fixer-flow
- **Severity**: major
- **Concern**: The default fixer path can dispatch an Agent without repeating the required `stall-recovery record-escalation` gate when `ledger_ready=true`, so the repo can be edited before the escalation record exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ci-fixer-flow: Insert an explicit “when `ledger_ready=true`, call `stall-recovery record-escalation` before `fixer-spawned.sentinel` and Agent dispatch” step in the default fixer path, and pin it in `scripts/test-implement-structure.sh`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_19: [OUT_OF_SCOPE] the default fixer path omits an explicit negated precondition for LARCH_CI_FIXER
- **Reviewer(s)**: dyn-dyn-ci-fixer-flow
- **Severity**: minor
- **Concern**: The default fixer path never states the negated precondition for `LARCH_CI_FIXER`, so a partial read could still spawn a fixer while the kill switch is set.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_20: [OUT_OF_SCOPE] timing reporting lacks a native task kind for the Agent-tool fixer span
- **Reviewer(s)**: dyn-dyn-ci-fixer-flow
- **Severity**: minor
- **Concern**: The timing report has no native Agent-style task kind for the fixer span, so `/report-tokens` can show timing without matching vendor cost rows.
- **Suggested revisions (informational for voters; coder decides)**:
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

