# Review Round 1

- Mode: `diff`
- 4 accepted, 0 rejected (2 neutral)

## Accepted Findings

### FINDING_3: correctness: stale renderer baseline rows are rejected as malformed
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: A baseline row whose function_name no longer matches the live renderer predicate is treated as malformed instead of stale, so the lint exits 2 instead of reporting the drift and exiting 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: correctness: non-UTF-8 renderer inputs can crash the lint
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: read_text only catches OSError, not UnicodeDecodeError, so a non-UTF-8 report, test, or baseline file can crash the lint instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Catch UnicodeDecodeError alongside OSError in the read helpers, and return TOOL_FAILURE_EXIT for any read or decode failure.


### FINDING_7: correctness: non-UTF-8 source files can crash the wrapper-bypass lint
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: scan_file only catches OSError on source reads, so a malformed production file can crash the lint instead of returning TOOL_FAILURE_EXIT.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Catch UnicodeDecodeError with OSError in scan_file(), and return TOOL_FAILURE_EXIT on any read or decode failure.


### FINDING_8: risk-integration: missing fail-closed regression test for write mode
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The test suite does not cover the case where --write encounters new live rows without preserved reasons or --initial-reason metadata, so the fail-closed contract could regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add test_write_fails_when_new_rows_lack_reasons mirroring test_lint_lifecycle_prefix_literal.py.


