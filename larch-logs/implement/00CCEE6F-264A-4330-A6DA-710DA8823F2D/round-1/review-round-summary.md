# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_3: PR-create tests do not prove the warning reaches committed run logs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-runlog-flush
- **Severity**: important
- **Concern**: The PR-create coverage still only checks call order around mocked `flush_logs_pre`. It does not exercise the real flush path or assert that `larch-logs/implement/<run-id>/execution-issues.ndjson` contains the architectural-guidelines warning before `ensure_pr` completes, so regressions in log rendering or batch commit could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add parameterized integration tests that run real flush_logs_pre and assert execution-issues.ndjson contains the architectural-guidelines warning.
  - From cursor-specialist-correctness: Assert return True and persist-failure warning text in execution-issues.md.
  - From cursor-specialist-edge-cases: Add integration test with real pin/flush, run-log manifest, step7a sentinel; assert execution-issues.ndjson contains the warning before ensure_pr (merge and non-merge)
  - From cursor-specialist-testing: Add parameterized ship integration tests using real flush_logs_pre that assert architectural-guidelines warning text in larch-logs/implement/<run-id>/execution-issues.ndjson before ensure_pr completes.
  - From codex-specialist-correctness: Add the plan-required regression tests using real run-log manifest/temp execution-issues plumbing, and assert the committed ndjson warning before ensure_pr or the simulated clean merge.
  - From codex-specialist-edge-cases: Add the planned regression coverage with a real tmp run-log manifest and real flush_logs_pre, asserting the committed execution-issues.ndjson contains the architectural-guidelines warning before ensure_pr for both merge and non-merge PR creation, plus the CI-fix path.
  - From codex-specialist-testing: Add integration-style tests using a real temp implement tmpdir, run-log manifest, Step 7a marker, and real warning append/flush path; assert the committed `execution-issues.ndjson` contains the architectural-guidelines warning before PR push for both non-merge and first-try `--merge`, and before the CI-fix branch push.
  - From dyn-dyn-runlog-flush: Add integration-style tests that run the real flush/commit path (minimal git repo + run-log manifest + `.execution-issues-step7a-reached`), then assert `execution-issues.ndjson` contains the guidelines warning before push/merge completes; parameterize over merge and non-merge PR-create paths and over CI-fix success after a simulated push-or-refresh retry.


### FINDING_4: CI-fix tests do not prove the warning reaches committed run logs
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-runlog-flush
- **Severity**: important
- **Concern**: The CI-fix regression coverage still mocks `stage_and_push` and manually invokes the callback. It does not exercise the real warning-triggered refresh-and-push path or assert committed `execution-issues.ndjson` contents, so the Step 7a to Step 8+ flush-timing race remains untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Implement planned harness: tmpdir manifest, step7a marker, forced invalidate warning, stubbed single push, assert ndjson contains warning
  - From cursor-specialist-testing: Add an end-to-end test: seed step7a marker + manifest + durable note, run real stage_and_push with invalidate callback, assert one push and warning content in execution-issues.ndjson.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Add the planned regression coverage with a real tmp run-log manifest and real flush_logs_pre, asserting the committed execution-issues.ndjson contains the architectural-guidelines warning before ensure_pr for both merge and non-merge PR creation, plus the CI-fix path.
  - From codex-specialist-testing: Add integration-style tests using a real temp implement tmpdir, run-log manifest, Step 7a marker, and real warning append/flush path; assert the committed `execution-issues.ndjson` contains the architectural-guidelines warning before PR push for both non-merge and first-try `--merge`, and before the CI-fix branch push.
  - From dyn-dyn-runlog-flush: Add integration-style tests that run the real flush/commit path (minimal git repo + run-log manifest + `.execution-issues-step7a-reached`), then assert `execution-issues.ndjson` contains the guidelines warning before push/merge completes; parameterize over merge and non-merge PR-create paths and over CI-fix success after a simulated push-or-refresh retry.


### FINDING_5: `--no-logs-commit` can stall warning-triggered flushes
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: The warning-triggered flush path treats `REFRESH_SKIP_NO_LOGS_COMMIT` as fatal. With `/implement --no-logs-commit`, a guidelines warning can stall before `pr.ensure_pr`, and the CI-fix seam can stall before push too, even though the flag is supposed to suppress log commits rather than block the workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Treat `no-logs-commit` as an explicit opt-out exception: warn that the guideline warning cannot be committed, then proceed, or reject the flag up front with a clear unsupported-combination error.


