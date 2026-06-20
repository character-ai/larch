### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_quality.py:1509-1648
- **Concern**: Gate B MAY_UPDATE preservation is prompt-only, not enforced. Scenario: The plan says Gate B must not upgrade optional headings, but current validation only checks that some scope heading remains. A revise agent can convert `### MAY_UPDATE: python/run_logs.py` to `### UPDATED: python/run_logs.py`, pass waterfall validation, and reintroduce the same untouched-file false positive during `/implement`.
- **Proposed resolution**: Add a minimal post-revision validation for original optional-only paths. Reject and restore when one appears under firm headings after revision. Add one regression where a fake revise output converts MAY_UPDATE to UPDATED and the waterfall rejects it.
