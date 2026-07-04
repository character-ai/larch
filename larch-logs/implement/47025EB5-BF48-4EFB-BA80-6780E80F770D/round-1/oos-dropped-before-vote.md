### OOS_1: [OUT_OF_SCOPE] Missing exit-code propagation from filing-status helper
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Tier B `_emit_chat_print_filing_status()` calls `normalize_file_failure_report_env()` but drops its return code, so a normalization failure could be ignored and `compose_report` might continue as if filing succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Validate gh repo output before cross-repo helper invocation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `gh repo view` stdout is forwarded to the cross-repo helper without strict owner/repo allowlist validation, so malformed or compromised output could cross the subprocess boundary unchecked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Missing direct unit tests for normalize_file_failure_report_env
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: `normalize_file_failure_report_env()` lacks direct unit coverage for pass-through and fallback statuses, leaving no-match / lookup-failed-open handling vulnerable to regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Prefixed-slice dedup test misses normalized stdout assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The prefixed-slice dedup integration path does not assert the normalized stdout shape after the production change, so the helper could emit raw FILE_FAILURE_REPORT_* keys without failing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend test to assert STALL_RECOVERY_REPORT_STATUS when helper mock writes realistic FILE_FAILURE_REPORT_* content.

### OOS_5: [OUT_OF_SCOPE] Subprocess mock targets shared module instead of call site
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The subprocess mock patches `stall_recovery.subprocess` rather than the module used by `_report`, which makes the test fragile to import-refactor changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Patch _sr_report.subprocess.run or use pytest-subprocess at the call site under test.

