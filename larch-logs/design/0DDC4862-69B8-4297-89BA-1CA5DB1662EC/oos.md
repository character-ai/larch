### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/batch_report.py:324-338
- **Concern**: [SCOPE-REDUCTION] Success cleanup can erase the required tally-failure trace. Scenario: A first Step 5 flush can fail and write code-review-tally.flush.err plus a Warnings entry, then a later flush in the same run can succeed and unlink the run-root sidecar. The committed warning then points at a missing file, losing the rc, stderr, and stdout the issue requires for root-cause capture.
- **Proposed resolution**: Do not unlink the run-root code-review-tally.flush.err on success. At most unlink the tmpdir-only sidecar, and adjust the stale-sidecar test to preserve committed failure evidence.

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

