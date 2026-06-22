# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: gh pr checks EXIT_TIMEOUT misclassified as empty/pending instead of status failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-dyn-ci-timeout-bail-output.txt
- **Severity**: important
- **Concern**: `gh pr checks` reads now use `CI_STATUS_QUERY_TIMEOUT_SEC`, but `EXIT_TIMEOUT` is treated as empty output and classified as pending or `NO_CHECKS` rather than a status-query failure. Unlike `gh pr view` (which maps timeout to `status="error"` / `GhReadTimeout` and `CI_MONITOR_STATUS_FAILURE_BAIL`), repeated checks timeouts do not increment `ci_failures`. The monitor can heartbeat and poll for the full `CI_WAIT_TIMEOUT_SEC` budget, or bail with false `CI_WAIT_BAIL_NO_CHECKS_OBSERVED` (startup-deadline or grace paths) while CI is active or finished on GitHub.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Treat config.EXIT_TIMEOUT from _gh_pr_checks and _read_pr_checks_text as a status-query failure, for example by returning CiStatus(status="error", ...) or raising a typed timeout that gather_status maps to CI_MONITOR_STATUS_FAILURE_BAIL.
  - From cursor-specialist-testing-output.txt: Treat checks timeouts like `pr_view` (raise `GhReadTimeout` or return `status="error"` from `gather_status`), wire through `_coerce_status_failure`, and add `test_gather_status_pr_checks_timeout_returns_error` plus a `poll_ci` bail test mirroring `test_poll_ci_pr_view_timeout_bails_status_stale`.
  - From dyn-dyn-ci-timeout-bail-output.txt: Treat `EXIT_TIMEOUT` from `_gh_pr_checks` / `_read_pr_checks_text` (and optionally `gh.pr_checks_text_read`) like `GhReadTimeout`: return `CiStatus(status="error", pr_view_ok=…, checks_observed=False)` from `gather_status`, or raise a shared timeout exception caught there, so `_coerce_status_failure` increments `ci_failures` and bails with `CI_WAIT_BAIL_STATUS_STALE` after `CI_MONITOR_STATUS_FAILURE_BAIL`. At minimum, failed reads must not set `rollup_empty=True` / `observed=True`; mirror the fetch-failure path at `python/ci_monitor.py:576-585` (`checks_observed=False`) so startup-deadline logic cannot fire on query failures.


### FINDING_2: git fetch and behind_count in gather_status have no subprocess timeout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: A hung `git fetch` or `git rev-list` after the query heartbeat can block `poll_ci` indefinitely with a stale poll breadcrumb, even though `gh` calls are now bounded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Bound fetch/rev-list with CI_STATUS_QUERY_TIMEOUT_SEC and route failures into _coerce_status_failure


