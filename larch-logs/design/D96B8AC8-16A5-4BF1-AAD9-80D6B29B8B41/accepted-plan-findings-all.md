### FINDING_1: Gap-fill guard can skip ISSUE_NUMBER recovery when REPO is already set
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The new `and` gap-fill guard can prevent `ISSUE_NUMBER` recovery once `REPO` is already populated. If `_load_wrapper_env` seeds `REPO` from the ambient environment before `_bind_step0_route_issue_env` runs, then a resume path with `POSITIONAL_KIND=none` and `ISSUE_NUMBER` only in `.design-step0-route-state.env` can skip gap-fill, reach route handling with an empty `--issue`, and fail to recover the paused issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Prefer keeping the existing OR gap-fill trigger and instead force resolve_repo() in step0_route_main when the issue came from explicit --issue-number or POSITIONAL_KIND=issue, even if REPO is already set, so stale route-state REPO is overwritten without breaking partial resume recovery.


### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/design/design_step0.py:310-311
- **Concern**: [SCOPE-REDUCTION] Both-missing gap-fill guard blocks ISSUE_NUMBER recovery when REPO is already non-empty. Scenario: Step 0a rewrites source-env without REPO, but _load_wrapper_env seeds REPO from os.environ via _base_env before source-env overlay. On POSITIONAL_KIND=none resume, ISSUE_NUMBER is empty while a non-empty ambient REPO survives. Changing the guard to require both ISSUE_NUMBER and REPO missing skips _gap_fill_resume_route_state_values, so route-state ISSUE_NUMBER is never restored and design route is invoked with an empty --issue.
- **Proposed resolution**: Use if not env.get("ISSUE_NUMBER"): instead of requiring both keys to be missing. That still blocks stale route-state REPO on fresh explicit issues because ISSUE_NUMBER is set before the guard, while preserving resume gap-fill whenever ISSUE_NUMBER is absent. Add a regression test with POSITIONAL_KIND=none, non-empty REPO in wrapper env, route-state ISSUE_NUMBER=42 only, and assert route uses --issue 42.

### FINDING_1: Pin ambient REPO for Test 1
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Test 1 can pass or fail for the wrong reason because it assumes `resolve_repo()` runs even when `os.environ.REPO` is already populated. That leaves the ambient repo state unpinned and can mask the stale-route-state path the test is meant to cover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In Test 1 add monkeypatch.delenv("REPO", raising=False) or monkeypatch.setenv("REPO", "") before step0_route_main, matching the empty-REPO precondition in the plan's failure-modes section and the ambient-REPO isolation pattern used elsewhere (e.g. test_plan_quality.py).


