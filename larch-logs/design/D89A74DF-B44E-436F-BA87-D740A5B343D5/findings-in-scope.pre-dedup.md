### FINDING_1:
- **Reviewer(s)**: Cursor-Arch Retry
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Plan documents PLR0911 metric-growth fast-fail as an overbroad-carve-out risk but does not add a PLR0911-only metric regression test. Scenario: The carve-out changes `_is_complexity_baseline_regression_log` semantics for PLR0911. Existing coverage uses PLR0913 metric growth (`test_run_lint_fix_complexity_baseline_metric_growth_fast_fail`) and mixed PLR0911 (new)+PLR0913 metric. An implementation that evaluates the PLR0911 (new) exemption before the metric matcher, or exempts all PLR0911 lines, could let isolated `PLR0911 metric N > baseline M` logs reach external lint-fix while PLR0913 metric logs still fast-fail; CI would stay green
- **Proposed resolution**: Add a `run_lint_fix` test mirroring the existing metric-growth fixture but with `larch/git/gh.py:pr_checks_not_ready_detail PLR0911 metric 7 > baseline 6` (or similar) and assert `_assert_complexity_fast_fail`; state in `checks.py` that metric regression matching must run before the PLR0911 (new)-only carve-out



