## Goal
Fix voter parse-rate diagnostic leak from test fixtures into parent run execution-issues and suppress CI Node.js 20 deprecation warning

## Implementation Plan
Fix test fixtures leaking voter parse-rate diagnostics into parent run execution-issues.


### Part A — scripts/test-dispatch-code-voters.sh
1. Add unset LARCH_EXECUTION_ISSUES_LOG SESSION_ENV_PATH IMPLEMENT_TMPDIR after unset CLAUDE_PLUGIN_ROOT.
2. Update retry-fail claude test: remove retry_fail_issues variable and assertions checking issues log IS written.
3. Update retry-fail codex test: remove retry_fail_codex_issues and issues-log assertion.
4. Add 3 regression tests: env isolation, test-tmpdir path guard, production-shape regression.

### Part B — scripts/dispatch-code-voters.sh
Add case guard in check_voter_parse_rate() after diag file write, before append-tool-failure.sh invocation, to suppress parent-log write when voter_path matches test-tmpdir patterns.

### Part C — CI workflow
Add FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true env block to ci.yaml and release-tag.yaml.

### Sibling .md updates
Update dispatch-code-voters.md and test-dispatch-code-voters.md.

## Test plan
(no test plan section in plan-file)
