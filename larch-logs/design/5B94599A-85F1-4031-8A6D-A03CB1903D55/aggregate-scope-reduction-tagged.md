### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: scripts/test-lint-bash32.sh
- **Concern**: [SCOPE-REDUCTION] Drop firm subshell rewrite of scripts/test-lint-awk-multibyte-regex.sh. Scenario: The plan admits lines 58 and 87 run under `set +e` and are not known bash 3.2 abort sites. Converting them is consistency-only churn once the lint exists. After the lint rule, satisfy CI with two `# lint-bash32: ok harness uses set +e` suppressions on those lines instead of an UPDATED harness file; keep the live tail fix, residual manifest entry, lint rule, and bash32 tests as the firm deliverables.
- **Proposed resolution**:
