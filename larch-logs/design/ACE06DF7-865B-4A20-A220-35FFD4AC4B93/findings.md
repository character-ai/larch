### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:518-551
- **Concern**: CI/probe row filter omits basename normalization for ledger output column. Scenario: The plan matches output basenames like ci.out and ci-fix-*.out but does not require Path(output).name before those checks. render-review-phase-detail.sh uses base(out). Ledger rows and tests can store full paths (see scripts/test-render-review-phase-detail.sh). Live inflight Gantt can still show CI/probe bars when only the dirname differs.
- **Proposed resolution**: In the new filter helper, derive basename = Path(output_col).name when output_col else "" and run all output-basename predicates on basename. Add a regression row with a full-path ci-fix output.

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:1642-1683
- **Concern**: MAIN_ADVANCED rebase must not copy the monitor.goto_rebase iteration guard verbatim. Scenario: The plan says route MAIN_ADVANCED through the same path as monitor.goto_rebase, but that path increments iteration only when monitor.action is wait or goto_rebase is true (ship.py:1642-1643). On MAIN_ADVANCED, monitor.action is merge, so a literal copy leaves iteration unchanged and breaks the merge loop cap and CI retry semantics; the old code incremented iteration at 1674
- **Proposed resolution**: Reuse flush, rebase_and_push, PrePushConflictHandoff, rebase_count, and ci-initial state writes from the goto_rebase block, but branch MAIN_ADVANCED out of the shared CI_NOT_READY bucket before ship.py:1673-1683 and increment iteration unconditionally after a successful MAIN_ADVANCED rebase pass; do not gate iteration on monitor.goto_rebase

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/rebase.py:188-213
- **Concern**: Fallback sidecar freshness conflicts with path-only seen_token_records. Scenario: After the proposed pre-clear, a second Codex or Cursor conflict-fix launch can write a fresh ${output}.token-record at the same path, but the existing seen set still contains that path from the first launch, so append-record skips the new usage and rebase token accounting remains partially dropped
- **Proposed resolution**: When pre-clearing the expected fallback path, also discard that exact path from seen_token_records, and add a two-launch fallback test that proves both fresh sidecars are appended
