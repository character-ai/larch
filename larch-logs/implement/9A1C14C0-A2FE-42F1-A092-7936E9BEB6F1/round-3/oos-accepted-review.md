### OOS_3: risk-integration: python/test_tracking_issue.py:462
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Full ghp_-shaped token added in pytest while .gitleaks.toml allowlist entries for retired tracking-issue-write harnesses were removed and test_tracking_issue.py was not allowlisted. make lint / CI gitleaks Layers 1-2 fail on the new test file despite correct runtime behavior. Use non-matching placeholder tokens per SECURITY.md or add a narrow python/test_tracking_issue.py allowlist only if unavoidable.
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/tracking_issue.py:708-717
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] read_main emits shell-level usage failure envelopes before quiet_init Under inherited quiet, command substitution can miss FAILED=true/ERROR=usage output because emit_kv uses the parent fd 3 instead of the child stdout pipe Initialize quiet routing before pre-parse CliFailure envelopes, while keeping parser-level missing-value cases stderr-only
- **Suggested revision**: Address the concern above.


