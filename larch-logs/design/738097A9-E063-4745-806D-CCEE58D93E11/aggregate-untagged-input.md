### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/progress_report.py:54-59
- **Concern**: _prior_immediate_round_end_s must skip malformed v1 round rows. Scenario: The new helper takes max(int(cols[7])) with no try/except; a corrupt or partial ledger row matching skill and round_n can raise ValueError and break the live p/progress report on the new fallback path where the old phase-start fallback returned a chart
- **Proposed resolution**: In _prior_immediate_round_end_s, wrap int(cols[7]) in try/except ValueError and skip bad rows, matching _progress_vendor_rows parsing style

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: python/review_and_fix.py:1923-1928, python/review_and_fix.py:2082-2085
- **Concern**: Implement round-start writer still follows symlinks when moved to the normal start path. Scenario: The plan expands _persist_round_start from escalation-only to every normal Step 5 round; a precreated round-N directory symlink or dangling round-start-s symlink under IMPLEMENT_TMPDIR can redirect the timestamp write outside the tmpdir before review starts
- **Proposed resolution**: Mirror the design helper's no-follow write-once guards in _persist_round_start: skip symlinked round dirs and symlinked round-start-s paths, create only regular round dirs, and write only when the target is absent as a non-symlink
