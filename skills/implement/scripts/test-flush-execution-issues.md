# test-flush-execution-issues.sh

Delegation smoke for `skills/implement/scripts/flush-execution-issues.sh`.

It verifies both `CLAUDE_PLUGIN_ROOT` override and script-relative fallback.
Each case checks exact CLI routing, argument forwarding, exit-status forwarding,
and stdout and stderr passthrough. Behavioral coverage lives in
`python/tests/issue/test_execution_issues.py`.
