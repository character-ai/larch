# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_gather_git_checks_and_behind` drops checks observation on behind-probe timeout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-dyn-ci-timeout-bail-output.txt
- **Severity**: important
- **Concern**: A timed-out `git rev-list --count` in `_behind_count` raises `GhReadTimeout`, and `_gather_git_checks_and_behind` converts any `GhReadTimeout` into `_ci_status_for_query_timeout` with `status="error"` and `checks_observed=False`, even when `_resolve_checks_observation` already returned `pass` or `fail`. That reverses the established fail-open behind-probe contract (non-zero `rev-list` still returns `None` and `gather_status` keeps the checks verdict). A transient behind-probe hang after green or failed CI can drop the real checks verdict, route to pending/coerced retry, increment `ci_failures`, and eventually bail with `CI_WAIT_BAIL_STATUS_STALE` instead of merging or triggering `evaluate_failure`/fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: On rev-list timeout only, return observation with behind_count=0 (match behind_raw is None path) and optional breadcrumb; reserve error/bail counting for gh pr view/checks timeouts.
  - From cursor-specialist-correctness-output.txt: Preserve observation.status and failed_run_id on behind-probe timeout; only treat pr_view/checks timeouts as full gather failures.
  - From dyn-dyn-ci-timeout-bail-output.txt: Do not treat behind-probe timeouts as a full status failure once checks are known. On `EXIT_TIMEOUT` in `_behind_count`, log and return `None` (same as other behind-probe failures), or catch behind-probe timeouts only after observation and return `(observation, None)` so `observation.status` and `checks_observed` are preserved.


### FINDING_4: Public `behind_count()` breaks fail-open on rev-list timeout
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-dyn-ci-timeout-bail-output.txt
- **Severity**: important
- **Concern**: Public `behind_count()` is documented and implemented as fail-open to `0`, but `_behind_count()` now raises `gh.GhReadTimeout` on subprocess timeout. The wrapper only maps `None` to `0`, so `python/cli.py ci behind-count` can crash on a timed-out probe instead of emitting `BEHIND_COUNT=0`. Existing `test_behind_count_fail_open` does not cover `EXIT_TIMEOUT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Catch GhReadTimeout in behind_count() (return 0) and add test_ci.py coverage for rev-list EXIT_TIMEOUT.
  - From dyn-dyn-ci-timeout-bail-output.txt: In `behind_count()`, catch `GhReadTimeout` (or handle `EXIT_TIMEOUT` inside `_behind_count` without raising) and return `0` after a warning breadcrumb, matching the existing non-zero exit-code path.


