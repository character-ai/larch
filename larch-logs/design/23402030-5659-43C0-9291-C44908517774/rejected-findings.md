### [Plan Review] FINDING_6

### FINDING_6: Preserve the zero-voter plan-review stub path
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The `eligible == 0` plan-review path must remain classification-only and must not emit ledger, rendering, or artifact outputs through unified serializers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep the `eligible == 0` early return explicit: engine stub contexts produce classification inputs only; skip `_render`, `_write_findings_ledger`, and all artifact writers. Add parity coverage in `test_plan_review.py` proving no `oos.md` / `accepted-plan-findings.md` bytes are written on this path.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/tests/review/test_review_tally.py:230-2950; python/tests/review/test_plan_review.py:1846-4261
- **Concern**: [SCOPE-REDUCTION] The plan modifies acceptance suites that must pass unchanged. Scenario: These suites already cover the listed tally paths. Editing them violates the explicit acceptance contract and needlessly enlarges the diff
- **Proposed resolution**: Remove their UPDATED headings. Run them unchanged and keep new coverage in the focused engine and parser tests


