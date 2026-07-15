# Review Round 1

- Mode: `diff`
- 7 accepted, 7 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Merge commits have no test discovery diff
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Merge fix commits are not diffed against a parent, so tests introduced by a merge can be treated as absent and skipped.


### FINDING_4: Runtime failure evidence loses the bounded stderr/stdout tail
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Evidence selection can omit the relevant failure tail and use leading output instead of combining both streams and retaining the bounded tail.


### FINDING_5: Planned runtime integration tests are largely missing
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Runner failures, continuation, budgets, report overlays, accounting, workflow order, and CLI behavior lack the plan-required integration coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add injected-runner integration tests for those plan-specified paths.
  - From cursor-specialist-testing: Add render_report golden tests, budget/SHA-order tests, multi-SHA continue-on-failure, and analyze-bugs runtime CLI help per the plan file list.
  - From codex-specialist-testing: Add focused tests for the omitted plan-required runtime paths and report assertions.


### FINDING_7: Absent or skipped runtime outcomes remain verified
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Absent and skipped runtime results can inflate verified snapshots and confirmed-fixed counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Track runtime certification and exclude absent or skipped rows from accounting.


### FINDING_8: Verified-predicate and snapshot changes lack regression tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Changes to `_verified_issue` and `VERIFIED_PREDICATE_VERSION` lack tests covering verified counts, deltas, runtime SUSPECT exclusion, and predecessor snapshots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add tests for narrowed _verified_issue, runtime SUSPECT exclusion, and predecessor snapshot handling after predicate bump.


### FINDING_9: Timeout and harness failures lack end-to-end runtime coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Timeout and make-harness failure handling is tested only through `_runtime_overlay`, not through `runtime_verify`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Exercise runtime_verify with injected timeout and failing make results, then assert JSONL and report overlay.


### FINDING_10: Runtime CLI dispatch lacks tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Runtime subcommand registration and argument handling are not covered by CLI tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add run_cli help and minimal argv tests for analyze-bugs runtime.
