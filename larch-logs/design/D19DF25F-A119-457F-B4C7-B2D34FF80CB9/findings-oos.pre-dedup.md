### OOS_1:
- **Description**: [OUT_OF_SCOPE] The design-log-publish contract still says the log-only path may rerun once without a network signature, which will be false after the planned transient-only guard.. Scenario: Operators reading the shipped script contract will expect a one-shot rerun on deterministic or unavailable logs even though the Python helper will now fail without submitting rerun_failed.
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.md:104-111
- **Phase**: design

### OOS_1:
- **Description**: No unit test for new is_transient_failed_log helper. Scenario: Regression in the shared predicate would only surface indirectly through design_log_ship or evaluate_failure integration tests
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: python/ci_monitor.py:1392-1395
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] No direct unit test for new is_transient_failed_log helper. Scenario: Behavior is covered indirectly by test_evaluate_failure_transient_rerun_only and test_evaluate_failure_deterministic_no_rerun (1038-1154); extraction alone does not need new tests under SIMPLE minimum-change gate
- **Reviewer**: Cursor-dyn-api-callers
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/ci_monitor.py:1392-1395
- **Phase**: design

