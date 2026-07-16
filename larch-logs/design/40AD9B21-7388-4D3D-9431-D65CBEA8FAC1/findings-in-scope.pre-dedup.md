### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: .github/workflows/duplicate-code.yaml:93
- **Concern**: Prior accepted failure-only owner-path fix is incomplete: an outcome-only condition is skipped after a failed lint step. Scenario: GitHub Actions implicitly applies success() unless the condition includes a status function, so the issue step never runs when duplicate_code fails
- **Proposed resolution**: Require `if: ${{ failure() && steps.duplicate_code.outcome == 'failure' }}` and retain the outcome check



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/duplicate_code.py:37-41
- **Concern**: Prior accepted per-observation identity fix is incomplete: one baseline row may grandfather multiple distinct shrink observations. Scenario: Replacing one baseline block with two distinct non-overlapping shorter windows lets both match the same stored text, so new clusters pass while the baseline row is merely represented
- **Proposed resolution**: Require an injective baseline-to-live match; treat surplus observations as new or ambiguity errors, and add the two-window regression test



