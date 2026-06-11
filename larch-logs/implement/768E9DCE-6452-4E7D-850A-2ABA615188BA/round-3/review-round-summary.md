# Review Round 3

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: token/timing callers still pass --ledger before the verb
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Migrated token and timing harness calls still place `--ledger` before the subcommand, but `python/cli.py` requires the verb first. This makes retained tests abort before exercising the migrated behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: JSON reports lack arbitrary vendor sibling coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No pytest covers dynamic non-Claude vendor JSON sibling objects required by acceptance. Custom vendor rows could disappear from JSON reports or emit empty objects that trigger downstream corrupt-zero warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_11: timing harness-mark tests do not assert sentinel format
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test_timing_harness_mark_runs_command` only checks child exit code. Sentinel format or non-zero propagation can regress without failing pytest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: timing ledger normalization and warning paths lack coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Missing tests for timing vendor rejection, task-kind warnings, and OK/ERROR/TIMEOUT status normalization. Unknown vendors or status alias bugs could corrupt timing reports or flood warnings without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_3: timing ledger validation creates directories before containment checks
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `validate_ledger_path` can create a candidate parent directory before proving the resolved path is under an allowed root. A symlinked parent can cause directory creation outside the allowed tree before rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_5: timing mark leaks ValueError for invalid ledger paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `timing_mark_main` does not catch `ValueError` from `_ensure_ledger` on invalid ledger paths. A symlink or FIFO timing ledger can produce an uncaught traceback instead of a clean exit 1 diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: token cost CLI golden coverage was lost
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Deleted bash golden harnesses for `token cost` and `render-cost-line` were replaced by internal pricing tests only. CLI grammar or `TOTAL_COST=` regressions can merge while production summaries break.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: TokenLedger lacks tests rejecting claude vendor rows
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No pytest asserts `TokenLedger.record_vendor` rejects vendor `claude`. A future change could allow Claude rows in the JSONL ledger and double-count usage against transcript totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


