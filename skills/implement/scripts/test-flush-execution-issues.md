# test-flush-execution-issues.sh

Delegation smoke for `skills/implement/scripts/flush-execution-issues.sh`.

It verifies both `CLAUDE_PLUGIN_ROOT` override and script-relative fallback.
Each case checks exact CLI routing, argument forwarding, exit-status forwarding,
and stdout and stderr passthrough. Behavioral coverage lives in
`crates/larch-cli/src/execution_issue_commands.rs`.
