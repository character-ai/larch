### OOS_1: Git-backed `main` tests should reuse `_git_ok_runner` explicitly
- **Description**: Git-backed `main` tests should reuse `_git_ok_runner` explicitly. Scenario: After port, tmp_path `main(["--root", ...])` needs tracked-path mocks; the plan only says "injected-runner `main`" without naming the shared helper. Failure is localized to tests, not production lint.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/lint/test_lint_markdown_heading_fence_state.py
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Per-finding baselined stderr warnings differ under `run_rule`
- **Description**: [OUT_OF_SCOPE] Per-finding baselined stderr warnings differ under `run_rule`. Scenario: Legacy check mode prints one `warning: <file>:<symbol> applies heading regex ... (baselined)` line per grandfathered finding. Engine baseline mode suppresses stdout for baselined rows and only emits generic stale warnings. Operators lose per-finding grandfathered breadcrumbs unless restored in the adapter.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: python/larch/lint/lint_markdown_heading_fence_state.py:799-807
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

