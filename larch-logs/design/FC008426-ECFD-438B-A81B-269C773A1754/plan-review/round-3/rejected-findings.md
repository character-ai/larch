### [Plan Review] FINDING_1

### FINDING_1: `rebase_then_evaluate` defers fix to a second `monitor()` poll
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `rebase_then_evaluate` defers fixing to a second `monitor()` poll after driver rebase. In Bash, `run_rebase_rebump` is followed immediately by `run_evaluate_failure` (`scripts/ship-pr.sh:3547-3549`). Re-polling can return `wait`/`pending` while CI is still running and skip the fix path that Bash always enters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Phase 7 contract: after `goto_rebase` from `rebase_then_evaluate`, call `evaluate_failure` directly (or add a monitor flag) instead of relying only on a fresh `poll_ci`.


