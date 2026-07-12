### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Retry clears the only captured child diagnostic
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-fd-lifecycle
- **Severity**: major
- **Concern**: An attempt-1 `ASSESSMENT_CHILD_DETAIL` is cleared before retry; if attempt 2 produces no stderr, the terminal fail-closed outcome loses the only actionable diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-fd-lifecycle: Before `clear_stale_state` on retry, read and retain the last non-empty sanitized `ASSESSMENT_CHILD_DETAIL` from merge/result env; carry it into attempt 2’s merge seed or into `publish_fail_closed_terminal` unless attempt 2 produces its own non-empty sanitized detail. Add a harness case that fails attempt 1 with stderr, retries, and asserts the terminal fail-closed envelope keeps attempt 1’s detail when attempt 2 stderr is empty.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Sanitization may read empty data after raw-file unlink
- **Reviewer(s)**: dyn-dyn-fd-lifecycle
- **Severity**: major
- **Concern**: The raw stderr path is unlinked before sanitization reads FD 4, allowing non-empty captured stderr to produce an empty successful detail without failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-fd-lifecycle: Sanitize before unlinking (read from the file path or pass the captured byte count back and fail closed when `written>0` but sanitized output is empty), or reopen the temp file for read after the drainer exits; only then remove the raw file and write merge KVs.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
