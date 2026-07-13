# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 3 adapter and wrapper behavioral coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The named Step 3 harness lacks planned behavioral coverage for session-env launches, resume replacement, marker handling, terminal routes, pause publication, and merge-publication failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Fresh-attempt marker clearing can race with daemon startup
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing, dyn-dyn-adapter-races
- **Severity**: major
- **Concern**: Clearing the completion marker after daemon startup can race with a fast child, fail after a live daemon has started, or emit `STARTED` before the adapter ultimately reports failure, leaving stale state or an orphaned job.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-adapter-races: Defer emitting `BGJOB_STATUS=STARTED` until `_clear_before_fresh` succeeds (for example, have `start_daemon` return PGID without printing, and print only from `_start_fresh` after a successful clear), or on clear failure terminate the just-started daemon/registry row and ensure stdout contains only the error token. Add a regression test for `clear-on-fresh-failed` after a successful daemon start.


### FINDING_4: Resume replacement lacks behavioral coverage
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Static assertions do not prove that a completed Step 3 result is replaced with a fresh child during resume rather than reattached.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
