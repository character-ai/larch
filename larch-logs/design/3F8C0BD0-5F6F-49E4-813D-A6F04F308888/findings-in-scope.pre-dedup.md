### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/state/finalize.py:704-714
- **Concern**: The stale-mismatch recovery does not require the second `load_coverage(tmpdir)` call to return coverage, despite the plan requiring missing persisted coverage to fail closed. Scenario: The coverage files can disappear between `load_live_coverage(...)` raising and recovery rereading them. `load_coverage(...)` then returns `None`, `load_disposition(..., coverage=None)` can also return `None`, and teardown selects `"closes"`, applies the `[DONE]` rename, and completes without validated persisted evidence
- **Proposed resolution**: After recovery calls `load_coverage(tmpdir)`, explicitly raise `ShipError` if it returns `None`. Add this case to the focused recovery test so the done rename and cleanup remain blocked



### FINDING_2:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:528-550
- **Concern**: The prior narrow-catch fix remains incomplete because the mismatch branch returns before validating the persisted disposition, contrary to the plan's fail-closed requirement. Scenario: If live coverage is stale and the disposition artifact is malformed, unsafe, or inconsistent with persisted coverage, final-report generation silently succeeds and hides the integrity failure
- **Proposed resolution**: Load persisted coverage and call `load_disposition(implement_tmpdir, coverage=coverage)` before returning `""` from the exact-mismatch branch; add a regression proving an invalid disposition still raises when the live fingerprint is stale



